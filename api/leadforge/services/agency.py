"""config/agency.yaml: sender identity, pricing and the monthly budget cap."""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from leadforge.core.config import get_settings


class PriceBook(BaseModel):
    currency: str
    symbol: str
    tiers: dict[str, int]


class AgencyConfig(BaseModel):
    agency_name: str
    sender_name: str
    sender_email: str
    physical_address: str
    booking_url: str
    monthly_budget_usd: float = Field(50, ge=0)
    provider_budgets_usd: dict[str, float] = Field(default_factory=dict)
    pricing: dict[str, PriceBook]

    def unfilled(self) -> list[str]:
        """Fields still holding TODO placeholders. Sending is refused while any remain."""
        fields = ("sender_name", "sender_email", "physical_address", "booking_url")
        return [f for f in fields if str(getattr(self, f)).strip().upper().startswith("TODO")]


def agency_path() -> Path:
    return get_settings().config_dir / "agency.yaml"


@lru_cache(maxsize=4)
def _load(path: str, mtime: float) -> AgencyConfig:
    with open(path, encoding="utf-8") as fh:
        return AgencyConfig.model_validate(yaml.safe_load(fh))


def load_agency() -> AgencyConfig:
    path = agency_path()
    return _load(str(path), path.stat().st_mtime)
