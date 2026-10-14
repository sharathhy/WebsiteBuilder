"""Deploy targets for generated sites: Vercel (REST API) or local previews (mock)."""

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from leadforge.core.config import Settings
from leadforge.services.previews import preview_root

VERCEL_API = "https://api.vercel.com"


@dataclass
class DeployResult:
    url: str
    project_id: str | None
    deployment_id: str | None
    mocked: bool


class Deployer(Protocol):
    name: str

    def base_url_for(self, slug: str) -> str: ...

    async def deploy(self, slug: str, out_dir: Path, *, noindex: bool) -> DeployResult: ...

    async def remove(self, slug: str, project_id: str | None) -> None: ...


class LocalPreviewDeployer:
    """Copies the static export under storage/previews/<slug>/, served by the API."""

    name = "local"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def base_url_for(self, slug: str) -> str:
        return f"{self.settings.public_base_url.rstrip('/')}/previews/{slug}"

    async def deploy(self, slug: str, out_dir: Path, *, noindex: bool) -> DeployResult:
        target = preview_root(self.settings) / slug
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(out_dir, target)
        return DeployResult(self.base_url_for(slug) + "/", None, f"local-{slug}", mocked=True)

    async def remove(self, slug: str, project_id: str | None) -> None:
        shutil.rmtree(preview_root(self.settings) / slug, ignore_errors=True)


class VercelDeployer:
    """One Vercel project per site; static files uploaded by SHA, deployed as a preview."""

    name = "vercel"

    def __init__(self, token: str, team_id: str | None = None) -> None:
        self.client = httpx.AsyncClient(
            base_url=VERCEL_API, headers={"Authorization": f"Bearer {token}"}, timeout=120
        )
        self.params = {"teamId": team_id} if team_id else {}

    def base_url_for(self, slug: str) -> str:
        return f"https://{slug}.vercel.app"

    async def _ensure_project(self, slug: str) -> str:
        resp = await self.client.get(f"/v9/projects/{slug}", params=self.params)
        if resp.status_code == 200:
            return str(resp.json()["id"])
        resp = await self.client.post(
            "/v10/projects", params=self.params, json={"name": slug, "framework": None}
        )
        resp.raise_for_status()
        return str(resp.json()["id"])

    async def deploy(self, slug: str, out_dir: Path, *, noindex: bool) -> DeployResult:
        project_id = await self._ensure_project(slug)
        if noindex:
            (out_dir / "vercel.json").write_text(
                '{"headers":[{"source":"/(.*)","headers":[{"key":"X-Robots-Tag","value":"noindex, nofollow"}]}]}'
            )
        files = []
        for path in sorted(p for p in out_dir.rglob("*") if p.is_file()):
            data = path.read_bytes()
            sha = hashlib.sha1(data).hexdigest()  # noqa: S324 (Vercel's content digest)
            up = await self.client.post(
                "/v2/files",
                params=self.params,
                content=data,
                headers={"x-vercel-digest": sha, "Content-Type": "application/octet-stream"},
            )
            up.raise_for_status()
            files.append({"file": str(path.relative_to(out_dir)), "sha": sha, "size": len(data)})
        resp = await self.client.post(
            "/v13/deployments",
            params=self.params,
            json={
                "name": slug,
                "project": project_id,
                "files": files,
                "projectSettings": {"framework": None},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return DeployResult(f"https://{data['url']}/", project_id, data["id"], mocked=False)

    async def remove(self, slug: str, project_id: str | None) -> None:
        if project_id:
            resp = await self.client.delete(f"/v9/projects/{project_id}", params=self.params)
            if resp.status_code not in (200, 204, 404):
                resp.raise_for_status()
