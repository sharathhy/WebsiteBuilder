import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import or_, select

from leadforge.core.deps import AdminUser, CurrentUser, DbSession
from leadforge.models import Business, SuppressionEntry
from leadforge.models.enums import LeadStatus
from leadforge.services import outreach as ox
from leadforge.services.contacts import normalize_phone
from leadforge.services.suppression import suppress

router = APIRouter(prefix="/suppression", tags=["outreach"])


class SuppressionIn(BaseModel):
    email: str | None = Field(None, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    domain: str | None = Field(None, max_length=255, pattern=r"^[a-z0-9.-]+\.[a-z]{2,}$")
    phone: str | None = Field(None, max_length=40)
    reason: str = Field("manual", max_length=100)

    @model_validator(mode="after")
    def _one(self) -> "SuppressionIn":
        if not (self.email or self.domain or self.phone):
            raise ValueError("Give an email, domain or phone")
        return self


class SuppressionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    domain: str | None
    phone_e164: str | None
    reason: str
    source: str | None
    created_at: datetime


@router.get("", response_model=list[SuppressionOut])
async def list_entries(_: CurrentUser, db: DbSession) -> list[SuppressionEntry]:
    return list(
        await db.scalars(select(SuppressionEntry).order_by(SuppressionEntry.created_at.desc()))
    )


@router.post("", response_model=SuppressionOut, status_code=status.HTTP_201_CREATED)
async def add_entry(body: SuppressionIn, user: CurrentUser, db: DbSession) -> SuppressionEntry:
    phone = normalize_phone(body.phone, "ZZ") if body.phone else None
    if body.phone and not phone:
        raise HTTPException(422, "Phone must include a country code, e.g. +1 512 555 0100")
    entry = await suppress(db, email=body.email, domain=body.domain, phone_e164=phone,
                           reason=body.reason, source=f"user:{user.email}")  # fmt: skip
    # Stop anything already queued for matching businesses.
    conds = []
    if entry.email:
        conds.append(Business.primary_email == entry.email)
    if entry.domain:
        conds += [Business.domain == entry.domain, Business.primary_email.like(f"%@{entry.domain}")]
    if entry.phone_e164:
        conds.append(Business.phone_e164 == entry.phone_e164)
    for biz in await db.scalars(select(Business).where(or_(*conds))):
        await ox.cancel_pending(db, biz.id, "suppressed")
        biz.lead_status = LeadStatus.SUPPRESSED
    await db.commit()
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_entry(entry_id: uuid.UUID, _: AdminUser, db: DbSession) -> None:
    entry = await db.get(SuppressionEntry, entry_id)
    if entry is None:
        raise HTTPException(404, "Not found")
    await db.delete(entry)
    await db.commit()
