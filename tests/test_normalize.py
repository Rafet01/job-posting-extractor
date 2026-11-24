"""Examples of equivalent spellings in posting fields."""

from extractor.normalize import normalize_company, normalize_place, normalize_skill, normalize_text


def test_text() -> None:
    """Accents, case and repeated whitespace should not affect comparisons."""
    assert normalize_text(None) == ""
    assert normalize_text("  GENÈVE\t und  Zürich ") == "geneve und zurich"


def test_company() -> None:
    """Only trailing legal suffixes are removed."""
    assert normalize_company("Deloitte Consulting AG") == "deloitte consulting"
    assert normalize_company("AG Partners, GmbH Ltd.") == "ag partners"
    assert normalize_company("Atlas Sage") == "atlas sage"


def test_place() -> None:
    """Local spellings, exonyms and punctuation map to the same place."""
    assert normalize_place("Zürich") == normalize_place("Zurich") == normalize_place("Zuerich")
    assert normalize_place("Genève") == normalize_place("Geneva")
    assert normalize_place("St.Gallen") == normalize_place("St. Gallen")
    assert normalize_place("Zürich/Kloten") != normalize_place("Zurich")


def test_skill() -> None:
    """Known aliases collapse while meaningful punctuation survives."""
    assert normalize_skill(" MS Power BI ") == "power bi"
    assert normalize_skill("C-Sharp") == "c#"
    assert normalize_skill("C++") == "c++"
