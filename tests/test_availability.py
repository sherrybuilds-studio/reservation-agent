"""Capacity per slot and which slots are offered. The demo restaurant has 60 covers."""
from reservations import availability

FRIDAY = "2026-10-02"
MONDAY = "2026-10-05"


def _booking(party_size, status="confirmed", restaurant_id="demo-restaurant", time="20:00"):
    return {"restaurant_id": restaurant_id, "date": FRIDAY, "time": time, "party_size": party_size, "status": status}


def test_only_active_bookings_of_this_restaurant_use_capacity(db):
    db.seed(
        "reservations",
        _booking(40),
        _booking(10),
        _booking(8, status="cancelled"),
        _booking(30, restaurant_id="another-restaurant"),
    )
    fits = availability.check_availability(FRIDAY, "20:00", 10)
    assert fits["available"] and fits["covers_used"] == 50 and fits["remaining"] == 10
    assert not availability.check_availability(FRIDAY, "20:00", 11)["available"]


def test_full_slot_suggests_the_next_free_slot(db):
    db.seed("reservations", _booking(60))
    result = availability.check_availability(FRIDAY, "20:00", 2)
    assert not result["available"]
    assert result["next_available"].endswith("um 20:30 Uhr")


def test_no_lunch_slots_monday_to_thursday(db):
    monday = availability.get_available_slots(MONDAY, 2)
    friday = availability.get_available_slots(FRIDAY, 2)
    assert monday[0] == "17:00" and "12:00" not in monday
    assert friday[0] == "12:00"
