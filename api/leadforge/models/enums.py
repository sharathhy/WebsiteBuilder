import enum


class Role(enum.StrEnum):
    ADMIN = "admin"
    REVIEWER = "reviewer"


class CampaignStatus(enum.StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class LeadStatus(enum.StrEnum):
    NEW = "new"
    ENRICHED = "enriched"
    AUDITED = "audited"
    REBUILD_QUEUED = "rebuild_queued"
    SITE_READY = "site_ready"
    CONTACTED = "contacted"
    WON = "won"
    LOST = "lost"
    SUPPRESSED = "suppressed"


class ContactKind(enum.StrEnum):
    EMAIL = "email"
    PHONE = "phone"
    WHATSAPP = "whatsapp"
    SOCIAL = "social"


class ContactSource(enum.StrEnum):
    PLACES = "places"
    MAILTO = "mailto"
    PAGE_TEXT = "page_text"
    JSON_LD = "json_ld"
    MANUAL = "manual"


class WebsiteStatus(enum.StrEnum):
    PENDING = "pending"
    OK = "ok"
    PARKED = "parked"
    CHALLENGE = "challenge"  # Cloudflare or similar bot wall
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"
    BLOCKED_BY_ROBOTS = "blocked_by_robots"


class AuditStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Grade(enum.StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class Viewport(enum.StrEnum):
    DESKTOP_1440 = "desktop_1440"
    MOBILE_390 = "mobile_390"


class GeneratedSiteStatus(enum.StrEnum):
    QUEUED = "queued"
    GENERATING = "generating"
    DEPLOYING = "deploying"
    LIVE = "live"
    FAILED_GATE = "failed_gate"
    MANUAL_REVIEW = "manual_review"
    EXPIRED = "expired"
    HANDED_OFF = "handed_off"


class OutreachChannel(enum.StrEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    CALL_SCRIPT = "call_script"


class DraftStatus(enum.StrEnum):
    DRAFTED = "drafted"
    APPROVED = "approved"
    SENT = "sent"
    REPLIED = "replied"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"


class EmailEventType(enum.StrEnum):
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    COMPLAINED = "complained"


class JobQueue(enum.StrEnum):
    DISCOVER = "discover"
    ENRICH = "enrich"
    AUDIT = "audit"
    GENERATE = "generate"
    DEPLOY = "deploy"
    EMAIL = "email"


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"  # will be retried
    DEAD = "dead"  # exhausted retries; dead-letter


class ApiProvider(enum.StrEnum):
    GOOGLE_PLACES = "google_places"
    PAGESPEED = "pagespeed"
    ANTHROPIC = "anthropic"
    VERCEL = "vercel"
    HIGGSFIELD = "higgsfield"
    RESEND = "resend"
    UNSPLASH = "unsplash"
