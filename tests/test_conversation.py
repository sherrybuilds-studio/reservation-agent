"""What the bot may share between guests through the semantic cache."""


def test_only_replies_written_without_guest_context_are_cached(db, bot, offline_llm, frozen_today):
    # Mid-booking, a name is answered for that guest alone. This is how a guest's name and
    # booking once ended up in the shared cache file.
    bot.process_message("guest-a", "Tisch für 2 Personen am Freitag")  # time and name still missing
    bot.process_message("guest-a", "Sherry")

    # A returning guest's reply is written with their name and history in the prompt.
    db.seed("customers", {"phone": "guest-b", "name": "Anna", "visit_count": 3})
    bot.process_message("guest-b", "Habt ihr vegane Gerichte?")

    # A first question from a new guest is generic and may be reused.
    bot.process_message("guest-c", "Habt ihr vegane Gerichte?")

    assert "Sherry" not in offline_llm.cache_lookups
    assert offline_llm.cache_stores == ["Habt ihr vegane Gerichte?"]
