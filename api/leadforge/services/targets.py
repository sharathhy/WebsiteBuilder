"""Read and write config/targets.yaml."""

import os
import tempfile
from pathlib import Path

import yaml

from leadforge.core.config import get_settings
from leadforge.schemas.targets import TargetsConfig


def targets_path() -> Path:
    return get_settings().config_dir / "targets.yaml"


def load_targets(path: Path | None = None) -> TargetsConfig:
    with (path or targets_path()).open(encoding="utf-8") as fh:
        return TargetsConfig.model_validate(yaml.safe_load(fh))


def save_targets(config: TargetsConfig, path: Path | None = None) -> None:
    """Atomic write so a crash never leaves a half-written config."""
    path = path or targets_path()
    data = config.model_dump(mode="json", exclude_none=True)
    header = "# LeadForge discovery targets. Edited from the dashboard; safe to hand-edit too.\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".targets-", suffix=".yaml")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(header)
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)
    os.replace(tmp, path)
