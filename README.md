# reservation-agent

A WhatsApp assistant for restaurants. It takes table reservations, runs a waitlist, sends reminders, and answers menu questions from a retrieval index.
It ships with a demo Turkish restaurant: 30 menu items plus specials, policies and FAQ in `data/menu.json`. Replies are in German by default, or in the guest's language (English, Turkish, Arabic).
Retrieval passes 10 of 10 gold questions (eval dated 2026-09-02). The bot is built and tested but not deployed.

Author: Shehryar Irfan · [sherrybuilds.com](https://sherrybuilds.com) · [sherry.aiops@gmail.com](mailto:sherry.aiops@gmail.com)

---

## Architecture

```
guest (WhatsApp)
   │
   ▼
Meta Cloud API ──POST /webhook──▶ agents/api.py (FastAPI, :8001)
                                   · HMAC-SHA256 signature check (X-Hub-Signature-256)
                                   · slowapi: 10/min on POST, 30/min on GET
                                   · prompt-injection pattern filter
                                   ▼
                          agents/bot.py
                           · rule-based intent detection before any LLM call
                           · reservation flow: date/time/party extraction → reservations/booking.py
                           · otherwise: rag/retriever.py (0.7 semantic + 0.3 keyword, ChromaDB + MiniLM)
                             → OpenRouter (anthropic/claude-3.5-haiku) with agents/system_prompt.md
                                   ▼
                          Supabase: reservations, customers, waitlist,
                                    broadcast_log, review_log, analytics (setup.sql)

Scheduled jobs (plain functions; any scheduler can call them, no workflows are in this repo):
  reservations/reminders.py      24h and 2h reminders, guest replies confirm or cancel
  reservations/waitlist.py       notify next guest when a slot frees, 15-minute confirm window
  automations/broadcast.py       slow-night offer to past guests
  automations/review_monitor.py  new Google reviews → Telegram alert to the owner
  automations/review_responder.py  drafts a reply for the owner to approve (never posts)
  automations/reports.py         daily and weekly covers report to Telegram (revenue is an estimate: covers × a fixed €35)
```

## What's verified

| Check | Result | Evidence |
|---|---|---|
| Menu retrieval, 10 gold questions (dishes, allergens, prices, vegan and vegetarian, hours, group policy, location, one in German) | 10/10, average retrieval score 0.646 | [ai-systems-portfolio/evals/2026-09-02-restaurant-bot-eval.json](https://github.com/sherrybuilds-studio/ai-systems-portfolio/blob/main/evals/2026-09-02-restaurant-bot-eval.json) (2026-09-02, offline, index rebuilt first) |

The dated run used the current copy of this code in my private monorepo, with the same `tests/eval.py` and menu. The eval checks retrieval only. It needs no LLM, Supabase or WhatsApp. Reservation, reminder and broadcast flows have no automated tests in this repo.

## Run it

```bash
git clone https://github.com/sherrybuilds-studio/reservation-agent.git
cd reservation-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # fill in values; names below
python3 rag/indexer.py            # build the ChromaDB index from data/menu.json
python3 tests/eval.py             # retrieval gate, offline
python3 -m agents.api             # webhook on :8001 (needs the WhatsApp and Supabase variables)
```

Database: run `setup.sql` once in the Supabase SQL editor.

Environment variables (names only):

| Variable | Used by |
|---|---|
| `OPENROUTER_API_KEY` | chat replies, review reply drafts |
| `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` | sending messages |
| `VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` | webhook handshake and signature check |
| `SUPABASE_URL`, `SUPABASE_KEY`, `RESTAURANT_ID` | all tables |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_CHAT_ID` | owner alerts and reports |
| `GOOGLE_API_KEY`, `GOOGLE_PLACE_ID` | review monitor (Google Places) |

## Limits

- Not deployed. No real guest traffic has gone through it.
- The system prompt and review responder are written for one demo restaurant. Using it for another restaurant means editing `agents/system_prompt.md`, `data/menu.json` and the name in `automations/review_responder.py`.
- The schedules for reminders, broadcasts and review checks are described in code comments, but this repo ships no scheduler configuration.
- Review replies are drafts only. Posting to Google needs the Business Profile API with owner OAuth, which is not built.

## License

MIT
