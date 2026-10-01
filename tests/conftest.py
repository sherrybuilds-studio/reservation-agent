"""
Shared fixtures. The unit tests run offline: no Supabase, WhatsApp, Telegram,
OpenRouter or model download. Supabase is replaced by FakeSupabase below and
any HTTP call through requests fails the test.
"""
import itertools
import operator
import os
from datetime import datetime
from types import SimpleNamespace

import pytest
import requests

# Settings are read when the app modules are imported, so clear them before any
# test module imports one. Credentials exported in a developer's shell must never
# reach a test.
for _setting in (
    "OPENROUTER_API_KEY", "SUPABASE_URL", "SUPABASE_KEY", "RESTAURANT_ID",
    "WHATSAPP_TOKEN", "WHATSAPP_PHONE_ID", "VERIFY_TOKEN", "WHATSAPP_APP_SECRET",
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_OWNER_CHAT_ID", "GOOGLE_API_KEY", "GOOGLE_PLACE_ID",
):
    os.environ.pop(_setting, None)

# A Thursday. Relative dates in guest messages ("morgen", "Freitag") resolve against it.
TODAY = datetime(2026, 10, 1, 12, 0)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fails the test if anything tries an HTTP call (the app catches the error, so it is recorded)."""
    attempts = []

    def refuse(self, method, url, *args, **kwargs):
        attempts.append(f"{method} {url}")
        raise requests.ConnectionError("network is disabled in tests")

    monkeypatch.setattr(requests.sessions.Session, "request", refuse)
    yield
    assert not attempts, f"tests must stay offline, but tried: {attempts}"


class FakeSupabase:
    """
    In-memory stand-in for the parts of the supabase-py client the code uses:
    table(), select/insert/update, eq/neq/lt/lte/gt/gte, order, limit, execute().
    It also records every (table, column) the code reads or writes.
    """

    def __init__(self):
        self.tables = {}
        self.columns_used = set()
        self._ids = itertools.count(1)

    def table(self, name):
        return _Query(self, name)

    def rows(self, name):
        return self.tables.setdefault(name, [])

    def seed(self, name, *rows):
        for row in rows:
            self.rows(name).append({"id": next(self._ids), **row})


class _Query:
    def __init__(self, db, table):
        self.db = db
        self.table = table
        self.action = "select"
        self.payload = None
        self.filters = []
        self.sort = None
        self.max_rows = None

    def _use(self, columns):
        self.db.columns_used.update((self.table, column) for column in columns)

    def select(self, columns="*"):
        if columns != "*":
            self._use(column.strip() for column in columns.split(","))
        return self

    def insert(self, payload):
        self.action, self.payload = "insert", payload
        return self

    def update(self, payload):
        self.action, self.payload = "update", payload
        self._use(payload)
        return self

    def _filter(self, compare, column, value):
        self._use([column])
        self.filters.append((compare, column, value))
        return self

    def eq(self, column, value):
        return self._filter(operator.eq, column, value)

    def neq(self, column, value):
        return self._filter(operator.ne, column, value)

    def lt(self, column, value):
        return self._filter(operator.lt, column, value)

    def lte(self, column, value):
        return self._filter(operator.le, column, value)

    def gt(self, column, value):
        return self._filter(operator.gt, column, value)

    def gte(self, column, value):
        return self._filter(operator.ge, column, value)

    def order(self, column, desc=False):
        self._use([column])
        self.sort = (column, desc)
        return self

    def limit(self, count):
        self.max_rows = count
        return self

    def _matches(self, row):
        try:
            return all(compare(row.get(column), value) for compare, column, value in self.filters)
        except TypeError:  # e.g. a missing timestamp compared with a string
            return False

    def execute(self):
        rows = self.db.rows(self.table)
        if self.action == "insert":
            inserted = []
            for row in self.payload if isinstance(self.payload, list) else [self.payload]:
                self._use(row)
                stored = {"id": next(self.db._ids), **row}
                rows.append(stored)
                inserted.append(dict(stored))
            return SimpleNamespace(data=inserted)

        matched = [row for row in rows if self._matches(row)]
        if self.action == "update":
            for row in matched:
                row.update(self.payload)
        elif self.sort:
            column, desc = self.sort
            matched.sort(key=lambda row: str(row.get(column) or ""), reverse=desc)
        if self.max_rows is not None:
            matched = matched[: self.max_rows]
        return SimpleNamespace(data=[dict(row) for row in matched])


@pytest.fixture
def db(monkeypatch):
    """A fresh FakeSupabase wired into every module that talks to Supabase."""
    from automations import broadcast, reports, review_monitor, reviews
    from reservations import availability, booking, reminders, waitlist

    fake = FakeSupabase()
    for module in (availability, booking, reminders, waitlist, broadcast, reports, review_monitor, reviews):
        monkeypatch.setattr(module, "_get_client", lambda: fake)
    return fake


@pytest.fixture
def bot(monkeypatch):
    """agents.bot with empty conversation and reservation state."""
    from agents import bot as bot_module

    monkeypatch.setattr(bot_module, "_conversations", {})
    monkeypatch.setattr(bot_module, "_pending_reservations", {})
    return bot_module


@pytest.fixture
def offline_llm(monkeypatch, bot):
    """Stubs retrieval, the semantic cache and the OpenRouter call; records what reached them."""
    calls = SimpleNamespace(llm=[], cache_lookups=[], cache_stores=[])

    def fake_llm(messages):
        calls.llm.append(messages)
        return "LLM reply"

    monkeypatch.setattr(bot, "retrieve_for_prompt", lambda query, n_results=3: "")
    monkeypatch.setattr(bot, "cache_lookup", lambda query: calls.cache_lookups.append(query))
    monkeypatch.setattr(bot, "cache_store", lambda query, response: calls.cache_stores.append(query))
    monkeypatch.setattr(bot, "_call_openrouter", fake_llm)
    return calls


@pytest.fixture
def frozen_today(monkeypatch):
    """Makes the bot's datetime.now() return TODAY."""
    from agents import bot as bot_module

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(TODAY.year, TODAY.month, TODAY.day, TODAY.hour, TODAY.minute)

    monkeypatch.setattr(bot_module, "datetime", FrozenDatetime)
    return TODAY.date()
