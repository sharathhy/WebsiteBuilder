# Decisions and open questions

Defaults chosen in Phase 1 until the owner confirms. Change them in `config/` or here.

| # | Question | Current default |
| --- | --- | --- |
| 1 | Agency name, sender, physical address | `LeadForge Studio`; sender and address are `TODO` in `config/agency.yaml`. The Phase 7 sender will refuse to send while any value starts with `TODO`. |
| 2 | First categories and leads per city | Dentists, restaurants, salons/spas enabled; 60 per city × category (the Places API maximum per query). |
| 3 | Pricing tiers | ₹15k / ₹35k / ₹75k and $499 / $1,299 / $2,999. |
| 4 | Generated-site framework | Next.js App Router. |
| 5 | Sending | Dedicated sending domain via Resend (not bought yet). |
| 6 | Monthly budget cap | $50 total across Google APIs, LLM and Higgsfield; enforced from `api_usage` in Phase 8 (tracked from Phase 2). |

## Technical choices

- **ARQ over Celery:** async-native like FastAPI, Redis only, small. One worker per queue so heavy queues (audit, generate) scale independently.
- **Enums as VARCHAR + CHECK** rather than native Postgres enums, so adding a status is a cheap migration.
- **Austin enabled** in `targets.yaml` because the acceptance test uses "dentists in Austin", although Austin was not in the original Tier-1 list.
- **Places Text Search caps at 60 results per query**, so `max_results_per_target` is capped at 60. Larger cities can be split into sub-areas in Phase 2 if needed.
