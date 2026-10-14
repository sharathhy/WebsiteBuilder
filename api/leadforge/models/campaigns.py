import uuid
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from leadforge.db.base import Base, Timestamps, UUIDPk, str_enum
from leadforge.models.enums import CampaignStatus


class Campaign(UUIDPk, Timestamps, Base):
    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[CampaignStatus] = mapped_column(
        str_enum(CampaignStatus, "campaign_status"), default=CampaignStatus.DRAFT
    )
    # Snapshot of the (city x category) targets this campaign runs, taken from config/targets.yaml.
    cities: Mapped[list[Any]] = mapped_column(default=list)
    categories: Mapped[list[Any]] = mapped_column(default=list)
    radius_m: Mapped[int] = mapped_column(Integer, default=15000)
    max_results_per_target: Mapped[int] = mapped_column(Integer, default=60)
    rebuild_threshold: Mapped[int] = mapped_column(Integer, default=60)
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


# A business can be found by several campaigns; the business row itself is global
# (keyed by place_id).
campaign_businesses = Table(
    "campaign_businesses",
    Base.metadata,
    Column("campaign_id", Uuid, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("business_id", Uuid, ForeignKey("businesses.id", ondelete="CASCADE"), primary_key=True),
    Column("found_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
