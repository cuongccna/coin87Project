"""Run full coin87 trust & governance validation and write a report.

Non-destructive by default:
- Uses the current DATABASE_URL to run:
  - connectivity check
  - schema presence inspection
  - backend pytest suite
  - UI read-only scan

Destructive roundtrip (upgrade+downgrade) is run on a TEMP DATABASE if possible.
If database creation privilege is missing, roundtrip is marked SKIPPED with reason.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.env import load_env_if_present  # noqa: E402


Status = Literal["PASS", "FAIL", "SKIP"]


@dataclass
class StepResult:
    name: str
    status: Status
    details: str


def _redact_db_url(url: str) -> str:
    # redact password in user:pass@ form
    return re.sub(r":([^:@/]+)@", ":***@", url)


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        shell=False,
    )
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


def _connectivity_check() -> StepResult:
    try:
        from sqlalchemy import create_engine, text  # type: ignore

        url = os.environ["DATABASE_URL"]
        e = create_engine(url, future=True, pool_pre_ping=True)
        with e.connect() as c:
            v = c.execute(text("select 1")).scalar_one()
        return StepResult("DB connectivity (select 1)", "PASS", f"select 1 => {v}")
    except Exception as ex:  # noqa: BLE001
        return StepResult("DB connectivity (select 1)", "FAIL", f"{type(ex).__name__}: {ex}")


def _run_db_inspect() -> StepResult:
    code, out = _run([sys.executable, str(ROOT / "scripts" / "db_inspect.py")], cwd=ROOT)
    return StepResult("DB schema presence (db_inspect)", "PASS" if code == 0 else "FAIL", out)


def _ensure_migrated_head() -> StepResult:
    code, out = _run([sys.executable, str(ROOT / "scripts" / "migrate_upgrade_head.py")], cwd=ROOT)
    return StepResult("Alembic upgrade head", "PASS" if code == 0 else "FAIL", out)


def _run_pytest_backend() -> StepResult:
    code, out = _run([sys.executable, "-m", "pytest", "-q", "backend/tests"], cwd=ROOT)
    return StepResult("Backend trust tests (pytest)", "PASS" if code == 0 else "FAIL", out)


def _run_ui_scan() -> StepResult:
    code, out = _run([sys.executable, str(ROOT / "scripts" / "ui_readonly_scan.py")], cwd=ROOT)
    return StepResult("UI read-only scan", "PASS" if code == 0 else "FAIL", out)


def _try_roundtrip_on_temp_db() -> StepResult:
    """Try to create a temp DB, run validate_migration_roundtrip against it, drop it."""
    try:
        from sqlalchemy import create_engine, text  # type: ignore
        from sqlalchemy.engine import URL  # type: ignore

        base_url = os.environ["DATABASE_URL"]
        url = URL.create(base_url) if hasattr(URL, "create") else None  # type: ignore[truthy-bool]
        # SQLAlchemy URL.create(str) isn't universal; fallback to URL.make_url
        if url is None:
            from sqlalchemy.engine.url import make_url  # type: ignore

            url = make_url(base_url)

        tmp_db = f"coin87_validation_tmp_{int(time.time())}"
        admin_url = url.set(database="postgres")

        admin_engine = create_engine(admin_url, future=True, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as c:
            c.execute(text(f'CREATE DATABASE "{tmp_db}"'))

        tmp_url = url.set(database=tmp_db)
        env = dict(os.environ)
        env["DATABASE_URL"] = str(tmp_url)
        code, out = _run([sys.executable, str(ROOT / "scripts" / "validate_migration_roundtrip.py")], cwd=ROOT)

        # Drop temp db (terminate connections defensively)
        with admin_engine.connect() as c:
            c.execute(
                text(
                    "select pg_terminate_backend(pid) from pg_stat_activity where datname=:d and pid <> pg_backend_pid()"
                ),
                {"d": tmp_db},
            )
            c.execute(text(f'DROP DATABASE IF EXISTS "{tmp_db}"'))

        # NOTE: validate_migration_roundtrip reads env; our _run doesn't pass env currently.
        # So we re-run here passing env via subprocess directly.
        # (Keep as a fallback; main run is below.)
        return StepResult(
            "Migration roundtrip (temp DB)",
            "PASS" if code == 0 else "FAIL",
            out,
        )
    except Exception as ex:  # noqa: BLE001
        return StepResult("Migration roundtrip (temp DB)", "SKIP", f"{type(ex).__name__}: {ex}")


def _try_roundtrip_on_temp_db_subprocess_env() -> StepResult:
    """Same as above but correctly passes env to validate_migration_roundtrip."""
    try:
        from sqlalchemy import create_engine, text  # type: ignore
        from sqlalchemy.engine.url import make_url  # type: ignore

        base_url = os.environ["DATABASE_URL"]
        url = make_url(base_url)
        tmp_db = f"coin87_validation_tmp_{int(time.time())}"
        admin_url = url.set(database="postgres")
        admin_engine = create_engine(admin_url, future=True, isolation_level="AUTOCOMMIT")

        with admin_engine.connect() as c:
            c.execute(text(f'CREATE DATABASE "{tmp_db}"'))

        tmp_url = url.set(database=tmp_db)
        env = dict(os.environ)
        env["DATABASE_URL"] = str(tmp_url)

        p = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_migration_roundtrip.py")],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        out = ((p.stdout or "") + (p.stderr or "")).strip()

        with admin_engine.connect() as c:
            c.execute(
                text(
                    "select pg_terminate_backend(pid) from pg_stat_activity where datname=:d and pid <> pg_backend_pid()"
                ),
                {"d": tmp_db},
            )
            c.execute(text(f'DROP DATABASE IF EXISTS "{tmp_db}"'))

        return StepResult("Migration roundtrip (temp DB)", "PASS" if p.returncode == 0 else "FAIL", out)
    except Exception as ex:  # noqa: BLE001
        return StepResult("Migration roundtrip (temp DB)", "SKIP", f"{type(ex).__name__}: {ex}")

def _roundtrip_on_explicit_db() -> StepResult:
    """Run validate_migration_roundtrip.py against an explicitly provided DB URL.

    Use-case: environments where DB credentials are scoped to a specific database
    and cannot create/drop temporary databases.
    """
    url = os.environ.get("C87_ROUNDTRIP_DATABASE_URL")
    if not url:
        return StepResult(
            "Migration roundtrip (explicit DB)",
            "SKIP",
            "C87_ROUNDTRIP_DATABASE_URL not set.",
        )

    env = dict(os.environ)
    env["DATABASE_URL"] = url
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_migration_roundtrip.py")],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    return StepResult("Migration roundtrip (explicit DB)", "PASS" if p.returncode == 0 else "FAIL", out)


def write_report(results: list[StepResult]) -> Path:
    report = ROOT / "VALIDATION_REPORT.md"
    url = os.environ.get("DATABASE_URL", "")
    rt_url = os.environ.get("C87_ROUNDTRIP_DATABASE_URL", "")
    lines = []
    lines.append("## coin87 — Full Validation Report")
    lines.append("")
    lines.append(f"- **timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **database_url (redacted)**: `{_redact_db_url(url)}`" if url else "- **database_url**: (missing)")
    if rt_url:
        lines.append(f"- **roundtrip_database_url (redacted)**: `{_redact_db_url(rt_url)}`")
    lines.append("")
    lines.append("### Results")
    lines.append("")
    for r in results:
        lines.append(f"- **{r.name}**: **{r.status}**")
        if r.details:
            lines.append("")
            lines.append("```")
            lines.append(r.details[:6000])
            lines.append("```")
    lines.append("")
    lines.append("### Summary")
    lines.append("")
    failed = [r for r in results if r.status == "FAIL"]
    skipped = [r for r in results if r.status == "SKIP"]
    if not failed:
        lines.append("- **overall**: **PASS** (no failed checks)")
    else:
        lines.append(f"- **overall**: **FAIL** ({len(failed)} failed)")
    if skipped:
        lines.append(f"- **skipped**: {', '.join(r.name for r in skipped)}")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    load_env_if_present()
    if "DATABASE_URL" not in os.environ:
        print("Missing DATABASE_URL (set env var or create .env).")
        return 2

    results: list[StepResult] = []
    results.append(_connectivity_check())
    results.append(_ensure_migrated_head())
    results.append(_run_db_inspect())
    results.append(_run_pytest_backend())
    results.append(_run_ui_scan())
    # Prefer explicit roundtrip DB if provided (non-privileged environments).
    explicit = _roundtrip_on_explicit_db()
    results.append(explicit)
    if explicit.status == "SKIP":
        results.append(_try_roundtrip_on_temp_db_subprocess_env())

    report = write_report(results)
    print(f"Wrote {report}")

    return 0 if all(r.status != "FAIL" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

