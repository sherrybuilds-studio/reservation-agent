# reservation-agent

A WhatsApp assistant that takes table bookings for a restaurant, runs its waitlist and reminders, and answers menu questions from the restaurant's own data.

[![CI](https://github.com/sherrybuilds-studio/reservation-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/sherrybuilds-studio/reservation-agent/actions/workflows/ci.yml)

## What it does

- **Bookings.** Rule-based parsing of party size, day and time in German and English, a check against the restaurant's booking slots and capacity, then a confirmation number. A full slot puts the guest on the waitlist and suggests the nearest free slot.
- **Waitlist.** When a guest cancels by replying NEIN to a reminder, the first guest on the waitlist whose party fits gets a WhatsApp message and 15 minutes to reply JA. A JA books the table. A NEIN, or no answer once the expiry job has run, passes it to the next guest.
- **Reminders.** 24-hour and 2-hour reminders on the restaurant's local clock. Replying JA confirms, NEIN cancels and frees the slot for the waitlist.
- **Menu questions.** Retrieval over the menu, policies and FAQ in `data/menu.json`, then a short reply from an LLM in the guest's language (German by default).
- **Owner side.** Daily and weekly reports go to the owner on Telegram, as do alerts for new Google reviews with a drafted reply. A slow-night offer can be broadcast to past guests on WhatsApp.

The repo ships with a fictional demo restaurant, Demo Restaurant Berlin, with a Turkish menu. Its phone number is deliberately invalid and its web addresses are on example.com.

## Architecture

```text
guest (WhatsApp)
   │
   ▼
Meta Cloud API ──POST /webhook──▶ agents/api.py (FastAPI, port 8001)
                                   · HMAC-SHA256 signature check (X-Hub-Signature-256)
                                   · slowapi rate limits per IP address: 10 a minute on POST, 30 on GET
                                   · prompt-injection phrase filter (a blocked message still gets HTTP 200)
                                   ▼
                          agents/bot.py
                           · rule-based intent detection before any LLM call
                           · booking flow: reservations/availability.py, booking.py, waitlist.py, reminders.py
                           · otherwise: rag/retriever.py (0.7 semantic + 0.3 keyword, ChromaDB + all-MiniLM-L6-v2)
                             → OpenRouter (anthropic/claude-3.5-haiku) with agents/system_prompt.md
                           · rag/cache.py: semantic cache, only for guests without conversation state
                                   ▼
                          Supabase: reservations, customers, waitlist,
                                    broadcast_log, review_log, analytics (setup.sql)

restaurant.py   the restaurant block of data/menu.json: identity, hours, capacity, timezone
clock.py        UTC for stored timestamps, the restaurant's local time for booking dates and times

Scheduled jobs (plain functions; this repo ships no scheduler configuration):
  reservations/reminders.py        24-hour and 2-hour reminders
  reservations/waitlist.py         expire_stale_notifications() passes unanswered offers on
  automations/reviews.py           post-visit review request
  automations/broadcast.py         slow-night offer to past guests
  automations/review_monitor.py    new Google reviews → Telegram alert to the owner
  automations/review_responder.py  drafts a reply for the owner to approve (never posts)
  automations/reports.py           daily and weekly covers report
```

## What's verified

| Check | Result | Evidence |
| --- | --- | --- |
| Retrieval eval: 10 gold questions (dishes, allergens, prices, vegan and vegetarian options, opening hours, reservation policy, waitlist, specials, location; one asked in German) | 10 of 10 pass against a 100% threshold, average top retrieval score 0.6552 | [evals/2026-10-01-retrieval-eval.json](evals/2026-10-01-retrieval-eval.json), index rebuilt first. CI re-runs the eval on every push and pull request and fails below the threshold. |
| Unit tests: intent detection; party size, day and time parsing; slot and capacity rules; booking flow; waitlist order and confirm window; reminder replies and timing; cache rules; webhook handshake, signature check and injection filter; `setup.sql` against every column the code uses | pass | [tests/](tests/), run by CI on every push and pull request |
| Lint | ruff clean | [pyproject.toml](pyproject.toml), run by CI |

The eval and the unit tests run offline: no LLM, Supabase, WhatsApp, Telegram or Google calls. The tests replace Supabase with an in-memory stand-in and fail if anything attempts HTTP. The eval only needs the embedding model, downloaded once. What they do not cover: the quality of the LLM's replies, and the real external services.

## Run it

Tested on Python 3.12.

```bash
git clone https://github.com/sherrybuilds-studio/reservation-agent.git
cd reservation-agent
python3.12 -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # optional, CPU-only torch is a much smaller download
pip install -r requirements-dev.txt   # runtime dependencies plus pytest and ruff; production needs requirements.txt only

pytest -q                    # unit tests, offline
python -m rag.indexer        # build the ChromaDB index from data/menu.json
python -m tests.eval         # retrieval eval, exits 1 below its threshold

cp .env.example .env         # fill in the values you need
set -a; . ./.env; set +a     # nothing reads .env by itself
python -m agents.api         # webhook on port 8001
```

Database: run `setup.sql` once in the Supabase SQL editor.

## Configuration

**The restaurant.** Everything that names the restaurant reads one place: the `restaurant` block of `data/menu.json` (name, address, phone, e-mail, website, review link, opening hours, capacity, timezone). `restaurant.py` loads it. The system prompt is a template filled from it, and guest messages, reminders, owner reports, review drafts and the retrieval index use the same values.

**Environment variables** (names only; see `.env.example`):

| Variable | Used by |
| --- | --- |
| `OPENROUTER_API_KEY` | chat replies, review reply drafts |
| `SUPABASE_URL`, `SUPABASE_KEY` | all tables |
| `RESTAURANT_ID` | key for this restaurant's rows in shared tables, default `demo-restaurant` |
| `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` | sending WhatsApp messages |
| `VERIFY_TOKEN` | Meta's webhook handshake; without it the handshake always fails |
| `WHATSAPP_APP_SECRET` | the signature check; without it every POST to `/webhook` is refused with 503 |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_OWNER_CHAT_ID` | owner alerts and reports |
| `GOOGLE_API_KEY`, `GOOGLE_PLACE_ID` | review monitor; no defaults, it checks nothing until both are set |

Without the WhatsApp or Telegram settings, messages are printed to the log instead of sent.

## Adapting it to a restaurant

1. `data/menu.json`: the `restaurant` block, the menu, specials and FAQ. FAQ answers can use `{name}`, `{address}`, `{email}` and the other placeholders listed in `restaurant.py`.
2. `agents/system_prompt.md`: tone, languages and the upsell examples, which name dishes from the demo menu.
3. `reservations/availability.py`: `TIME_SLOTS` and the rule that there is no lunch service Monday to Thursday. Keep them in line with the opening hours in `menu.json`; the code does not derive one from the other.
4. `tests/eval.py`: gold questions and expected keywords for the new menu.
5. `AVERAGE_SPEND_PER_COVER` in `automations/reports.py` and `automations/broadcast.py`, so the reports' revenue estimate fits the restaurant.
6. Rebuild the index with `python -m rag.indexer`, then run `pytest -q` and `python -m tests.eval`.

## Limits

- Not deployed. No real guest traffic has gone through it.
- This repo ships no scheduler configuration. The reminder, waitlist, review, broadcast and report jobs are plain functions that something has to call on a schedule.
- Review replies are drafts only. Posting to Google needs the Business Profile API with owner OAuth, which is not built. The review monitor has not been run against Google.
- Revenue figures in reports are estimates: covers times a fixed average spend per cover, not till data. The broadcast report also assumes a fixed party size per booking.
- The booking parser understands today, tomorrow, the day after tomorrow and weekday names, not calendar dates written as day and month. A request for such a date goes to the LLM, which cannot book.
- A guest cancels by replying NEIN to a reminder. A cancellation written in free text goes to the LLM, which cannot change bookings.
- Conversation state (a booking in progress, recent messages) lives in memory and is lost on restart.
- Rate limits are keyed by IP address. Behind Meta's servers or a proxy, all guests share them.

## License

MIT, see [LICENSE](LICENSE).

Shehryar Irfan · [sherrybuilds.com](https://sherrybuilds.com) · [sherry.aiops@gmail.com](mailto:sherry.aiops@gmail.com)
