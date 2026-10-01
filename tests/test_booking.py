"""Creating reservations, directly and through the bot's multi-turn booking flow."""
import re

from reservations import booking

GUEST = "491700000001"


def test_create_reservation_stores_a_confirmed_booking_and_counts_visits(db):
    first = booking.create_reservation("Anna Schmidt", GUEST, 2, "2026-10-02", "20:00")
    booking.create_reservation("Anna Schmidt", GUEST, 4, "2026-10-09", "19:00")

    stored = db.rows("reservations")[0]
    assert stored["restaurant_id"] == "demo-restaurant" and stored["status"] == "confirmed"
    assert re.fullmatch(r"RES-\d{4}", first["confirmation_number"])
    [customer] = db.rows("customers")
    assert customer["name"] == "Anna Schmidt" and customer["visit_count"] == 2


def test_reservation_flow_asks_for_the_name_then_books(db, bot, offline_llm, frozen_today):
    # Everything but the name: the LLM is left to ask for it.
    assert bot.process_message(GUEST, "Tisch für 2 Personen am Freitag um 20 Uhr") == "LLM reply"
    assert db.rows("reservations") == []

    reply = bot.process_message(GUEST, "Anna Schmidt")

    assert "Anna Schmidt" in reply and "RES-" in reply
    [row] = db.rows("reservations")
    booked = (row["customer_name"], row["party_size"], row["date"], row["time"])
    assert booked == ("Anna Schmidt", 2, "2026-10-02", "20:00")
    assert GUEST not in bot._pending_reservations


def test_full_slot_puts_the_guest_on_the_waitlist(db, bot, offline_llm, frozen_today):
    full_slot = {"date": "2026-10-02", "time": "20:00", "party_size": 60, "status": "confirmed"}
    db.seed("reservations", {"restaurant_id": "demo-restaurant", **full_slot})
    bot.process_message(GUEST, "Tisch für 2 Personen am Freitag um 20 Uhr")
    reply = bot.process_message(GUEST, "Anna Schmidt")

    assert "Warteliste" in reply
    assert "Der nächste freie Tisch wäre:" in reply and "um 20:30 Uhr" in reply
    [entry] = db.rows("waitlist")
    assert (entry["name"], entry["party_size"], entry["status"]) == ("Anna Schmidt", 2, "waiting")
    assert len(db.rows("reservations")) == 1  # only the booking that filled the slot
