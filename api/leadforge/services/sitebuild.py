"""Build a SiteSpec into a static site: Next.js templates (primary) or static fallback."""

import asyncio
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from leadforge.core.config import Settings
from leadforge.schemas.site_spec import SiteSpec
from leadforge.services.static_site import write_redirects, write_site


@dataclass
class BuildResult:
    out_dir: Path
    builder: str
    first_load_js_kb: float | None
    log_tail: str


class BuildError(RuntimeError):
    pass


def next_available(settings: Settings) -> bool:
    site = settings.templates_dir / "site"
    return (
        (site / "package.json").exists()
        and (site / "node_modules").exists()
        and bool(shutil.which("npm"))
    )


def choose_builder(settings: Settings) -> str:
    if settings.site_builder == "auto":
        return "next" if next_available(settings) else "static"
    return settings.site_builder


_BUILD_LOCK = asyncio.Lock()


def _lock_file(f: IO[str], lock: bool) -> None:
    """Exclusive cross-process lock on an open file (fcntl on Linux/macOS, msvcrt on Windows)."""
    if sys.platform == "win32":
        import msvcrt

        f.seek(0)
        if not lock:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
            return
        while True:  # LK_LOCK gives up after ~10 s; a build can take minutes
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]
                return
            except OSError:
                continue
    else:
        import fcntl

        fcntl.flock(f, fcntl.LOCK_EX if lock else fcntl.LOCK_UN)


def _npm() -> str:
    # On Windows npm is npm.cmd; resolve the full path so subprocess can start it.
    return shutil.which("npm") or "npm"


async def _run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        return 124, "build timed out"
    return proc.returncode or 0, out.decode(errors="replace")


async def build_site(
    settings: Settings, spec: SiteSpec, assets: dict[str, bytes], *, slug: str, base_path: str
) -> BuildResult:
    work = settings.storage_dir / "builds" / slug
    if work.exists():
        shutil.rmtree(work)
    builder = choose_builder(settings)
    if builder == "static":
        out = write_site(spec, work / "out", assets)
        return BuildResult(out, "static", 0.0, "")

    # Next/Turbopack won't resolve a symlinked node_modules outside the project root, so builds
    # run in the template checkout itself, one at a time (a file lock covers every worker).
    template = settings.templates_dir / "site"
    work.mkdir(parents=True, exist_ok=True)
    lock_path = template / ".build.lock"
    async with _BUILD_LOCK:
        with lock_path.open("w") as lock:
            await asyncio.to_thread(_lock_file, lock, True)
            try:
                gen = template / "public" / "generated"
                shutil.rmtree(gen, ignore_errors=True)
                gen.mkdir(parents=True)
                for name, data in assets.items():
                    (gen / name).write_bytes(data)
                spec_path = work / "site.json"
                spec_path.write_text(json.dumps(spec.model_dump(mode="json"), indent=2))
                env = {
                    **os.environ,
                    "SITE_SPEC": str(spec_path),
                    "BASE_PATH": base_path,
                    "NEXT_TELEMETRY_DISABLED": "1",
                }
                code, log = await _run([_npm(), "run", "build"], template, env, timeout=900)
                if code != 0 or not (template / "out" / "index.html").exists():
                    raise BuildError(f"next build failed ({code}): {log[-1500:]}")
                budget_code, budget_log = await _run(
                    [_npm(), "run", "check:budget"], template, env, timeout=120
                )
                shutil.copytree(template / "out", work / "out")
                write_redirects(spec, work / "out")
            finally:
                shutil.rmtree(template / "public" / "generated", ignore_errors=True)
                _lock_file(lock, False)
    js_kb = None
    for line in budget_log.splitlines():
        if "KB" in line and any(ch.isdigit() for ch in line):
            digits = "".join(ch if ch.isdigit() or ch == "." else " " for ch in line).split()
            if digits:
                js_kb = float(digits[0])
                break
    if budget_code != 0:
        raise BuildError(f"first-load JS budget exceeded: {budget_log[-500:]}")
    return BuildResult(work / "out", "next", js_kb, log[-1000:])
