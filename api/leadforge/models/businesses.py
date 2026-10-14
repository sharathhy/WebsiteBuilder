import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from leadforge.db.base import Base, Timestamps, UUIDPk, str_enum
from leadforge.models.enums import ContactKind, ContactSource, LeadStatus, WebsiteStatus

NOT_FOUND = "not_found"


class Business(UUIDPk, Timestamps, Base):
    """A local business discovered via the Google Places API. place_id is the durable key."""

    __tablename__ = "businesses"
    __table_args__ = (
        Index("ix_businesses_city_category", "city", "category"),
        Index("ix_businesses_phone_e164", "phone_e164"),
        Index("ix_businesses_domain", "domain"),
    )

    place_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    # Lowercased, punctuation-free name used for fuzzy dedup.
    normalized_name: Mapped[str] = mapped_column(String(300), index=True)
    category: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(2))  # ISO 3166-1 alpha-2
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    phone_national: Mapped[str | None] = mapped_column(String(40))
    phone_e164: Mapped[str | None] = mapped_column(String(20))
    website: Mapped[str | None] = mapped_column(String(2048))
    domain: Mapped[str | None] = mapped_column(String(255))
    has_website: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[float | None] = mapped_column(Float)
    review_count: Mapped[int | None] = mapped_column(Integer)
    business_status: Mapped[str | None] = mapped_column(String(40))
    hours: Mapped[dict[str, Any] | None] = mapped_column()
    google_maps_url: Mapped[str | None] = mapped_column(String(2048))
    lead_status: Mapped[LeadStatus] = mapped_column(
        str_enum(LeadStatus, "lead_status"), default=LeadStatus.NEW
    )
    # Set when fuzzy dedup decides this row is the same business as another.
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("businesses.id", ondelete="SET NULL")
    )
    primary_type: Mapped[str | None] = mapped_column(String(100))
    # Denormalized for the leads table: best public email, or "not_found" with when we looked.
    primary_email: Mapped[str | None] = mapped_column(String(320))
    email_status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending"
    )  # found|not_found
    email_confidence: Mapped[float | None] = mapped_column(Float)
    email_source_url: Mapped[str | None] = mapped_column(String(2048))
    latest_score: Mapped[int | None] = mapped_column(Integer, index=True)
    latest_grade: Mapped[str | None] = mapped_column(String(2))
    places_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    audited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Raw Places payload, kept within Google's caching terms and refreshed periodically.
    places_raw: Mapped[dict[str, Any] | None] = mapped_column()


class Contact(UUIDPk, Timestamps, Base):
    """A publicly published contact point. Every row records where it was found."""

    __tablename__ = "contacts"
    __table_args__ = (
        Index("uq_contacts_business_kind_value", "business_id", "kind", "value", unique=True),
    )

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[ContactKind] = mapped_column(str_enum(ContactKind, "contact_kind"))
    value: Mapped[str] = mapped_column(String(2048))  # normalized: lowercase email, E.164 phone
    label: Mapped[str | None] = mapped_column(String(100))  # e.g. "instagram", "info@"
    source: Mapped[ContactSource] = mapped_column(str_enum(ContactSource, "contact_source"))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    is_role_address: Mapped[bool | None] = mapped_column(Boolean)
    mx_valid: Mapped[bool | None] = mapped_column(Boolean)
    is_disposable: Mapped[bool | None] = mapped_column(Boolean)
    found_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Website(UUIDPk, Timestamps, Base):
    __tablename__ = "websites"

    business_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("businesses.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(2048))
    final_url: Mapped[str | None] = mapped_column(String(2048))
    domain: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[WebsiteStatus] = mapped_column(
        str_enum(WebsiteStatus, "website_status"), default=WebsiteStatus.PENDING
    )
    http_status: Mapped[int | None] = mapped_column(Integer)
    is_https: Mapped[bool | None] = mapped_column(Boolean)
    robots_allowed: Mapped[bool | None] = mapped_column(Boolean)
    crawl_delay_s: Mapped[float | None] = mapped_column(Float)
    tech_stack: Mapped[list[Any]] = mapped_column(default=list)
    pages_crawled: Mapped[list[Any]] = mapped_column(default=list)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
