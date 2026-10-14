"""Email delivery. Only ever called for drafts a human approved."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

import httpx

from leadforge.core.config import Settings


@dataclass
class OutgoingEmail:
    to: str
    from_: str
    subject: str
    text: str
    html: str
    headers: dict[str, str] = field(default_factory=dict)
    reply_to: str | None = None


class EmailSender(Protocol):
    name: str

    async def send(self, msg: OutgoingEmail) -> str: ...


class ResendSender:
    name = "resend"

    def __init__(self, api_key: str) -> None:
        self.client = httpx.AsyncClient(
            base_url="https://api.resend.com",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )

    async def send(self, msg: OutgoingEmail) -> str:
        body = {
            "from": msg.from_,
            "to": [msg.to],
            "subject": msg.subject,
            "text": msg.text,
            "html": msg.html,
            "headers": msg.headers,
        }
        if msg.reply_to:
            body["reply_to"] = msg.reply_to
        resp = await self.client.post("/emails", json=body)
        resp.raise_for_status()
        return str(resp.json()["id"])


class MockSender:
    """Writes messages to storage/outbox/ instead of sending them."""

    name = "mock"

    def __init__(self, settings: Settings) -> None:
        self.dir = settings.storage_dir / "outbox"

    async def send(self, msg: OutgoingEmail) -> str:
        self.dir.mkdir(parents=True, exist_ok=True)
        msg_id = f"mock-{uuid.uuid4().hex[:12]}"
        record = {
            "id": msg_id,
            "at": datetime.now(UTC).isoformat(),
            "to": msg.to,
            "from": msg.from_,
            "subject": msg.subject,
            "headers": msg.headers,
            "text": msg.text,
        }
        (self.dir / f"{msg_id}.json").write_text(json.dumps(record, indent=2))
        return msg_id
