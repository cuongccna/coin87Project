# coin87 — Full System Validation (Trust & Governance)

This document is the canonical validation checklist for pilot readiness.

**Scope**: PostgreSQL schema + Alembic baseline, SQLAlchemy immutability guards, read-only repositories, FastAPI GET-only API, read-only institutional UI.

**Pass/Fail rule**: a validation area passes only if all checks in that area pass.

---

## 1) DATABASE & SCHEMA VALIDATION

### 1.1 Tables exist (expected baseline)
- **Expected** (exact):
  - `information_events`
  - `decision_risk_events`
  - `narrative_clusters`
  - `narrative_memberships`
  - `consensus_pressure_events`
  - `timing_distortion_windows`
  - `decision_contexts`
  - `decision_environment_snapshots`
  - `decision_impact_records`
  - `re_evaluation_logs`

**Query**:

```sql
select tablename
from pg_tables
where schemaname = 'public'
order by tablename;
```

**Pass**: all expected tables present, no table named `news`.

---

### 1.2 ENUM types exist
**Expected** (must exist):
- `decision_risk_type_enum`
- `recommended_posture_enum`
- `narrative_status_enum`
- `distortion_type_enum`
- `decision_context_type_enum`
- `environment_state_enum`

**Query**:

```sql
select t.typname
from pg_type t
join pg_namespace n on n.oid = t.typnamespace
where n.nspname = 'public' and t.typtype = 'e'
order by t.typname;
```

**Pass**: required enums present.

---

### 1.3 Foreign keys and names
**Query**:

```sql
select
  tc.constraint_name,
  tc.table_name,
  kcu.column_name,
  ccu.table_name as foreign_table_name,
  ccu.column_name as foreign_column_name
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu
  on tc.constraint_name = kcu.constraint_name
join information_schema.constraint_column_usage ccu
  on ccu.constraint_name = tc.constraint_name
where tc.constraint_type = 'FOREIGN KEY'
  and tc.table_schema = 'public'
order by tc.table_name, tc.constraint_name;
```

**Pass**: FK names match migration and reference correct targets.

---

### 1.4 CHECK constraints enforced
Validate by inspection + runtime insert checks.

**Query**:

```sql
select conname, conrelid::regclass as table_name, pg_get_constraintdef(c.oid) as def
from pg_constraint c
where contype = 'c'
order by table_name::text, conname;
```

**Pass**: constraints exist for:
- `decision_risk_events.severity` range
- `decision_risk_events.valid_to > valid_from`
- `narrative_clusters.saturation_level` range
- `consensus_pressure_events.pressure_level` range
- `timing_distortion_windows.window_end > window_start`
- `decision_environment_snapshots.risk_density >= 0`
- `information_events.content_hash_sha256` length

---

### 1.5 No unintended NULLs
**Query**:

```sql
select table_name, column_name, is_nullable, data_type
from information_schema.columns
where table_schema = 'public'
order by table_name, ordinal_position;
```

**Pass**: nullable flags match model intent.

---

### 1.6 Migration downgrade leaves DB clean
Use script:
- `scripts/validate_migration_roundtrip.py`

**Pass**:
- After downgrade, expected tables are gone.
- Required enum types are gone.

---

## 2) IMMUTABILITY ENFORCEMENT TESTS

Run:
- `pytest -q backend/tests/test_immutability.py`

**Pass**:
- Updating `DecisionRiskEvent.severity` raises explicit exception and DB row unchanged.
- Deleting historical records is forbidden (explicit exception).
- Snapshots cannot be updated or deleted.
- Impact records cannot be updated or deleted.

---

## 3) REPOSITORY READ-ONLY GUARANTEE

Run:
- `pytest -q backend/tests/test_repository_read_only_static.py`
- `pytest -q backend/tests/test_repository_read_only_runtime.py`

**Pass**:
- No `.commit()`, `.add()`, `.delete()`, `.execute(insert/update/delete)` in repositories.
- Runtime guard rejects execution if session is dirty/new/deleted.

---

## 4) API CONTRACT VERIFICATION

Run:
- `pytest -q backend/tests/test_api_contract.py`

**Pass**:
- Only GET endpoints exposed under `/v1/*`.
- OpenAPI is parseable and contains no POST/PUT/PATCH/DELETE under `/v1/decision/*`.
- Responses do not leak internal DB fields (no `raw_payload`, no SQLAlchemy internals).
- Empty lists are valid (200 with `[]`).
- No implicit “urgency sorting” in contract (explicit ordering only).

---

## 5) ROLE & ACCESS CONTROL CHECK

Run:
- `pytest -q backend/tests/test_api_access_control.py`

**Pass**:
- READ_ONLY and PM can access environment/risk/narratives endpoints.
- PM cannot access `/v1/decision/history*` (403).
- CIO/RISK can access `/v1/decision/history*` (200 or 404 if absent).
- Default deny: invalid token => 401.

---

## 6) UI INTEGRITY CHECK (READ-ONLY)

Run:
- `python scripts/ui_readonly_scan.py`

**Pass**:
- No POST/PUT/PATCH/DELETE usage in UI code.
- No `setInterval`/aggressive polling loops in UI.
- IC Prep mode renders even if API returns empty arrays (handled in code).

---

## 7) FAILURE & DEGRADED MODE SIMULATION

Run:
- `pytest -q backend/tests/test_api_degraded_modes.py`

**Pass**:
- DB connection errors return 503 with neutral message.
- No fabricated data.
- No retry storms (API does not instruct tight retries).

---

## 8) LOGGING & AUDIT TRAIL CHECK

Run:
- `pytest -q backend/tests/test_logging_audit.py`

**Pass**:
- Every response includes `x-request-id`.
- Access logs are structured JSON and do not include authorization headers.

---

## 9) PILOT READINESS CHECKLIST

### Pilot boundaries (30–45 days)
- Single deployment, single API worker (rate limiter is per-process).
- Tokens provisioned manually; no self-signup.
- Read-only endpoints only; no data mutation via API.

### Known limitations (explicit)
- Rate limiting is **in-memory per process** (enforce single worker for strictness).
- Governance/audit UI pages may show placeholders if audit endpoints are not exposed.

**Pass**: pilot stakeholders accept limitations and operational boundaries.

