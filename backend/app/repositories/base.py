"""Read-only repository base.

Institutional rationale:
- Repositories are the only layer permitted to query the database.
- Read-only discipline is enforced to protect auditability and prevent accidental
  mutation in request paths.
"""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar, Union, cast

from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.sql import Executable
from sqlalchemy.sql.dml import Delete, Insert, Update
from sqlalchemy.sql.selectable import Select


class RepositoryReadOnlyViolation(RuntimeError):
    """Raised when a repository detects a write or mutation attempt."""


SessionLike = Union[Session, AsyncSession]
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base repository providing a guarded execute helper.

    - Accepts Session or AsyncSession.
    - Enforces read-only discipline: SELECT statements only.
    - Prevents accidental flush state (new/dirty/deleted) during query execution.
    """

    def __init__(self, session: SessionLike) -> None:
        self._session: SessionLike = session

    def _sync_session(self) -> Session:
        if isinstance(self._session, AsyncSession):
            return cast(Session, self._session.sync_session)
        return cast(Session, self._session)

    def _assert_clean_uow(self) -> None:
        """Reject queries if the session has pending writes."""
        s = self._sync_session()
        if s.new or s.dirty or s.deleted:
            raise RepositoryReadOnlyViolation(
                "Repository layer is read-only: session has pending changes "
                f"(new={len(s.new)}, dirty={len(s.dirty)}, deleted={len(s.deleted)})."
            )

    def _assert_select_only(self, stmt: Executable) -> None:
        """Reject any non-SELECT statement."""
        if isinstance(stmt, (Insert, Update, Delete)):
            raise RepositoryReadOnlyViolation("Repository layer is read-only: DML is forbidden.")
        if not isinstance(stmt, Select):
            raise RepositoryReadOnlyViolation(
                f"Repository layer is read-only: only SELECT statements are allowed (got {type(stmt)!r})."
            )

    async def _execute(self, stmt: Executable, *, params: Optional[dict[str, Any]] = None) -> Result[Any]:
        """Execute a SELECT statement safely against Session or AsyncSession."""
        self._assert_select_only(stmt)
        self._assert_clean_uow()

        if isinstance(self._session, AsyncSession):
            result = await self._session.execute(stmt, params or {})
        else:
            # NOTE: If used in async contexts, caller must ensure sync session executes
            # in an appropriate threadpool. Repository remains transport-agnostic.
            result = self._sync_session().execute(stmt, params or {})

        self._assert_clean_uow()
        return result

