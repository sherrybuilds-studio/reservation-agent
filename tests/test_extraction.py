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


def test_minutes_are_kept(bot, frozen_today):
    assert bot._extract_reservation_details("Tisch für 2 Personen am Freitag um 19:30")["time"] == "19:30"
    assert bot._extract_reservation_details("A table for 3 people at 19:30")["time"] == "19:30"


def test_greeting_and_relative_days(bot, frozen_today):
    def date_of(message):
        return bot._extract_reservation_details(message).get("date")

    assert date_of("Guten Morgen! Tisch für 2 Personen am Samstag um 20 Uhr") == "2026-10-03"
    assert date_of("Tisch für 4 Personen übermorgen um 19 Uhr") == "2026-10-03"
    assert date_of("A table for 4 tonight at 7pm") == "2026-10-01"


def test_german_am_is_not_a_clock_time(bot, frozen_today):
    # "am Samstag" means "on Saturday": these are party sizes, not 12 a.m. or 3 p.m.
    assert bot._extract_reservation_details("Tisch für 12 am Samstag") == {"party_size": 12, "date": "2026-10-03"}
    assert "time" not in bot._extract_reservation_details("Wir sind 15 am Freitag")
    english = bot._extract_reservation_details("A table for 4 tonight at 7pm")
    assert english == {"party_size": 4, "time": "19:00", "date": "2026-10-01"}
