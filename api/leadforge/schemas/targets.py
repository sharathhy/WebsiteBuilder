"""Validated shape of config/targets.yaml."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Slug = str


class Defaults(BaseModel):
    radius_m: int = Field(15000, ge=500, le=50000)
    max_results_per_target: int = Field(60, ge=1, le=60)
    rebuild_threshold: int = Field(60, ge=0, le=100)
    audit_cache_days: int = Field(30, ge=1, le=365)
    places_refresh_days: int = Field(30, ge=1, le=365)


class City(BaseModel):
    id: Slug = Field(pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=100)
    state: str
    country: Literal["IN", "US"]
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    enabled: bool = True
    metro: str | None = None
    radius_m: int | None = Field(None, ge=500, le=50000)


class Category(BaseModel):
    id: Slug = Field(pattern=r"^[a-z0-9-]+$")
    label: str
    query: str = Field(min_length=2, max_length=100)
    template: str
    enabled: bool = True
    max_results_per_target: int | None = Field(None, ge=1, le=60)


class TargetsConfig(BaseModel):
    defaults: Defaults = Defaults()
    cities: list[City]
    categories: list[Category]

    @model_validator(mode="after")
    def _unique_ids(self) -> "TargetsConfig":
        for name, items in (("city", self.cities), ("category", self.categories)):
            ids = [i.id for i in items]
            dupes = {i for i in ids if ids.count(i) > 1}
            if dupes:
                raise ValueError(f"duplicate {name} ids: {sorted(dupes)}")
        return self

    def enabled_targets(self) -> list[tuple[City, Category]]:
        return [
            (city, cat)
            for city in self.cities
            if city.enabled
            for cat in self.categories
            if cat.enabled
        ]
