"""Pure-Python metrics for comparing predictions with annotated postings."""

from difflib import SequenceMatcher

from extractor.normalize import normalize_place, normalize_skill, normalize_title


def exact_match(gold: str | int | bool | None, pred: str | int | bool | None) -> bool:
    """Compare scalar fields directly, including two missing values."""
    return gold == pred


def text_similarity(gold: str | None, pred: str | None) -> float:
    """Return the continuous title score before applying a threshold."""
    return SequenceMatcher(None, normalize_title(gold), normalize_title(pred)).ratio()


def text_match(gold: str | None, pred: str | None, threshold: float = 0.85) -> bool:
    """Compare normalized strings using character-sequence similarity."""
    # Titles can differ slightly (Intern vs Internship) while describing the same job.
    # The threshold trades missed matches for false matches. Justify it with examples.
    return text_similarity(gold, pred) >= threshold


def _f1(precision: float, recall: float) -> float:
    """Return the harmonic mean, or zero when both scores are zero."""
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def set_prf(gold: set[str], pred: set[str]) -> tuple[float, float, float]:
    """Return precision, recall and F1. Empty pred gives precision 1, empty gold
    gives recall 1, both empty give three ones, and two zeros give F1 zero.
    """
    hits = len(gold & pred)
    precision = hits / len(pred) if pred else 1.0
    recall = hits / len(gold) if gold else 1.0
    return precision, recall, _f1(precision, recall)


def skill_prf(gold_items: list[str], pred: list[str]) -> tuple[float, float, float]:
    """Score distinct predicted skills and gold requirements with alternatives."""
    predicted = {normalize_skill(skill) for skill in pred}
    groups = []
    allowed = set()
    for item in gold_items:
        members = {normalize_skill(skill) for skill in item.split("|")}
        groups.append(members)
        allowed.update(members)

    satisfied = sum(bool(group & predicted) for group in groups)
    precision = len(predicted & allowed) / len(predicted) if predicted else 1.0
    recall = satisfied / len(groups) if groups else 1.0
    return precision, recall, _f1(precision, recall)


def location_prf(gold: list[str], pred: list[str]) -> tuple[float, float, float]:
    """Score distinct normalized workplace names, ignoring their order."""
    return set_prf({normalize_place(p) for p in gold}, {normalize_place(p) for p in pred})


def classification_report(gold: list[str], pred: list[str | None]) -> dict:
    """Report accuracy, class scores and macro F1. A missing prediction is a miss
    for its gold class, not a new class. Undefined scores are zero.
    """
    if len(gold) != len(pred):
        raise ValueError("Gold and prediction lists must have the same length")

    per_class = {}
    correct = 0
    classes = set(gold) | {label for label in pred if label is not None}
    for label in sorted(classes):
        support = gold.count(label)
        predicted = pred.count(label)
        hits = sum(actual == guess == label for actual, guess in zip(gold, pred))
        correct += hits
        precision = hits / predicted if predicted else 0.0
        recall = hits / support if support else 0.0
        per_class[label] = {
            "precision": precision, "recall": recall,
            "f1": _f1(precision, recall), "support": support,
        }

    return {
        "accuracy": correct / len(gold) if gold else 0.0,
        "per_class": per_class,
        "macro_f1": sum(c["f1"] for c in per_class.values()) / len(per_class) if per_class else 0.0,
    }
