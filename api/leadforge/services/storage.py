"""Object storage. Local filesystem in dev (served by the API under /files);
swap for R2/S3 in production by implementing the same three methods."""

from pathlib import Path

from leadforge.core.config import get_settings


class LocalStorage:
    def __init__(self, root: Path, public_base: str) -> None:
        self.root = root
        self.public_base = public_base.rstrip("/")

    def path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("key escapes storage root")
        return p

    def put(self, key: str, data: bytes) -> str:
        p = self.path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def url(self, key: str) -> str:
        return f"{self.public_base}/files/{key}"


def get_storage() -> LocalStorage:
    s = get_settings()
    return LocalStorage(s.storage_dir, s.public_base_url)
