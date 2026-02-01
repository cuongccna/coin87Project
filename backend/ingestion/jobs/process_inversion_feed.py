"""Background job to process inversion feeds."""
import sys
import argparse
import logging
from typing import List
from uuid import UUID

# Ensure app modules are importable
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.core.db import SessionLocal
from app.services.inversion_service import process_inversion_feed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run(feed_ids: List[UUID]):
    """Process a list of feed IDs."""
    logger.info(f"Starting processing for {len(feed_ids)} feeds")
    
    with SessionLocal() as db:
        for fid in feed_ids:
            try:
                process_inversion_feed(db, fid)
            except Exception as e:
                logger.error(f"Failed to process feed {fid}: {e}")
    
    logger.info("Processing complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Inversion Feed(s)")
    parser.add_argument("feed_id", type=str, help="Feed UUID to process")
    args = parser.parse_args()
    
    try:
        fid = UUID(args.feed_id)
        run([fid])
    except ValueError:
        logger.error("Invalid UUID provided")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
