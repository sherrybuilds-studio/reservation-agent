"""
The restaurant this assistant speaks for, read from the "restaurant" block of
data/menu.json.

The repo ships a fictional demo identity. Everything that names the restaurant
(the system prompt, guest messages, owner reports, review reply drafts and the
retrieval index) reads it from here, so adapting the bot to a real restaurant
starts with that one block.
"""
import json
import os
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

MENU_PATH = Path(__file__).resolve().parent / "data" / "menu.json"

# Key for this restaurant's rows in the shared Supabase tables.
RESTAURANT_ID = os.getenv("RESTAURANT_ID", "demo-restaurant")

_WEEK = [
    ("monday", "Mon"), ("tuesday", "Tue"), ("wednesday", "Wed"), ("thursday", "Thu"),
    ("friday", "Fri"), ("saturday", "Sat"), ("sunday", "Sun"),
]
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


@dataclass(frozen=True)
class Restaurant:
    name: str
    cuisine: str
    timezone: str  # IANA name; booking dates and times are wall-clock time here
    street: str
    postal_code: str
    city: str
    phone: str
    email: str
    website: str
    review_link: str
    capacity: int
    hours: str  # one line, e.g. "Mon–Wed 17:00–23:00 | Thu 17:00–23:30 | ..."

    @property
    def address(self):
        return f"{self.street}, {self.postal_code} {self.city}"

    def placeholders(self):
        return {
            "name": self.name,
            "cuisine": self.cuisine,
            "city": self.city,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "review_link": self.review_link,
            "capacity": str(self.capacity),
            "hours": self.hours,
        }

    def render(self, text):
        """Fills {name}, {address}, {phone} and the other placeholders in text.

        Braces around anything that is not a single word are left alone; an
        unknown {word} raises KeyError so a typo in a template fails loudly.
        """
        values = self.placeholders()

        def fill(match):
            key = match.group(1)
            if key not in values:
                raise KeyError(f"unknown placeholder {{{key}}}; known: {', '.join(sorted(values))}")
            return values[key]

        return _PLACEHOLDER.sub(fill, text)


def parse_restaurant(block):
    """Builds a Restaurant from the "restaurant" block of menu.json."""
    address = block["address"]
    contact = block["contact"]
    return Restaurant(
        name=block["name"],
        cuisine=block["cuisine"],
        timezone=block["timezone"],
        street=address["street"],
        postal_code=address["postal_code"],
        city=address["city"],
        phone=contact["phone"],
        email=contact["email"],
        website=contact["website"],
        review_link=block["review_link"],
        capacity=int(block["capacity"]),
        hours=summarise_hours(block["opening_hours"]),
    )


@cache
def load_restaurant(path=MENU_PATH):
    """Reads the restaurant block from menu.json (once per path)."""
    with open(path, encoding="utf-8") as f:
        return parse_restaurant(json.load(f)["restaurant"])


def summarise_hours(opening_hours):
    """{"monday": "17:00–23:00", ...} -> "Mon–Wed 17:00–23:00 | Thu 17:00–23:30 | ..."."""
    groups = []  # [first_day, last_day, hours] for runs of days with the same hours
    for key, day in _WEEK:
        hours = opening_hours[key]
        if groups and groups[-1][2] == hours:
            groups[-1][1] = day
        else:
            groups.append([day, day, hours])
    return " | ".join(
        f"{first} {hours}" if first == last else f"{first}–{last} {hours}" for first, last, hours in groups
    )
