# Development set

Postings in this folder are for **prompt work**: look at errors, change a prompt, run again, as often as needed. The 26 postings in `data/postings/` are the **test set**. A new prompt version is scored on the test set once, when it is finished, and never tuned on it.

- Posting texts are in `postings/` as `d001.txt` … `d026.txt`. The `d` keeps dev ids apart from test ids in every file and results table.
- Labels are in `labels.csv`, with the same columns and the same rules as the test set: [docs/annotation_guidelines.md](../../docs/annotation_guidelines.md).
- `sources.csv` gives the public job page each posting is based on.
- `python scripts/check_labels.py` validates the labels and flags postings that look the same in both sets.

```powershell
python -m extractor.run --model llama3.1 --prompt v1 --split dev
python -m extractor.evaluate --model llama3.1 --prompt v1 --split dev   # writes outputs/dev/
```

## How the development set was made

The 26 postings are **paraphrases of real job ads**, not copies. They were collected on 2026-11-24:

1. Public Swiss job pages for internships and junior data or AI roles were found with a web search. Ads that are already in the test set were skipped.
2. For each page, the facts that the labels depend on were written down: title, employer, location, workload, duration, start date, language and degree requirements, and every requirement with its exact qualifier ("a plus", "von Vorteil", "un atout", "e.g.", "or similar").
3. Each ad was rewritten in its original language, in new words, with the same structure (intro, tasks, profile, offer) and the same facts. Contact names, e-mail addresses and phone numbers were left out.
4. Each posting was labelled following the annotation guidelines. The `notes` column marks the ambiguous cases.

Why paraphrases: the text of a job ad belongs to the employer. Rewriting keeps what matters for extraction (the facts and how they are qualified) without republishing the employer's text or anyone's contact details.

**Limitations.** The rewritten ads are cleaner than real ones: no page navigation, no duplicated blocks, no platform metadata. Results on the dev set are therefore likely to be a bit better than on real postings. The dev set guides prompt work; the test set of real ads remains the measure. The labels have not been checked by a second annotator.

| | count |
|---|---|
| English / German / French | 13 / 8 / 5 |
| Internships | 20 |
| Other roles (graduate programmes, working student, permanent and fixed-term jobs) | 6 |
