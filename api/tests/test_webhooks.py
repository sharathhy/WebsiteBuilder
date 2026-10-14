import base64
import hashlib
import hmac
import time

from leadforge.routers.webhooks import verify_svix

SECRET = "whsec_" + base64.b64encode(b"super-secret-key").decode()


def _sign(body: bytes, ts: int, msg_id: str = "msg_1") -> dict[str, str]:
    sig = hmac.new(b"super-secret-key", f"{msg_id}.{ts}.".encode() + body, hashlib.sha256)
    return {
        "svix-id": msg_id,
        "svix-timestamp": str(ts),
        "svix-signature": "v1," + base64.b64encode(sig.digest()).decode(),
    }


def test_valid_signature() -> None:
    body = b'{"type":"email.bounced"}'
    now = int(time.time())
    assert verify_svix(SECRET, _sign(body, now), body, now)


def test_tampered_or_stale_signature_rejected() -> None:
    body = b'{"type":"email.bounced"}'
    now = int(time.time())
    assert not verify_svix(SECRET, _sign(body, now), body + b" ", now)
    assert not verify_svix(SECRET, _sign(body, now - 3600), body, now)
    assert not verify_svix(SECRET, {}, body, now)
