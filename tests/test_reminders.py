"""Reminder jobs and the guest's replies to them."""
from datetime import datetime

import clock
from reservations import reminders


def _confirmed(phone, time, date="2026-10-01"):
    return {
        "restaurant_id": "demo-restaurant", "phone": phone, "customer_name": "Anna", "party_size": 2,
        "date": date, "time": time, "status": "confirmed", "confirmation_number": "RES-1234",
    }


def test_two_hour_reminder_uses_the_restaurants_clock(db, monkeypatch):
    # Bookings are stored in local time. 18:00 in Berlin is 16:00 UTC in October (summer time).
    monkeypatch.setattr(clock, "local_now", lambda: datetime(2026, 10, 1, 18, 0))
    monkeypatch.setattr(clock, "utc_now", lambda: datetime(2026, 10, 1, 16, 0))
    sent = []
    monkeypatch.setattr(reminders, "_send_whatsapp", lambda phone, message: sent.append(phone) or True)
    db.seed("reservations", _confirmed("in-two-hours", "20:00"), _confirmed("in-half-an-hour", "18:30"))

    assert reminders.send_reminder_2h() == 1
    assert sent == ["in-two-hours"]


def test_replies_with_punctuation_or_a_polite_word_count(db, frozen_today):
    db.seed(
        "reservations",
        _confirmed("guest-a", "20:00", date="2026-10-02"),
        _confirmed("guest-b", "20:00", date="2026-10-02"),
        _confirmed("guest-c", "20:00", date="2026-10-02"),
    )
    assert reminders.process_reminder_reply("guest-a", "Ja!") == "confirmed"
    assert reminders.process_reminder_reply("guest-b", "Nein, danke") == "cancelled"
    assert reminders.process_reminder_reply("guest-c", "No vegan options?") == "unknown"  # a question, not an answer

    statuses = {row["phone"]: row["status"] for row in db.rows("reservations")}
    assert statuses == {"guest-a": "confirmed", "guest-b": "cancelled", "guest-c": "confirmed"}


def test_a_reply_only_changes_this_restaurants_booking(db, frozen_today):
    elsewhere = {**_confirmed("guest", "19:00", date="2026-10-01"), "restaurant_id": "another-restaurant"}
    db.seed("reservations", elsewhere, _confirmed("guest", "20:00", date="2026-10-02"))

    assert reminders.process_reminder_reply("guest", "NEIN") == "cancelled"

    statuses = [(row["restaurant_id"], row["status"]) for row in db.rows("reservations")]
    assert statuses == [("another-restaurant", "confirmed"), ("demo-restaurant", "cancelled")]
