# Reservation Agent — restaurant AI assistant

> **Status (2026-08-25):** public snapshot (May 2026) of the WhatsApp variant. The
> current production version runs on Telegram inside a private platform monorepo
> with a shared core and eval gates in CI — retrieval eval **10/10** on a fresh
> index on 2026-08-25. Live products + dated evidence: [sherrybuilds.com](https://sherrybuilds.com)
> · the newer sibling product, an AI phone receptionist, answers calls at **+1 650 479 7535**.

## What it does
Reservations, menu questions, no-show prevention, and owner reporting for a
restaurant, grounded in the restaurant's own menu data via RAG.

| Feature | What it means for the restaurant |
|---|---|
| 24/7 WhatsApp + website chat | Never misses a customer inquiry |
| Smart reservations | Books tables, sends RES-XXXX confirmation |
| No-show prevention | 24h + 2h reminders, auto-releases table |
| Waitlist management | Fills cancelled slots automatically |
| Empty night broadcast | Tuesday 5pm WhatsApp blast to past customers — fills slow nights |
| Google review shield | Instant Telegram alert for every new review, 🚨 URGENT flag for 1-2 stars |
| AI review responses | Claude drafts German response for owner to approve |
| Daily owner report | Telegram summary every morning — covers, revenue, cancellations |
| Menu RAG | Answers allergen, price, ingredient questions from ChromaDB |
| Multilingual | German, English, Turkish, Arabic auto-detected |

## Tech stack
- **AI** — Claude Haiku via OpenRouter (3.5 in this snapshot; 4.5 in the current version — 3.5 was retired 2026-07)
- **Vector DB** — ChromaDB with all-MiniLM-L6-v2 embeddings
- **Search** — Hybrid semantic + keyword (70/30)
- **Backend** — FastAPI + uvicorn on port 8001
- **Database** — Supabase PostgreSQL
- **Security** — HMAC-SHA256 webhook verification, slowapi rate limiting, prompt injection blocking
- **Automation** — n8n workflows for reminders, broadcasts, review monitoring
- **Messaging** — Meta WhatsApp Cloud API

## Eval score (retrieval-only, no LLM — re-run 2026-08-25)
RESULTS: 10/10 passed
SCORE:   100%
AVG RETRIEVAL SCORE: 0.6464

## File structure
restaurant-bot/
├── agents/          # bot.py, api.py, system_prompt.md
├── automations/     # broadcast.py, reviews.py, review_monitor.py, review_responder.py, reports.py
├── reservations/    # booking.py, availability.py, waitlist.py, reminders.py
├── rag/             # indexer.py, retriever.py, cache.py
├── data/            # menu.json (25 items, 46 indexed docs)
└── tests/           # eval.py (10 gold standard questions)

## Pricing (for clients, May 2026)
- **Setup:** €2,500 (one-time)
- **Monthly retainer:** €400/month
- Includes: WhatsApp integration, menu RAG setup, Supabase tables, n8n workflows, owner Telegram dashboard

## Built by
[sherrybuilds-studio](https://github.com/sherrybuilds-studio) — Berlin-based AI automation developer
