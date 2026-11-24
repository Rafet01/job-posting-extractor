"""Canonical spellings for evaluation of job postings."""

import re
import string
import unicodedata

PLACE_ALIASES = {
    "geneve": "geneva", "genf": "geneva", "zuerich": "zurich",
    "bale": "basel", "berne": "bern", "luzern": "lucerne",
    "saintgall": "stgallen", "sanktgallen": "stgallen",
    "soleure": "solothurn", "zuerichkloten": "zurichkloten",
}

SKILL_ALIASES = {
    "powerbi": "power bi", "power-bi": "power bi", "ms power bi": "power bi",
    "ms excel": "excel", "microsoft excel": "excel",
    "js": "javascript", "ts": "typescript",
    "amazon web services": "aws", "google cloud": "gcp",
    "google cloud platform": "gcp", "microsoft azure": "azure",
    "postgres": "postgresql", "github": "git", "gitlab": "git",
    "c-sharp": "c#", "pyspark": "spark", "apache spark": "spark",
    "react.js": "react", "reactjs": "react",
}


def normalize_text(value: str | None) -> str:
    """Remove accents, lowercase text and collapse whitespace."""
    decomposed = unicodedata.normalize("NFD", (value or "").lower())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(plain.split())


def normalize_company(value: str | None) -> str:
    """Remove punctuation at the edges and trailing legal suffixes."""
    name = normalize_text(value).strip(string.punctuation + " ")
    while match := re.search(r"\b(?:ag|gmbh|sa|ltd|inc|llc|se)$", name):
        name = name[:match.start()].rstrip(string.punctuation + " ")
    return name


def normalize_place(value: str | None) -> str:
    """Map alphanumeric place names to a shared spelling."""
    place = "".join(char for char in normalize_text(value) if char.isalnum())
    return PLACE_ALIASES.get(place, place)


def normalize_skill(value: str) -> str:
    """Map a skill name to its canonical spelling, preserving symbols like +."""
    skill = value.strip().lower()
    return SKILL_ALIASES.get(skill, skill)
