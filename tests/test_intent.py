"""Rule-based intent detection, which decides whether a message enters the booking flow."""
from agents.bot import detect_intent


def test_booking_requests_are_reservations():
    for message in (
        "Ich möchte einen Tisch für 4 Personen reservieren",
        "Can I book a table for tonight?",
        "Haben Sie heute Abend noch Platz?",
    ):
        assert detect_intent(message) == "reservation", message


def test_menu_questions_are_menu():
    for message in ("Haben Sie vegane Gerichte?", "Was kostet die Baklava?", "Is the kitchen halal?"):
        assert detect_intent(message) == "menu", message


def test_short_yes_no_replies_are_confirmations():
    for message in ("Ja", "NEIN", "yes"):
        assert detect_intent(message) == "confirmation", message


def test_complaints_are_flagged():
    assert detect_intent("Das Essen war schlecht und ich bin enttäuscht") == "complaint"
