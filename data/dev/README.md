# Development set

Postings in this folder are for **prompt work**: look at errors, change a prompt, run again, as often as needed. The 26 postings in `data/postings/` are the **test set**. A new prompt version is scored on the test set once, when it is finished, and never tuned on it.

- Posting texts go in `postings/` as `d001.txt`, `d002.txt`, … The `d` keeps dev ids apart from test ids in every file and results table.
- Labels go in `labels.csv`, with the same columns and the same rules as the test set: [docs/annotation_guidelines.md](../../docs/annotation_guidelines.md).
- Collect the postings the same way as the test set (see [data/README.md](../README.md)), and never copy a posting that is already in the test set. `python scripts/check_labels.py` flags postings that look the same in both sets.

```powershell
python -m extractor.run --model llama3.1 --prompt v1 --split dev
python -m extractor.evaluate --model llama3.1 --prompt v1 --split dev   # writes outputs/dev/
```
