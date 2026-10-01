"""setup.sql must have every column the code reads or writes."""
import re
from pathlib import Path

from automations import broadcast, reports, review_monitor, review_responder, reviews
from reservations import availability, booking, reminders, waitlist

SETUP_SQL = Path(__file__).resolve().parent.parent / "setup.sql"
GUEST = "guest-1"


def _schema():
    """{table: {column, ...}} from the create table statements in setup.sql."""
    tables = {}
    for table, body in re.findall(r"create table (\w+) \((.*?)\);", SETUP_SQL.read_text(), flags=re.S | re.I):
        tables[table] = {definition.split()[0] for definition in body.split(",") if definition.strip()}
    return tables


def _run_every_query(db):
    """Calls each function that talks to Supabase once, along the paths that write."""
    booking.create_reservation("Anna", GUEST, 2, "2026-10-02", "20:00")
    booking.create_reservation("Anna", GUEST, 2, "2026-10-09", "20:00")  # returning guest: customer update
    booking.get_reservation(phone=GUEST)
    booking.get_reservations_for_date("2026-10-02")
    booking.cancel_reservation("RES-0000", phone=GUEST)
    booking.mark_no_show("RES-0000")
    availability.check_availability("2026-10-02", "20:00", 2)

    waitlist.add_to_waitlist(GUEST, "Anna", 2, "2026-10-03", "20:00")
    waitlist.notify_waitlist("2026-10-03", "20:00", 2)
    waitlist.expire_stale_notifications()
    waitlist.find_open_offer(GUEST)
    waitlist.get_waitlist("2026-10-03", "20:00")
    waitlist.remove_from_waitlist(phone=GUEST, date="2026-10-03", time="20:00")

    # The restaurant's clock reads 2026-10-01 12:00 (frozen_today).
    db.seed(
        "reservations",
        *({"restaurant_id": "demo-restaurant", "phone": phone, "customer_name": "Ben", "party_size": 2,
           "date": "2026-10-01", "time": time, "status": "confirmed", "confirmation_number": "RES-1111"}
          for phone, time in (("in-two-hours", "14:00"), ("two-hours-ago", "10:00"))),
    )
    reminders.send_reminder_24h()
    reminders.send_reminder_2h()
    reminders.send_review_request(GUEST, "Anna", reservation_id=1)
    reminders.process_reminder_reply(GUEST, "JA")
    reviews.run_post_visit_reviews()

    broadcast.send_broadcast("Heute Abend {discount}% Rabatt", customers=[{"phone": GUEST, "name": "Anna"}])
    broadcast.get_past_customers(slow_days_only=True)
    broadcast.track_broadcast_result(GUEST, "booked")
    broadcast.generate_broadcast_report()
    reports.generate_daily_report()
    reports.generate_weekly_report()

    review = {"review_id": "r1", "reviewer_name": "Eva", "stars": 5, "text": "Sehr gut", "time": "2026-10-01T10:00:00"}
    review_monitor.send_review_alert(review)
    review_monitor._get_seen_review_ids()
    review_monitor._update_weekly_stats([review])
    review_monitor.generate_weekly_review_report()


def test_setup_sql_has_every_column_the_code_uses(db, monkeypatch, frozen_today):
    # Every send succeeds, so the paths that record a send run too.
    for module in (reminders, reviews, broadcast):
        monkeypatch.setattr(module, "_send_whatsapp", lambda phone, message: True)
    for module in (broadcast, reports, review_monitor):
        monkeypatch.setattr(module, "_send_telegram", lambda message: True)
    monkeypatch.setattr(review_responder, "draft_response", lambda text, stars: "Danke!")

    _run_every_query(db)

    schema = _schema()
    missing = sorted(f"{table}.{column}" for table, column in db.columns_used if column not in schema.get(table, ()))
    assert not missing, f"setup.sql lacks {', '.join(missing)}"
