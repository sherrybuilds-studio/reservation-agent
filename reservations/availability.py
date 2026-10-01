import os
from datetime import datetime, timedelta

from supabase import create_client

from restaurant import RESTAURANT_ID, load_restaurant

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RESTAURANT_CAPACITY = load_restaurant().capacity

# Time slots offered (24h format strings)
TIME_SLOTS = [
    "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
    "17:00", "17:30", "18:00", "18:30", "19:00", "19:30",
    "20:00", "20:30", "21:00", "21:30", "22:00"
]

_WEEKDAYS_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
_MONTHS_DE = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

_supabase = None


def german_date(day, with_year=False):
    """'Freitag, 2. Oktober' for guest replies. strftime would print English names under the default locale."""
    text = f"{_WEEKDAYS_DE[day.weekday()]}, {day.day}. {_MONTHS_DE[day.month - 1]}"
    return f"{text} {day.year}" if with_year else text


def _get_client():
    global _supabase
    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def _covers_at_slot(date, time):
    """Returns total covers booked for a given date+time slot."""
    try:
        client = _get_client()
        result = (
            client.table("reservations")
            .select("party_size")
            .eq("restaurant_id", RESTAURANT_ID)
            .eq("date", str(date))
            .eq("time", str(time))
            .neq("status", "cancelled")
            .execute()
        )
        return sum(r["party_size"] for r in (result.data or []))
    except Exception as e:
        print(f"[availability] _covers_at_slot error: {e}")
        return 0


def _offered_slots(day):
    """Booking times on that day: no lunch service Monday to Thursday."""
    if day.weekday() < 4:
        return [slot for slot in TIME_SLOTS if int(slot.split(":")[0]) >= 17]
    return list(TIME_SLOTS)


def check_availability(date, time, party_size):
    """
    Returns dict:
      { available: True/False, reason: None | "closed" | "full", covers_used: int,
        remaining: int, capacity: int, next_available: str or None }
    reason "closed" means no booking is taken at that time at all (not one of
    TIME_SLOTS, or lunch Monday to Thursday). next_available is set only when
    available=False.
    """
    try:
        party_size = int(party_size)
        if str(time) not in _offered_slots(datetime.strptime(str(date), "%Y-%m-%d")):
            return {"available": False, "reason": "closed", "covers_used": 0, "remaining": 0,
                    "capacity": RESTAURANT_CAPACITY,
                    "next_available": _find_next_available(date, time, party_size)}

        covers_used = _covers_at_slot(date, time)
        remaining = RESTAURANT_CAPACITY - covers_used
        available = remaining >= party_size

        result = {
            "available": available,
            "reason": None if available else "full",
            "covers_used": covers_used,
            "remaining": remaining,
            "capacity": RESTAURANT_CAPACITY,
            "next_available": None
        }

        if not available:
            result["next_available"] = _find_next_available(date, time, party_size)

        return result

    except Exception as e:
        print(f"[availability] check_availability error: {e}")
        # Fail open so the bot can still take reservations if Supabase is down
        return {"available": True, "reason": None, "covers_used": 0, "remaining": RESTAURANT_CAPACITY,
                "capacity": RESTAURANT_CAPACITY, "next_available": None}


def _find_next_available(start_date, start_time, party_size):
    """
    Searches the next 7 days (starting from start_date) for the nearest
    slot that can fit party_size. Returns a human-readable string or None.
    """
    try:
        base = datetime.strptime(str(start_date), "%Y-%m-%d")

        for day_offset in range(0, 8):
            check_date = base + timedelta(days=day_offset)
            check_date_str = check_date.strftime("%Y-%m-%d")

            for slot in _offered_slots(check_date):
                # Skip the original slot on day 0
                if day_offset == 0 and slot <= start_time:
                    continue

                covers_used = _covers_at_slot(check_date_str, slot)
                if RESTAURANT_CAPACITY - covers_used >= party_size:
                    return f"{german_date(check_date)} um {slot} Uhr"

        return None

    except Exception as e:
        print(f"[availability] _find_next_available error: {e}")
        return None


def get_available_slots(date, party_size):
    """Returns a list of available time slots for a given date and party size."""
    try:
        party_size = int(party_size)
        available_slots = []

        for slot in _offered_slots(datetime.strptime(str(date), "%Y-%m-%d")):
            covers_used = _covers_at_slot(date, slot)
            if RESTAURANT_CAPACITY - covers_used >= party_size:
                available_slots.append(slot)

        return available_slots

    except Exception as e:
        print(f"[availability] get_available_slots error: {e}")
        return []
