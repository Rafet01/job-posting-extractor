"""Evaluate a cached run: python -m extractor.evaluate --model llama3.1 --prompt v1."""

import argparse
import json
from pathlib import Path

import pandas as pd

from extractor.labels import load_labels
from extractor.metrics import classification_report, exact_match, location_prf, skill_prf, text_similarity
from extractor.normalize import normalize_company, normalize_start
from extractor.run import cache_path, load_cached
from extractor.schema import JobPosting

# Bump when a scoring rule changes, then re-evaluate every run. See docs/experiments.md.
# 1: first version. 2: gender markers in titles and guideline start wordings normalised.
METRIC_VERSION = 2
# Kept at 0.85 after inspecting v1 titles: the matches just above it differ by a short
# suffix, and lowering it would split one error type (dropped title suffixes) arbitrarily.
TITLE_THRESHOLD = 0.85
CLASS_FIELDS = {"degree_level", "german_level", "english_required", "is_internship"}
METRICS = {
    "company": "normalized exact",
    "role_title": f"title >= {TITLE_THRESHOLD}",
    "locations": "mean posting F1",
    "required_skills": "mean posting F1",
    "start": "normalized exact (proxy)",
    **dict.fromkeys(CLASS_FIELDS, "macro F1"),
}


def output_path(kind: str, model: str, prompt: str) -> Path:
    """Where the details or summary CSV of one run is written, e.g. outputs/summary_qwen2.5_7b_v1.csv."""
    run_dir = cache_path(model, prompt, "001").parent
    return Path("outputs") / f"{kind}_{run_dir.parent.name}_{run_dir.name}.csv"


def detail_rows(labels: dict[str, JobPosting], predictions: dict[str, JobPosting | None],
                languages: dict[str, str]) -> pd.DataFrame:
    """Build one row per labelled posting and field, including missing predictions."""
    rows = []
    for posting_id, label in labels.items():
        prediction = predictions.get(posting_id)
        for field, gold in label.model_dump().items():
            pred = getattr(prediction, field) if prediction is not None else None
            similarity = None
            if prediction is None:
                score = 0.0
            elif field == "company":
                score = exact_match(normalize_company(gold), normalize_company(pred))
            elif field == "role_title":
                similarity = text_similarity(gold, pred)
                score = similarity >= TITLE_THRESHOLD
            elif field == "locations":
                score = location_prf(gold, pred)[2]
            elif field == "required_skills":
                score = skill_prf(gold, pred)[2]
            elif field == "start":
                score = exact_match(normalize_start(gold), normalize_start(pred))
            else:
                score = exact_match(gold, pred)
            rows.append({
                "id": posting_id, "language": languages[posting_id], "field": field,
                "gold": gold, "pred": pred, "score": float(score),
                "missing_prediction": prediction is None, "title_similarity": similarity,
            })
    return pd.DataFrame(rows)


def summarize(details: pd.DataFrame) -> pd.DataFrame:
    """Recompute each metric within each language, and once over all postings."""
    rows = []
    for language in ("overall", "en", "de", "fr"):
        subset = details if language == "overall" else details[details.language == language]
        for field in JobPosting.model_fields:
            group = subset[subset.field == field]
            score = group.score.mean()
            if field in CLASS_FIELDS and not group.empty:
                gold = [str(value) for value in group.gold]
                pred = [None if missing else str(value)
                        for value, missing in zip(group.pred, group.missing_prediction)]
                score = classification_report(gold, pred)["macro_f1"]
            rows.append({
                "field": field, "metric": METRICS.get(field, "exact"),
                "language": language, "n": len(group), "score": score,
                "missing_predictions": int(group.missing_prediction.sum()),
            })
    return pd.DataFrame(rows)


def show_report(summary: pd.DataFrame, details: pd.DataFrame) -> None:
    """Display field scores, denominators and real titles around the decision boundary."""
    groups = ["overall", "en", "de", "fr"]
    table = summary.pivot(index=["field", "metric"], columns="language", values="score")[groups]
    counts = summary.drop_duplicates("language").set_index("language")
    table.columns = [f"{lang} (n={counts.at[lang, 'n']})" for lang in groups]
    print(table.to_string(float_format=lambda score: f"{score:.3f}", na_rep="-"))
    print("Missing/invalid predictions:", counts.missing_predictions.to_dict())
    starts = details[details.field == "start"]
    stated = starts[starts.gold.notna()]
    print("Start is a textual proxy: equivalent date formats may differ; two absent dates match.")
    print(f"Start matched when stated: {int(stated.score.sum())}/{len(stated)}")
    titles = details.dropna(subset=["title_similarity"]).sort_values("title_similarity")
    below = titles[titles.title_similarity < TITLE_THRESHOLD].tail(2).iloc[::-1]
    above = titles[titles.title_similarity >= TITLE_THRESHOLD].head(2)
    for side, pairs in (("below", below), ("at or above", above)):
        print(f"Closest titles {side} {TITLE_THRESHOLD}:")
        if pairs.empty:
            print("  (none)")
        for row in pairs.itertuples():
            print(f"  {row.id} {row.title_similarity:.3f}  {row.gold} -> {row.pred}")


def main() -> None:
    """Read labels and cache, then write comparable detail and summary CSVs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", default="v1")
    args = parser.parse_args()
    path = Path("data/labels.csv")
    labels = load_labels(path)
    metadata = pd.read_csv(path, usecols=["id", "language"], dtype=str, keep_default_na=False)
    languages = dict(zip(metadata.id.str.strip(), metadata.language.str.strip()))
    if not labels or set(languages.values()) - {"en", "de", "fr"}:
        parser.error("Expected labelled postings with language en, de or fr")
    predictions = {key: load_cached(cache_path(args.model, args.prompt, key)) for key in labels}
    if all(prediction is None for prediction in predictions.values()):
        # Most likely a fresh clone: the cache is not in git. Scoring it would publish all zeros.
        run_dir = cache_path(args.model, args.prompt, "001").parent
        raise SystemExit(f"No valid cached predictions in {run_dir}. Nothing was written. "
                         f"Extract first: python -m extractor.run --model {args.model} --prompt {args.prompt}")
    details = detail_rows(labels, predictions, languages)
    summary = summarize(details)
    print(f"Model: {args.model}   Prompt: {args.prompt}   Metric version: {METRIC_VERSION}")
    show_report(summary, details)

    # JSON inside CSV preserves the difference between null, [], false and strings.
    export = details.copy()
    for column in ("gold", "pred"):
        export[column] = export[column].map(lambda value: json.dumps(value, ensure_ascii=False))
    for name, frame in (("details", export), ("summary", summary)):
        output = output_path(name, args.model, args.prompt)
        output.parent.mkdir(exist_ok=True)
        frame.assign(model=args.model, prompt=args.prompt,
                     metric_version=METRIC_VERSION).to_csv(output, index=False)
        print(output)


if __name__ == "__main__":
    main()
