import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from leadforge.models.enums import (
    CampaignStatus,
    DraftStatus,
    GeneratedSiteStatus,
    LeadStatus,
    OutreachChannel,
)

NOT_FOUND = "not found"


class CampaignIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    cities: list[str] = Field(min_length=1)
    categories: list[str] = Field(min_length=1)
    radius_m: int = Field(15000, ge=500, le=50000)
    max_results_per_target: int = Field(60, ge=1, le=60)
    rebuild_threshold: int = Field(60, ge=0, le=100)


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: CampaignStatus
    cities: list[str]
    categories: list[str]
    radius_m: int
    max_results_per_target: int
    rebuild_threshold: int
    created_at: datetime


class CampaignProgress(BaseModel):
    campaign: CampaignOut
    jobs: dict[str, dict[str, int]]  # queue -> status -> count
    leads: dict[str, int]  # lead_status -> count
    total_leads: int


class LeadRow(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    city: str
    state: str | None
    country: str
    address: str
    phone: str
    email: str
    email_source_url: str | None
    email_confidence: float | None
    website: str
    maps_url: str | None
    rating: float | None
    review_count: int | None
    score: int | None
    grade: str | None
    lead_status: LeadStatus
    has_website: bool
    preview_url: str | None
    places_fetched_at: datetime | None
    enriched_at: datetime | None
    audited_at: datetime | None


class LeadPage(BaseModel):
    items: list[LeadRow]
    total: int
    page: int
    page_size: int


class DraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    business_name: str | None = None
    to: str | None = None
    channel: OutreachChannel
    variant: str
    subject: str | None
    body: str
    status: DraftStatus
    sequence_day: int
    scheduled_for: datetime | None
    approved_at: datetime | None
    sent_at: datetime | None
    created_at: datetime
    preview_url: str | None = None
    score_before: int | None = None
    score_after: int | None = None


class DraftEdit(BaseModel):
    subject: str | None = Field(None, max_length=200)
    body: str | None = Field(None, min_length=1, max_length=5000)


class ApproveIn(BaseModel):
    # Queue the send immediately (still subject to suppression, daily limit and agency checks).
    send_now: bool = True


class MarkIn(BaseModel):
    status: DraftStatus


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    template: str
    status: GeneratedSiteStatus
    attempts: int
    preview_url: str | None
    score: int | None
    baseline_score: int | None
    expires_at: datetime | None
    failure_reason: str | None
    page_parity: dict[str, Any] | None = None
    created_at: datetime


class LeadDetail(BaseModel):
    lead: LeadRow
    business: dict[str, Any]
    contacts: list[dict[str, Any]]
    website: dict[str, Any] | None
    audits: list[dict[str, Any]]
    sites: list[SiteOut]
    drafts: list[DraftOut]
    jobs: list[dict[str, Any]]
