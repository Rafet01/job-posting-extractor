"""Normalisation: spellings that mean the same thing compare equal, and nothing more."""

from extractor.normalize import (
    normalize_company, normalize_place, normalize_skill, normalize_start, normalize_text,
    normalize_title,
)


def test_text_ignores_accents_case_and_whitespace() -> None:
    """Accents, case and repeated whitespace should not affect comparisons."""
    assert normalize_text(None) == ""
    assert normalize_text("  GENÈVE\t und  Zürich ") == "geneve und zurich"


def test_title_drops_gender_markers_only() -> None:
    """Separate gender markers disappear, gendered word forms stay."""
    assert normalize_title("Data Scientist (w/m/d)") == "data scientist"
    assert normalize_title("Stagiaire (H/F)") == normalize_title("Stagiaire (all genders)")
    assert normalize_title("Intern (6-12 months, 50-100%, all genders)") == "intern (6-12 months, 50-100%)"
    assert normalize_title("Praktikant/in Data") == "praktikant/in data"
    assert normalize_title("Datenanalyst:in (80%)") == "datenanalyst:in (80%)"


def test_start_wordings_from_the_guidelines_compare_equal() -> None:
    """Wordings that the guidelines map to one value compare equal."""
    assert normalize_start("As soon as possible") == normalize_start("ab sofort") == "asap"
    assert normalize_start("dès que possible") == "asap"
    assert normalize_start("1. Januar 2027 oder nach Vereinbarung") == "1. januar 2027"
    assert normalize_start("1 March 2027, or by agreement") == "1 march 2027"
    assert normalize_start("février 2027 ou à convenir") == "fevrier 2027"
    assert normalize_start("to be discussed") == normalize_start(None) == ""
    # An end date is not an addition the guidelines drop, so this stays a mismatch.
    assert normalize_start("ab sofort bis 31.12.2026") != "asap"


def test_company_drops_only_trailing_legal_suffixes() -> None:
    """Only trailing legal suffixes are removed."""
    assert normalize_company("Deloitte Consulting AG") == "deloitte consulting"
    assert normalize_company("AG Partners, GmbH Ltd.") == "ag partners"
    assert normalize_company("Atlas Sage") == "atlas sage"


def test_place_names_map_to_one_spelling() -> None:
    """Local spellings, exonyms and punctuation map to the same place."""
    assert normalize_place("Zürich") == normalize_place("Zurich") == normalize_place("Zuerich")
    assert normalize_place("Genève") == normalize_place("Geneva")
    assert normalize_place("St.Gallen") == normalize_place("St. Gallen")
    assert normalize_place("Zürich/Kloten") != normalize_place("Zurich")


def test_skill_aliases_collapse_and_symbols_survive() -> None:
    """Known aliases collapse while meaningful punctuation survives."""
    assert normalize_skill(" MS Power BI ") == "power bi"
    assert normalize_skill("C-Sharp") == "c#"
    assert normalize_skill("C++") == "c++"
