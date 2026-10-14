"""Discover: Places Text Search per (city, category), with pagination, upsert and dedup."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from leadforge.clients.places import SearchQuery
from leadforge.models import Business, Campaign, campaign_businesses
from leadforge.models.enums import ApiProvider, JobQueue, LeadStatus
from leadforge.pipeline.context import JobContext
from leadforge.pipeline.registry import PermanentError, handler
from leadforge.services.contacts import normalize_phone
from leadforge.services.dedup import domain_of, find_duplicate, normalize_name
from leadforge.services.targets import load_targets
from leadforge.services.usage import ensure_budget, record_usage


def _component(place: dict[str, Any], kind: str, short: bool = False) -> str | None:
    for comp in place.get("addressComponents", []):
        if kind in comp.get("types", []):
            value = comp.get("shortText" if short else "longText") or comp.get("longText")
            return str(value) if value else None
    return None


def apply_place(
    biz: Business, place: dict[str, Any], *, city: str, state: str, country: str, category: str
) -> None:
    biz.name = place.get("displayName", {}).get("text") or biz.name
    biz.normalized_name = normalize_name(biz.name)
    biz.category = category
    biz.address = place.get("formattedAddress") or biz.address or ""
    biz.city = _component(place, "locality") or city
    biz.state = _component(place, "administrative_area_level_1") or state
    biz.country = (_component(place, "country", short=True) or country)[:2].upper()
    loc = place.get("location") or {}
    biz.lat, biz.lng = loc.get("latitude"), loc.get("longitude")
    intl = place.get("internationalPhoneNumber")
    biz.phone_national = place.get("nationalPhoneNumber")
    biz.phone_e164 = normalize_phone(intl, biz.country) if intl else None
    biz.website = place.get("websiteUri")
    biz.domain = domain_of(biz.website)
    biz.has_website = bool(biz.website)
    biz.rating = place.get("rating")
    biz.review_count = place.get("userRatingCount")
    biz.business_status = place.get("businessStatus")
    biz.hours = place.get("regularOpeningHours")
    biz.google_maps_url = place.get("googleMapsUri")
    biz.primary_type = place.get("primaryType")
    biz.places_raw = place
    biz.places_fetched_at = datetime.now(UTC)


async def _link(ctx: JobContext, campaign: Campaign, biz: Business) -> None:
    dialect = ctx.db.get_bind().dialect.name
    insert = pg_insert if dialect == "postgresql" else sqlite_insert
    stmt = insert(campaign_businesses).values(campaign_id=campaign.id, business_id=biz.id)
    await ctx.db.execute(stmt.on_conflict_do_nothing())


@handler("discover")
async def discover(ctx: JobContext) -> dict[str, Any]:
    p = ctx.job.payload
    campaign = await ctx.db.get(Campaign, ctx.job.campaign_id)
    if campaign is None:
        raise PermanentError("campaign not found")
    targets = load_targets()
    city = next((c for c in targets.cities if c.id == p["city_id"]), None)
    category = next((c for c in targets.categories if c.id == p["category_id"]), None)
    if city is None or category is None:
        raise PermanentError(f"unknown target {p['city_id']} x {p['category_id']}")

    max_results = min(
        campaign.max_results_per_target,
        category.max_results_per_target or targets.defaults.max_results_per_target,
    )
    query = SearchQuery(
        text=f"{category.query} in {city.name}, {city.state}",
        lat=city.lat,
        lng=city.lng,
        radius_m=city.radius_m or campaign.radius_m,
        city_id=city.id,
        city_name=city.name,
        state=city.state,
        country=city.country,
        category_id=category.id,
    )

    seen = created = duplicates = 0
    token: str | None = None
    while seen < max_results:
        if not ctx.services.mock:
            await ensure_budget(ctx.db, ApiProvider.GOOGLE_PLACES, 0.035)
        page = await ctx.services.places.search_text(query, token)
        await record_usage(
            ctx.db,
            ApiProvider.GOOGLE_PLACES,
            "text_search",
            cost_usd=page.cost_usd,
            mocked=page.mocked,
            job_id=ctx.job.id,
            meta={"query": query.text},
        )
        for place in page.places[: max_results - seen]:
            seen += 1
            if place.get("businessStatus") == "CLOSED_PERMANENTLY":
                continue
            biz = await ctx.db.scalar(select(Business).where(Business.place_id == place["id"]))
            if biz is None:
                biz = Business(
                    place_id=place["id"],
                    name="",
                    normalized_name="",
                    address="",
                    city=city.name,
                    country=city.country,
                    category=category.id,
                )
                ctx.db.add(biz)
                created += 1
            apply_place(
                biz,
                place,
                city=city.name,
                state=city.state,
                country=city.country,
                category=category.id,
            )
            await ctx.db.flush()
            await _link(ctx, campaign, biz)
            if biz.duplicate_of_id is None:
                dup = await find_duplicate(ctx.db, biz)
                if dup is not None:
                    biz.duplicate_of_id = dup.id
                    biz.lead_status = LeadStatus.SUPPRESSED
                    duplicates += 1
            await ctx.db.commit()
            if biz.duplicate_of_id is None:
                await ctx.enqueue(
                    JobQueue.ENRICH,
                    "enrich",
                    f"enrich:{biz.id}:{campaign.id}",
                    {"business_id": str(biz.id)},
                    business_id=biz.id,
                )
        token = page.next_page_token
        if not token:
            break
    await ctx.db.commit()
    return {"seen": seen, "created": created, "duplicates": duplicates, "query": query.text}
