from datetime import UTC, datetime
from typing import Any

from sqlalchemy import String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from dsa_api.core.database import Base
from dsa_api.core.ownership import OWNER_DEFAULT


class AnalysisRunORM(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNDERSTANDING")
    state_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    #: R-08: whose row this is. Non-null with a server default so the startup ALTER can backfill it, and
    #: deliberately not in `to_dict` -- scoping is a server-side predicate, not a field a client reads.
    owner: Mapped[str] = mapped_column(
        String(64), nullable=False, default=OWNER_DEFAULT, server_default=text(f"'{OWNER_DEFAULT}'")
    )

    def to_dict(self) -> dict[str, Any]:
        import json

        state = json.loads(self.state_json) if self.state_json else None
        return {
            "id": self.id,
            "dataset_id": self.dataset_id,
            "dataset_path": self.dataset_path,
            "user_query": self.user_query,
            "status": self.status,
            "state": state,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
