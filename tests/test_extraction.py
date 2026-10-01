"""Date, time and party size read from a guest's message. TODAY in conftest is Thursday 2026-10-01."""


def test_german_request_gives_party_day_and_time(bot, frozen_today):
    details = bot._extract_reservation_details("Tisch für 4 Personen am Freitag um 20 Uhr")
    assert details == {"party_size": 4, "time": "20:00", "date": "2026-10-02"}


def test_english_request_with_pm_time_and_tomorrow(bot, frozen_today):
    details = bot._extract_reservation_details("A table for 2 people tomorrow at 8pm")
    assert details == {"party_size": 2, "time": "20:00", "date": "2026-10-02"}


def test_weekday_that_is_today_means_next_week(bot, frozen_today):
    assert bot._extract_reservation_details("Tisch am Donnerstag")["date"] == "2026-10-08"


def test_hours_outside_service_are_not_read_as_times(bot, frozen_today):
    assert "time" not in bot._extract_reservation_details("Um 9 Uhr bitte")
