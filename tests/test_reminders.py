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
