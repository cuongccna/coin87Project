# Time-Series Database Integration for Coin87

## Executive Summary

This document outlines the strategy for integrating time-series database capabilities into Coin87 to handle high-frequency real-time metrics while maintaining PostgreSQL for relational data.

## Current Architecture Limitations

### PostgreSQL Strengths
- ✅ ACID compliance for critical data
- ✅ Complex queries and joins
- ✅ Immutability enforcement for `information_events`
- ✅ Mature ecosystem and tooling

### PostgreSQL Weaknesses for Real-Time Metrics
- ❌ High write overhead for time-series data (every price tick, sentiment score)
- ❌ No built-in downsampling/retention policies
- ❌ Suboptimal storage for high-cardinality time-series
- ❌ Limited compression for time-ordered data

## Proposed Solution: Hybrid Architecture

### Option 1: TimescaleDB (PostgreSQL Extension) ⭐ RECOMMENDED

**Why TimescaleDB:**
- Drop-in PostgreSQL extension (no separate database)
- SQL interface (familiar to team)
- Automatic partitioning and compression
- Retention policies out-of-the-box
- Free for single-node deployments

**Implementation:**
```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Convert existing metrics tables to hypertables
SELECT create_hypertable('source_reliability_metrics', 'timestamp');
SELECT create_hypertable('market_price_ticks', 'timestamp');
SELECT create_hypertable('sentiment_scores', 'timestamp');

-- Add compression policy (compress data older than 7 days)
ALTER TABLE source_reliability_metrics SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'source_ref'
);

SELECT add_compression_policy('source_reliability_metrics', INTERVAL '7 days');

-- Add retention policy (drop data older than 90 days)
SELECT add_retention_policy('market_price_ticks', INTERVAL '90 days');
```

**Migration Steps:**
1. Install TimescaleDB extension on existing PostgreSQL server
2. Create new hypertables for real-time metrics
3. Migrate historical data (if needed)
4. Update application code to use new tables
5. Set up continuous aggregates for dashboards

**Estimated Effort:** 2-3 days
**Risk Level:** Low (extension, not separate service)

---

### Option 2: InfluxDB (Dedicated Time-Series DB)

**Why InfluxDB:**
- Purpose-built for time-series (optimal performance)
- Industry-standard for IoT/monitoring
- InfluxQL and Flux query languages
- Built-in downsampling and retention

**Drawbacks:**
- Separate service to manage
- New query language to learn
- Increased operational complexity
- Licensing concerns for clustering

**Use Case:** Only if write throughput exceeds 100k points/second (unlikely for Coin87)

**Estimated Effort:** 5-7 days
**Risk Level:** Medium (new service dependency)

---

## Recommended Schema Split

### PostgreSQL (Relational/Immutable)
```python
# Core immutable data
information_events         # Raw ingestion (append-only)
narratives                 # Derived clusters
risk_events                # Risk classifications
governance_logs            # Audit trail
users, sessions, tokens    # Application state
```

### TimescaleDB Hypertables (Time-Series/High-Frequency)
```python
# Real-time metrics (high write volume)
source_reliability_metrics (
    timestamp TIMESTAMPTZ NOT NULL,
    source_ref TEXT NOT NULL,
    trust_score FLOAT,
    response_time_ms INT,
    error_rate FLOAT,
    PRIMARY KEY (timestamp, source_ref)
);

market_price_ticks (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DECIMAL(18, 8),
    volume DECIMAL(18, 8),
    exchange TEXT,
    PRIMARY KEY (timestamp, symbol, exchange)
);

sentiment_scores (
    timestamp TIMESTAMPTZ NOT NULL,
    narrative_id TEXT NOT NULL,
    sentiment_score FLOAT,
    volume INT,
    PRIMARY KEY (timestamp, narrative_id)
);

alert_events (
    timestamp TIMESTAMPTZ NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT,
    source_ref TEXT,
    metadata JSONB,
    PRIMARY KEY (timestamp, alert_type)
);
```

### Redis (Cache/Ephemeral)
```python
# Short-lived data (< 1 hour TTL)
live:source:{id}:behavior   # Real-time health monitoring
cache:article:{id}          # Processed content cache
ratelimit:api:{endpoint}    # API rate limiting
queue:ingestion             # Processing queues
```

---

## Implementation Roadmap

### Phase 1: Setup TimescaleDB (Week 1)
- [ ] Install TimescaleDB extension on PostgreSQL
- [ ] Create migration script for hypertable conversion
- [ ] Test on development environment
- [ ] Document query patterns

### Phase 2: Migrate High-Frequency Tables (Week 2)
- [ ] Create `source_reliability_metrics` hypertable
- [ ] Create `market_price_ticks` hypertable (if WebSocket implemented)
- [ ] Create `sentiment_scores` hypertable
- [ ] Set up compression policies
- [ ] Set up retention policies

