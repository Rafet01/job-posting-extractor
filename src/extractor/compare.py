"""Compare evaluated runs side by side: python -m extractor.compare

Reads the CSVs written by extractor.evaluate and writes outputs/comparison.md.
On the dev split, name the runs to compare; each is paired with the first one:
    python -m extractor.compare --split dev --run llama3.1 v1 --run llama3.1 v3
"""

import argparse
from math import comb
from pathlib import Path

import pandas as pd

from extractor.evaluate import output_path
from extractor.schema import JobPosting
from extractor.splits import SPLITS, TEST, Split

# The published comparison of the test split.
RUNS = [("llama3.1", "v1"), ("llama3.1", "v2"), ("qwen2.5:7b", "v1"), ("qwen2.5:7b", "v2")]
PAIRS = [("llama3.1 v1", "llama3.1 v2"), ("qwen2.5:7b v1", "qwen2.5:7b v2"), ("llama3.1 v2", "qwen2.5:7b v2")]
LANGUAGES = ("overall", "en", "de", "fr")
ALPHA = 0.05


def sign_test(wins: int, losses: int) -> float:
    """Two-sided exact sign test: the chance of a split at least this uneven
    if both runs were equally good. Ties are left out before calling this.
    """
    trials = wins + losses
    if trials == 0:
        return 1.0
    tail = sum(comb(trials, k) for k in range(min(wins, losses) + 1)) / 2 ** trials
    return min(1.0, 2 * tail)


def paired_change(before: pd.DataFrame, after: pd.DataFrame, field: str) -> tuple[int, int, float]:
    """Count postings whose score for a field went up or down, with the sign-test p-value."""
    scores = pd.merge(before[before.field == field][["id", "score"]],
                      after[after.field == field][["id", "score"]], on="id", suffixes=("_a", "_b"))
    change = scores.score_b - scores.score_a
    wins, losses = int((change > 1e-9).sum()), int((change < -1e-9).sum())
    return wins, losses, sign_test(wins, losses)


def describe_change(wins: int, losses: int, p_value: float) -> str:
    """Format a paired comparison so that small differences read as small."""
    verdict = "**significant**" if p_value < ALPHA else "n.s."
    return f"+{wins} / −{losses} (p={p_value:.2f}, {verdict})"


def load_run(model: str, prompt: str, split: Split = TEST) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the detail and summary CSVs of one evaluated run."""
    frames = []
    for kind in ("details", "summary"):
        path = output_path(kind, model, prompt, split)
        if not path.exists():
            raise SystemExit(f"{path} is missing. Run: python -m extractor.evaluate "
                             f"--model {model} --prompt {prompt} --split {split.name}")
        frames.append(pd.read_csv(path, dtype={"id": str}))
    return frames[0], frames[1]


def fmt(score: float) -> str:
    """Two decimals, or a dash for a group without postings."""
    return "-" if pd.isna(score) else f"{score:.2f}"


def build_report(runs: dict[str, tuple[pd.DataFrame, pd.DataFrame]], pairs: list[tuple[str, str]]) -> str:
    """Write Markdown: an overview, paired changes and one table per field."""
    versions = {int(summary.metric_version.iloc[0]) for _, summary in runs.values()}
    if len(versions) != 1:
        raise SystemExit(f"Runs were scored with different metric versions {versions}. Re-evaluate them.")
    first = next(iter(runs.values()))[1]
    counts = first[first.field == "company"].set_index("language").n
    lines = [f"Metric version {versions.pop()}. Postings per group: "
             + ", ".join(f"{lang} n={counts[lang]}" for lang in LANGUAGES) + ".", ""]

    lines += ["## Failed extractions", "", "| run | failed or invalid |", "|---|---|"]
    for name, (_, summary) in runs.items():
        overall = summary[(summary.field == "company") & (summary.language == "overall")]
        lines.append(f"| {name} | {int(overall.missing_predictions.iloc[0])} |")

    lines += ["", f"## Overall scores (n={counts['overall']})", "",
              "| field | metric | " + " | ".join(runs) + " |",
              "|---|---|" + "---|" * len(runs)]
    for field in JobPosting.model_fields:
        cells = []
        for _, summary in runs.values():
            row = summary[(summary.field == field) & (summary.language == "overall")].iloc[0]
            cells.append(fmt(row.score))
            metric = row.metric
        lines.append(f"| {field} | {metric} | " + " | ".join(cells) + " |")

    tests = len(pairs) * len(JobPosting.model_fields)
    lines += ["", "## Paired changes per posting", "",
              "Postings that scored higher / lower in the second run, ties left out. "
              f"p is a two-sided exact sign test; only p < {ALPHA} is called significant. "
              f"With {tests} tests, about {tests * ALPHA:.0f} could reach that by chance alone.", "",
              "| field | " + " | ".join(f"{a} → {b}" for a, b in pairs) + " |",
              "|---|" + "---|" * len(pairs)]
    for field in JobPosting.model_fields:
        cells = [describe_change(*paired_change(runs[a][0], runs[b][0], field)) for a, b in pairs]
        lines.append(f"| {field} | " + " | ".join(cells) + " |")

    lines += ["", "## Per field and language", ""]
    header = " | ".join(f"{lang} (n={counts[lang]})" for lang in LANGUAGES)
    for field in JobPosting.model_fields:
        metric = first[first.field == field].metric.iloc[0]
        lines += [f"### {field} ({metric})", "", f"| run | {header} |", "|---|" + "---|" * len(LANGUAGES)]
        for name, (_, summary) in runs.items():
            scores = summary[summary.field == field].set_index("language").score
            lines.append(f"| {name} | " + " | ".join(fmt(scores[lang]) for lang in LANGUAGES) + " |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Compare the published test runs, or the runs named with --run against the first of them."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", choices=SPLITS, default="test")
    parser.add_argument("--run", nargs=2, action="append", metavar=("MODEL", "PROMPT"),
                        help="A run to include. Repeat for each run. Default: the four published test runs")
    parser.add_argument("--output", type=Path, help="Default: comparison.md in the split's output folder")
    args = parser.parse_args()
    split = SPLITS[args.split]
    if args.run is None and split is not TEST:
        parser.error("Name the runs to compare with --run MODEL PROMPT, at least twice")
    selected = [tuple(run) for run in args.run] if args.run else RUNS
    runs = {f"{model} {prompt}": load_run(model, prompt, split) for model, prompt in selected}
    names = list(runs)
    pairs = [(names[0], name) for name in names[1:]] if args.run else PAIRS
    output = args.output or split.output_dir / "comparison.md"
    title = "# Run comparison" if split is TEST else f"# Run comparison ({split.name} split)"
    report = f"{title}\n\nGenerated by `python -m extractor.compare`.\n\n" + build_report(runs, pairs)
    output.write_text(report + "\n", encoding="utf-8")
    print(report)
    print(output)


if __name__ == "__main__":
    main()
