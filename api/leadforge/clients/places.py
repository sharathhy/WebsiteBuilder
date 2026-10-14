"""Google Places API (New) Text Search. Official API only; never scrape Maps HTML."""

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from leadforge.fixtures import mock_world

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Only the fields we store. Each field tier is billed separately, so keep this tight.
FIELD_MASK = (
    ",".join(
        f"places.{f}"
        for f in (
            "id",
            "displayName",
            "formattedAddress",
            "addressComponents",
            "location",
            "nationalPhoneNumber",
            "internationalPhoneNumber",
            "websiteUri",
            "rating",
            "userRatingCount",
            "businessStatus",
            "regularOpeningHours",
            "googleMapsUri",
            "primaryType",
        )
    )
    + ",nextPageToken"
)

# Text Search with contact/atmosphere fields bills at the Enterprise tier.
COST_PER_REQUEST_USD = 0.035


@dataclass
class SearchQuery:
    text: str
    lat: float
    lng: float
    radius_m: int
    # Mock-mode context: lets the fixture world produce matching businesses.
    city_id: str = ""
    city_name: str = ""
    state: str = ""
    country: str = ""
    category_id: str = ""


@dataclass
class SearchPage:
    places: list[dict[str, Any]]
    next_page_token: str | None
    cost_usd: float
    mocked: bool


class PlacesClient(Protocol):
    async def search_text(self, query: SearchQuery, page_token: str | None) -> SearchPage: ...


class GooglePlacesClient:
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self.api_key = api_key
        self.client = client or httpx.AsyncClient(timeout=30)

    async def search_text(self, query: SearchQuery, page_token: str | None) -> SearchPage:
        body: dict[str, Any] = {
            "textQuery": query.text,
            "pageSize": 20,
            "locationBias": {
                "circle": {
                    "center": {"latitude": query.lat, "longitude": query.lng},
                    "radius": float(min(query.radius_m, 50_000)),
                }
            },
        }
        if page_token:
            body["pageToken"] = page_token
        resp = await self.client.post(
            TEXT_SEARCH_URL,
            json=body,
            headers={"X-Goog-Api-Key": self.api_key, "X-Goog-FieldMask": FIELD_MASK},
        )
        resp.raise_for_status()
        data = resp.json()
        return SearchPage(
            places=data.get("places", []),
            next_page_token=data.get("nextPageToken"),
            cost_usd=COST_PER_REQUEST_USD,
            mocked=False,
        )


class MockPlacesClient:
    """Serves the deterministic fixture world in pages of 20, like the real API."""

    PER_TARGET = 30

    async def search_text(self, query: SearchQuery, page_token: str | None) -> SearchPage:
        all_places = [
            mock_world.places_payload(b)
            for b in mock_world.businesses_for(
                query.city_id,
                query.city_name,
                query.state,
                query.country,
                query.lat,
                query.lng,
                query.category_id,
                self.PER_TARGET,
            )
        ]
        start = int(page_token or 0)
        end = start + 20
        return SearchPage(
            places=all_places[start:end],
            next_page_token=str(end) if end < len(all_places) else None,
            cost_usd=COST_PER_REQUEST_USD,
            mocked=True,
        )
