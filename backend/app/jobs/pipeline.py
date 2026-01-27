"""Coin87 Core Pipeline Orchestrator.

This module coordinates the complete lifecycle of information:
1. Ingestion (Raw Data)
2. Derivation (Clustering & Mapping)
3. Evaluation (Reliability & Trust)

Architecture:
- Cron-driven (stateless runs)
- Idempotent (safe to re-run)
- Failure-tolerant (individual item failures don't stop batch)

Execution Flow:
    run_full_pipeline()
    ├── Phase 1: Ingestion
    │   ├── Fetch from sources (RSS, Twitter, etc.)
    │   └── Persist raw InformationEvents (deduplicated)
    ├── Phase 2: Clustering
    │   ├── Identify unassigned events
    │   ├── Load active narrative context
    │   ├── AI Classification (New vs Existing vs Noise)
    │   └── Persist ClusterAssignments
    ├── Phase 3: Reliability Evaluation
    │   ├── Aggregate metrics per cluster
    │   ├── Apply reliability rules
    │   └── Snapshot history
    └── Phase 4: Source Trust Update
        ├── Aggregate source performance
        └── Update SourceReliability indices
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.information_event import InformationEvent
from app.models.cluster_assignment import ClusterAssignment
from app.models.narrative_cluster import NarrativeCluster, NarrativeStatus

# Components
from ingestion.core.raw_ingest import RawIngestInput, ingest_raw_batch
from derive.core.clustering import ClusteringEngine, ExistingClusterSummary, MockLLMProvider
from derive.core.mapping import map_event_to_cluster
from derive.job.run_reliability_evaluation import run_reliability_evaluation_job
from derive.core.trust import aggregate_source_metrics, update_source_trust_scores
from derive.core.lifecycle import run_lifecycle_update
from derive.core.noise_suppression import run_noise_suppression

# Mock adapters import (In real app, these would be concrete implementations)
# from ingestion.adapters import rss, twitter, telegram


logger = logging.getLogger(__name__)


async def run_ingestion_phase(db: Session) -> int:
    """Phase 1: Fetch and Ingest Raw Data.
    
    Real implementation would iterate configured sources and call adapters.
    Here we simulate or allow injection of inputs.
    """
    logger.info("Starting Phase 1: Ingestion")
    
    # Placeholder: collecting inputs from adapters
    # inputs: List[RawIngestInput] = []
    # inputs.extend(rss.fetch_pending())
    # inputs.extend(twitter.fetch_pending())
    
    # For now, assuming ingestion happens via API or separate workers pushing to DB.
    # If this script owns ingestion, call ingest_raw_batch(db, inputs)
    
    # Return count of new items
    return 0 


async def run_clustering_phase(db: Session, batch_size: int = 50) -> int:
    """Phase 2: Cluster Unassigned Events.
    
    Finds events with no ClusterAssignment and runs AI classification.
    """
    logger.info("Starting Phase 2: Clustering")
    
    # 1. Find unassigned events
    # Outer join or NOT IN query
    subquery = select(ClusterAssignment.information_event_id)
    stmt = select(InformationEvent).where(
        InformationEvent.id.not_in(subquery)
    ).limit(batch_size)
    
    unassigned_events = db.execute(stmt).scalars().all()
    
    if not unassigned_events:
        logger.info("No unassigned events found.")
        return 0

    # 2. Load context (Active Clusters)
    cluster_stmt = select(NarrativeCluster).where(
        NarrativeCluster.status.in_([NarrativeStatus.ACTIVE, NarrativeStatus.FADING])
    )
    active_clusters_orm = db.execute(cluster_stmt).scalars().all()
    
    cluster_summaries = [
        ExistingClusterSummary(
            id=str(c.id),
            theme=c.theme,
            last_seen_iso=c.last_seen_at.isoformat()
        ) 
        for c in active_clusters_orm
    ]

    # 3. Process Batch
    # TODO: In prod, inject real LLM provider
    engine = ClusteringEngine(llm_provider=MockLLMProvider())
    processed_count = 0
    
    for event in unassigned_events:
        try:
            # Extract text
            text_content = f"{event.title}\n{event.body_excerpt or ''}"
            
            # AI Decision
            result = await engine.classify_content(
                text_content=text_content,
                existing_clusters=cluster_summaries
            )
            
            # Persist assignment (or new cluster)
            assignment = map_event_to_cluster(db, event, result)
            
            if assignment:
                logger.info(f"Mapped event {event.id} to cluster {assignment.cluster_id} ({result.decision})")
            else:
                logger.info(f"Event {event.id} classified as NOISE")
                
            # If we created a new cluster, we should probably add it to current context 
            # to avoid creating duplicates in the same batch.
            # (Omitted for simplicity, rely on DB constraints/dedupe logic in mapping)

            processed_count += 1
            
        except Exception as e:
            logger.error(f"Failed to cluster event {event.id}: {e}")
            # Continue to next event (Failure Tolerance)
            continue
            
    db.commit()
    return processed_count


def run_evaluation_phase(db: Session) -> dict:
    """Phase 3: Reliability Evaluation & Snapshotting."""
    logger.info("Starting Phase 3: Reliability Evaluation")
    try:
        return run_reliability_evaluation_job(db)
    except Exception as e:
        logger.error(f"Reliability evaluation failed: {e}")
        return {"status": "error", "message": str(e)}


def run_trust_phase(db: Session) -> int:
    """Phase 4: Source Trust Updates."""
    logger.info("Starting Phase 4: Source Trust Update")
    try:
        metrics = aggregate_source_metrics(db)
        updated_count = update_source_trust_scores(db, metrics)
        db.commit()
        return updated_count
    except Exception as e:
        logger.error(f"Trust update failed: {e}")
        return 0


async def run_full_pipeline():
    """Main entry point for cron job."""
    db = SessionLocal()
    try:
        # 1. Ingestion
        # await run_ingestion_phase(db)
        
        # 2. Clustering
        clustered = await run_clustering_phase(db, batch_size=100)
        logger.info(f"Clustering complete. Processed: {clustered}")
        
        # 3. Evaluation
        eval_result = run_evaluation_phase(db)
        logger.info(f"Evaluation complete. Result: {eval_result}")
        
        # 4. Lifecycle (Phase 6)
        lifecycle_result = run_lifecycle_update(db)
        logger.info(f"Lifecycle update complete. Result: {lifecycle_result}")

        # 5. Trust
        trust_updates = run_trust_phase(db)
        logger.info(f"Trust update complete. Sources updated: {trust_updates}")
        
        # 6. Noise Suppression (Phase 7)
        suppress_stats = run_noise_suppression(db)
        logger.info(f"Noise suppression complete. Stats: {suppress_stats}")
        
    except Exception as e:
        logger.critical(f"Pipeline crashed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_full_pipeline())
