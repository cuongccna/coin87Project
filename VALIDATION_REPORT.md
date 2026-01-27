## coin87 — Full Validation Report

- **timestamp**: 2026-01-26 00:05:17
- **database_url (redacted)**: `postgresql+psycopg2://coin87_user:***@localhost:5432/coin87_db`
- **roundtrip_database_url (redacted)**: `postgresql+psycopg2://coin87_user_test:***@localhost:5432/coin87_db_test`

### Results

- **DB connectivity (select 1)**: **PASS**

```
select 1 => 1
```
- **Alembic upgrade head**: **PASS**

```
Upgrading Alembic to head…
PASS: upgraded to head.
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```
- **DB schema presence (db_inspect)**: **PASS**

```
public tables: ['alembic_version', 'consensus_pressure_events', 'decision_contexts', 'decision_environment_snapshots', 'decision_impact_records', 'decision_risk_events', 'information_events', 'narrative_clusters', 'narrative_memberships', 're_evaluation_logs', 'timing_distortion_windows']
coin87 tables (any schema): [('public', 'alembic_version'), ('public', 'consensus_pressure_events'), ('public', 'decision_contexts'), ('public', 'decision_environment_snapshots'), ('public', 'decision_impact_records'), ('public', 'decision_risk_events'), ('public', 'information_events'), ('public', 'narrative_clusters'), ('public', 'narrative_memberships'), ('public', 're_evaluation_logs'), ('public', 'timing_distortion_windows')]
enum types (all schemas): [('public', 'decision_context_type'), ('public', 'decision_context_type_enum'), ('public', 'decision_environment_state'), ('public', 'decision_recommended_posture'), ('public', 'decision_risk_type'), ('public', 'decision_risk_type_enum'), ('public', 'distortion_type_enum'), ('public', 'environment_state_enum'), ('public', 'narrative_status'), ('public', 'narrative_status_enum'), ('public', 'recommended_posture_enum'), ('public', 'timing_distortion_type')]
alembic_version: [('0001_initial',)]
```
- **Backend trust tests (pytest)**: **PASS**

```
..................                                                       [100%]
18 passed in 1.21s
```
- **UI read-only scan**: **PASS**

```
Scanned 36 files.
PASS: UI appears read-only (no write HTTP methods; no polling intervals).
```
- **Migration roundtrip (explicit DB)**: **PASS**

```
Upgrading to head…
Downgrading to base…
PASS: migration roundtrip clean.
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial, Initial institutional baseline for decision risk infrastructure.
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 0001_initial -> , Initial institutional baseline for decision risk infrastructure.
```

### Summary

- **overall**: **PASS** (no failed checks)
