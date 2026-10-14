from pathlib import Path

import httpx
import pytest

from conftest import ADMIN, REVIEWER, login
from leadforge.services.targets import load_targets

pytestmark = pytest.mark.usefixtures("users")


def test_repo_config_is_valid() -> None:
    cfg = load_targets(Path(__file__).resolve().parents[2] / "config" / "targets.yaml")
    countries = {c.country for c in cfg.cities}
    assert countries == {"IN", "US"}
    ids = {c.id for c in cfg.cities}
    assert {"bengaluru", "austin", "mumbai", "new-york", "san-francisco"} <= ids
    assert len(cfg.categories) == 14


async def test_get_targets(client: httpx.AsyncClient) -> None:
    headers = await login(client, REVIEWER)
    resp = await client.get("/api/config/targets", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["defaults"]["rebuild_threshold"] == 60


async def test_admin_updates_targets(client: httpx.AsyncClient, config_dir: Path) -> None:
    headers = await login(client, ADMIN)
    cfg = (await client.get("/api/config/targets", headers=headers)).json()
    cfg["defaults"]["rebuild_threshold"] = 55
    for city in cfg["cities"]:
        if city["id"] == "miami":
            city["enabled"] = True
    resp = await client.put("/api/config/targets", json=cfg, headers=headers)
    assert resp.status_code == 200
    saved = load_targets(config_dir / "targets.yaml")
    assert saved.defaults.rebuild_threshold == 55
    assert next(c for c in saved.cities if c.id == "miami").enabled


async def test_invalid_targets_rejected(client: httpx.AsyncClient, config_dir: Path) -> None:
    headers = await login(client, ADMIN)
    cfg = (await client.get("/api/config/targets", headers=headers)).json()
    before = (config_dir / "targets.yaml").read_text()
    cfg["cities"].append(dict(cfg["cities"][0]))  # duplicate id
    assert (await client.put("/api/config/targets", json=cfg, headers=headers)).status_code == 422
    cfg["cities"].pop()
    cfg["defaults"]["max_results_per_target"] = 500  # Places caps at 60
    assert (await client.put("/api/config/targets", json=cfg, headers=headers)).status_code == 422
    assert (config_dir / "targets.yaml").read_text() == before


async def test_reviewer_cannot_update_targets(client: httpx.AsyncClient) -> None:
    headers = await login(client, REVIEWER)
    cfg = (await client.get("/api/config/targets", headers=headers)).json()
    assert (await client.put("/api/config/targets", json=cfg, headers=headers)).status_code == 403
