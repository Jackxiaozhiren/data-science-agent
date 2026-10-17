from datetime import UTC, datetime
from typing import Any

from sqlalchemy import String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from dsa_api.core.database import Base
from dsa_api.core.ownership import OWNER_DEFAULT


class ExperimentORM(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    params_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: R-08: whose row this is. Non-null with a server default so the startup ALTER can backfill it, and
    #: deliberately not in `to_dict` -- scoping is a server-side predicate, not a field a client reads.
    owner: Mapped[str] = mapped_column(
        String(64), nullable=False, default=OWNER_DEFAULT, server_default=text(f"'{OWNER_DEFAULT}'")
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        import json

        return {
            "id": self.id,
            "run_id": self.run_id,
            "dataset_id": self.dataset_id,
            "name": self.name,
            "params": json.loads(self.params_json) if self.params_json else {},
            "metrics": json.loads(self.metrics_json) if self.metrics_json else {},
            "artifact_path": self.artifact_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
