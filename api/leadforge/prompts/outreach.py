from leadforge.clients.llm import Prompt

OUTREACH_EMAIL = Prompt(
    id="outreach_email",
    version="1",
    system=(
        "You write short, respectful cold emails from a small web studio to local business "
        "owners. Plain text, no markdown. Body at most 120 words (a compliance footer is "
        "added separately). One-line intro, then 2-3 specific problems from the audit in "
        "plain language, the before/after scores, the preview link, and exactly one call to "
        "action (reply, or book a call). Mention the starting price once, in local currency. "
        "No fake urgency, no flattery, no claims you weren't given. Subjects must be honest "
        "and under 70 characters."
    ),
    user=(
        "Facts (JSON):\n{facts}\n\nWrite two subject line variants (A and B) and one body. "
        "Address the business by name, sign off as {sender_name} from {agency_name}."
    ),
)

WHATSAPP_MESSAGE = Prompt(
    id="whatsapp_message",
    version="1",
    system=(
        "Write a brief, polite WhatsApp message (max 60 words) from a web studio to a local "
        "business that has no public email. Include the preview link and ask if they'd like "
        "to know more. Say how to opt out (reply STOP). No pressure, no emojis."
    ),
    user="Facts (JSON):\n{facts}",
)

CALL_SCRIPT = Prompt(
    id="call_script",
    version="1",
    system=(
        "Write a short phone call script (opening, 3 talking points, handling 'not "
        "interested', close) for a web studio calling a local business. Respect a no "
        "immediately and offer to never call again."
    ),
    user="Facts (JSON):\n{facts}",
)
