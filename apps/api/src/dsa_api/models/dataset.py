from datetime import UTC, datetime
from typing import Any

from sqlalchemy import String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from dsa_api.core.database import Base
from dsa_api.core.ownership import OWNER_DEFAULT


class DatasetORM(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    rows: Mapped[int | None] = mapped_column(nullable=True)
    cols: Mapped[int | None] = mapped_column(nullable=True)
    profile_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: R-08: whose row this is. Non-null with a server default so the startup ALTER can backfill it, and
    #: deliberately not in `to_dict` -- scoping is a server-side predicate, not a field a client reads.
    owner: Mapped[str] = mapped_column(
        String(64), nullable=False, default=OWNER_DEFAULT, server_default=text(f"'{OWNER_DEFAULT}'")
    )

    def to_dict(self) -> dict[str, Any]:
        import json

        return {
            "id": self.id,
            "filename": self.filename,
            "format": self.format,
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "rows": self.rows,
            "cols": self.cols,
            "profile": json.loads(self.profile_json) if self.profile_json else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": json.loads(self.meta_json) if self.meta_json else {},
        }
