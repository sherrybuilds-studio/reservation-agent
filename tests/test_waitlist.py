"""Waitlist order and the confirm window after a table frees up."""
from datetime import UTC, datetime, timedelta

from reservations import waitlist

DATE, TIME = "2026-10-02", "20:00"


def _utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


def _entry(name, party_size, created_at, **fields):
    row = {
        "restaurant_id": "demo-restaurant", "phone": f"phone-{name}", "name": name, "party_size": party_size,
        "date": DATE, "time": TIME, "status": "waiting", "created_at": created_at,
    }
    return {**row, **fields}


def _statuses(db):
    return {row["name"]: row["status"] for row in db.rows("waitlist")}


def test_guest_is_added_once_per_slot(db):
    first = waitlist.add_to_waitlist("guest-1", "Anna", 2, DATE, TIME)
    again = waitlist.add_to_waitlist("guest-1", "Anna", 2, DATE, TIME)
    assert again["id"] == first["id"]
    assert len(db.rows("waitlist")) == 1


def test_free_table_goes_to_the_earliest_guest_who_fits(db):
    db.seed(
        "waitlist",
        _entry("Berta", 6, "2026-09-30T10:00:00"),  # first in line, but too many people for the freed table
        _entry("Cem", 2, "2026-09-30T10:05:00"),
        _entry("Dana", 2, "2026-09-30T10:10:00"),
    )

    notified = waitlist.notify_waitlist(DATE, TIME, 4)

    assert notified["name"] == "Cem"
    assert _statuses(db) == {"Berta": "waiting", "Cem": "notified", "Dana": "waiting"}
    cem = next(row for row in db.rows("waitlist") if row["name"] == "Cem")
    window = datetime.fromisoformat(cem["expires_at"]) - datetime.fromisoformat(cem["notified_at"])
    assert abs(window - timedelta(minutes=waitlist.CONFIRM_WINDOW_MINUTES)) < timedelta(seconds=1)
    assert waitlist.CONFIRM_WINDOW_MINUTES == 15


def test_expired_offer_moves_to_the_next_guest(db):
    now = _utcnow()
    db.seed(
        "waitlist",
        _entry("Cem", 2, "2026-09-30T10:05:00", status="notified",
               notified_at=(now - timedelta(minutes=20)).isoformat(),
               expires_at=(now - timedelta(minutes=5)).isoformat()),
        _entry("Dana", 2, "2026-09-30T10:10:00"),
    )

    waitlist.expire_stale_notifications()

    assert _statuses(db) == {"Cem": "expired", "Dana": "notified"}


def test_offer_inside_the_window_is_left_alone(db):
    now = _utcnow()
    db.seed(
        "waitlist",
        _entry("Cem", 2, "2026-09-30T10:05:00", status="notified",
               notified_at=(now - timedelta(minutes=5)).isoformat(),
               expires_at=(now + timedelta(minutes=10)).isoformat()),
        _entry("Dana", 2, "2026-09-30T10:10:00"),
    )

    waitlist.expire_stale_notifications()

    assert _statuses(db) == {"Cem": "notified", "Dana": "waiting"}


def test_expiry_job_only_touches_this_restaurant(db):
    now = _utcnow()
    db.seed(
        "waitlist",
        _entry("Other", 2, "2026-09-30T10:00:00", restaurant_id="another-restaurant", status="notified",
               notified_at=(now - timedelta(minutes=20)).isoformat(),
               expires_at=(now - timedelta(minutes=5)).isoformat()),
        _entry("Dana", 2, "2026-09-30T10:10:00"),
    )

    waitlist.expire_stale_notifications()

    # Another restaurant's offer is its own job's business, and its free table is not ours to offer.
    assert _statuses(db) == {"Other": "notified", "Dana": "waiting"}


def _offer(name, phone, minutes_left):
    """A guest who was told a table is free, with minutes_left of the confirm window (negative: expired)."""
    now = _utcnow()
    return _entry(name, 2, "2026-09-30T10:05:00", phone=phone, status="notified",
                  notified_at=(now - timedelta(minutes=15 - minutes_left)).isoformat(),
                  expires_at=(now + timedelta(minutes=minutes_left)).isoformat())


def test_ja_inside_the_window_books_the_offered_table(db, bot, offline_llm, frozen_today):
    db.seed("waitlist", _offer("Cem", "guest-5", minutes_left=10), _offer("Eva", "guest-6", minutes_left=-2))

    reply = bot.process_message("guest-5", "JA")

    assert "RES-" in reply and "am Freitag, 2. Oktober 2026 um 20:00 Uhr" in reply
    [booking] = db.rows("reservations")
    assert (booking["customer_name"], booking["date"], booking["time"]) == ("Cem", DATE, TIME)
    assert offline_llm.llm == []  # answered by the booking logic, not left to the LLM

    # Eva's window has closed: her JA books nothing; the expiry job passes her offer on.
    bot.process_message("guest-6", "JA")
    assert len(db.rows("reservations")) == 1
    assert _statuses(db) == {"Cem": "booked", "Eva": "notified"}


def test_nein_passes_the_offer_to_the_next_guest(db, bot, offline_llm, frozen_today):
    db.seed("waitlist", _offer("Cem", "guest-5", minutes_left=10), _entry("Dana", 2, "2026-09-30T10:10:00"))

    bot.process_message("guest-5", "Nein danke")

    assert _statuses(db) == {"Cem": "declined", "Dana": "notified"}
    assert db.rows("reservations") == []