### Phase 3: Application Integration (Week 3)
- [ ] Update ingestion jobs to write to hypertables
- [ ] Create continuous aggregates for dashboards
- [ ] Add time-series queries to API endpoints
- [ ] Performance testing and optimization

### Phase 4: Monitoring & Optimization (Week 4)
- [ ] Set up TimescaleDB monitoring
- [ ] Optimize chunk intervals
- [ ] Fine-tune compression settings
- [ ] Document operational procedures

---

## Query Examples

### Before (Standard PostgreSQL)
```sql
-- Slow: full table scan for time range
SELECT source_ref, AVG(trust_score) 
FROM source_metrics 
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY source_ref;
```

### After (TimescaleDB)
```sql
-- Fast: uses time partitioning + continuous aggregate
SELECT source_ref, AVG(trust_score)
FROM source_reliability_metrics
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY source_ref;

-- Or use continuous aggregate (pre-computed)
SELECT * FROM source_daily_stats
WHERE day > NOW() - INTERVAL '7 days';
```

### Continuous Aggregate (Real-Time Materialized View)
```sql
CREATE MATERIALIZED VIEW source_hourly_stats
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS hour,
    source_ref,
    AVG(trust_score) AS avg_trust,
    MAX(error_rate) AS max_errors,
    COUNT(*) AS sample_count
FROM source_reliability_metrics
GROUP BY hour, source_ref;

-- Auto-refresh policy
SELECT add_continuous_aggregate_policy('source_hourly_stats',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

---

## Performance Benchmarks (Expected)

| Metric | PostgreSQL | TimescaleDB | Improvement |
|--------|-----------|-------------|-------------|
| Insert 10k points/sec | ~500 ms | ~50 ms | **10x** |
| Range query (7 days) | ~2000 ms | ~200 ms | **10x** |
| Storage (1M points) | ~500 MB | ~50 MB | **10x** |
| Downsampling query | Manual | Built-in | **N/A** |

---

## Cost Analysis

### Option 1: TimescaleDB (RECOMMENDED)
- **License:** Free (Apache 2.0)
- **Infrastructure:** No additional servers (extension only)
- **Operational Cost:** $0/month extra
- **Total Cost:** **$0**

### Option 2: InfluxDB
- **License:** Free (single node) / $500+/month (cluster)
- **Infrastructure:** +1 server (~$50/month)
- **Operational Cost:** Team learning curve
- **Total Cost:** **$50-600/month**

---

## Risk Assessment

### TimescaleDB Risks (Low)
- ✅ Mature extension (5+ years production use)
- ✅ PostgreSQL compatibility (can disable if needed)
- ✅ No vendor lock-in
- ⚠️ Single-node limit for free tier (fine for MVP)

### InfluxDB Risks (Medium)
- ⚠️ Separate service dependency
- ⚠️ Team needs to learn new query language
- ⚠️ Clustering requires paid license
- ⚠️ Data migration complexity

---

## Decision Matrix

| Criteria | TimescaleDB | InfluxDB | Winner |
|----------|-------------|----------|---------|
| Ease of Integration | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | TimescaleDB |
| Performance | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | InfluxDB |
| Cost | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | TimescaleDB |
| Team Familiarity | ⭐⭐⭐⭐⭐ | ⭐⭐ | TimescaleDB |
| Operational Complexity | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | TimescaleDB |
| Scalability | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | InfluxDB |
| **TOTAL** | **27/30** | **23/30** | **TimescaleDB** |

---

## Recommendation

**Use TimescaleDB** for the following reasons:

1. **Zero Additional Cost:** Extension to existing PostgreSQL
2. **Low Risk:** Can be enabled/disabled without data loss
3. **Team Familiarity:** SQL interface (no new language)
4. **Sufficient Performance:** Handles 100k+ inserts/sec (well above our needs)
5. **Easy Migration:** Gradual migration, table-by-table
6. **Built-in Features:** Compression, retention, continuous aggregates

**Reserve InfluxDB** for future consideration only if:
- Write throughput exceeds 100k points/second
- Multi-datacenter replication is required
- TimescaleDB proves insufficient (unlikely)

---

## Next Steps

1. ✅ Review this document with team
2. ⬜ Approve TimescaleDB integration
3. ⬜ Install TimescaleDB on dev environment
4. ⬜ Create proof-of-concept hypertable
5. ⬜ Benchmark against current PostgreSQL tables
6. ⬜ Plan production migration (if benchmarks successful)

---

## References

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [TimescaleDB vs InfluxDB Comparison](https://docs.timescale.com/timescaledb/latest/overview/timescaledb-vs-influxdb/)
- [PostgreSQL Extension Security](https://www.postgresql.org/docs/current/extend-extensions.html)
- [Coin87 Architecture Doc](./ARCHITECTURE.md)
