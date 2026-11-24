# Error analysis

The analysis uses the **best run: Llama 3.1 8B with prompt v1** (mean field score 0.81, 254 of 312 field values correct, metric version 2). Of its 58 wrong field values, 37 fall into categories 1–6 and 9 involve a label I consider debatable (category 8, which overlaps with category 3 on one value). The remaining 13 are scattered: reordered titles (010, 016), German `plus` missed (001, 003), a missing `workload_max` (012, 016) and a few single cases. Category 7 comes from the prompt-v2 runs, because it explains why v2 did not help. Category 8 is about the labels, not the model.

Counts are per field value in the Llama v1 run, out of 26 postings, unless stated otherwise. Source files: `outputs/details_llama3.1_v1.csv`, plus the v2 and Qwen detail files where named.

## Summary

| # | Category | Count (Llama v1) | Fields |
|---|---|---|---|
| 1 | Preference or alternative read as a requirement | 10 | required_skills, degree_level, language fields |
| 2 | General field reported as a skill | 9 postings (8 not already in category 1) | required_skills |
| 3 | Degree label read as a degree level, or a bachelor_ok default | 6 + 3 of 12 degree errors | degree_level |
| 4 | Date of another event taken as the start | 4 of 5 start errors | start |
| 5 | Missing value: a duration given as a range | 5 of 5 duration errors | duration_months |
| 6 | Invented value | 1 (Qwen v1: 8) | english_required, duration_months, start |
| 7 | Prompt example copied into the answer (v2 only) | Llama v2: about 25 values | locations, workload, start, duration, skills |
| 8 | Label debatable | 9 | degree, english, skills, german, title |

## 1. Preference or alternative read as a requirement

**How often:** 10 errors. Skills on 001, 009, 010, 018, 024, 025; degree on 026; languages on 006, 016, 025.

| posting | evidence in the posting | label | prediction |
|---|---|---|---|
| 001 | "Solid experience with Python. Experience with R is a plus." | `python; aws\|azure\|gcp` | `python, r` |
| 024 | "Kenntnisse in Excel …; erste Erfahrungen mit Power BI sind **von Vorteil**" | `excel` | `excel, power bi` |
| 026 | "Begonnenes oder abgeschlossenes Hochschulstudium **von Vorteil**" | degree `unknown` | `bachelor_ok` |

**Likely cause:** the model collects every tool or degree mentioned near the profile section and ignores the qualifier that follows it. The v1 prompt never says that preferences are excluded: the field description is just "Mandatory technical skills". Prompt v2 states the rule and the preference words explicitly, but the skills score did not improve (+4/−7 postings for Llama), and v2 created new errors of this type. On 015 both models now list Google Cloud, Power Automate and C# from "… sind von Vorteil", which v1 got right. Writing the rule into the prompt is not enough for an 8B model.

## 2. General field reported as a skill

**How often:** 9 postings (003, 007, 008, 016, 017, 018, 022, 023, 026). These hurt precision only.

| posting | label | prediction |
|---|---|---|
| 023 | `[]` | `reinforcement learning, large language models, distributed systems, multi-gpu training environments` |
| 008 | `[]` | `ai, automation, process optimisation` |

**Likely cause:** "skill" is ambiguous in everyday language. The guideline's narrower meaning (named tools only, no fields such as ML or LLMs) is not in the v1 prompt. v2 removed some of these terms (Llama 008: `ai, apis`), but on 023 Qwen v2 replaced them with a copied list of tools (category 7).

## 3. Degree label read as a degree level

**How often:** 6 of Llama's 12 degree errors (014, 016, 022, 024 → `bachelor_ok`; 017, 020 → `master_only`).

| posting | evidence in the posting | label | prediction |
|---|---|---|---|
| 024 | "Bachelor- oder Masterabschluss in Betriebswirtschaft …" | `graduate_only` | `bachelor_ok` |
| 017 | "Master degree in Computer Science, Mathematics or similar field" | `graduate_only` | `master_only` |

**Likely cause:** the label names describe a *degree level*, while the guidelines use them for *who may apply*. Read naively, "a Bachelor's degree is enough" means `bachelor_ok`, and "a Master degree is required" means `master_only`. The v1 description ("'master_only' if only master students") does not settle it, and it is older than the guidelines. v2 explains the distinction explicitly, yet Llama v2 still makes the same choice on 014, 016, 017 and 024. Qwen v2 over-corrects instead: it labels five bachelor_ok postings `graduate_only`. This points to a schema design problem more than a prompt problem. Splitting the field into `required_level` (bachelor/master/phd) and `must_have_completed` (yes/no) would remove the ambiguity.

Llama also defaults to `bachelor_ok` when nothing is stated (001, 007, 023): 3 more errors.

## 4. Date of another event taken as the start

**How often:** 4 of the 5 start errors (008, 020, 022, 024). Qwen v1 has the same errors on 008, 020, 022 and 024.

| posting | evidence in the posting | label | prediction |
|---|---|---|---|
| 008 | publication date "18 November 2026" on line 5; no start date anywhere | null | `18 November 2026` |
| 020 | publication date "03 November 2026"; body: "per sofort oder nach Vereinbarung" | `asap` | `03 November 2026` |

**Likely cause:** the copied postings start with a metadata block (date, workload, contract type). The publication date sits where a start date would sit and is the only full date in the header. v1 says nothing about other dates. v2 names the publication date explicitly, and Qwen v2 then fixed 008 and 022 (start +7/−0, p = 0.02). Llama v2 instead started writing `asap` where no start is given (category 7).

## 5. Missing value: a duration given as a range

**How often:** all 5 of Llama's duration errors (005, 006, 013, 018, 019).

| posting | evidence in the posting | label | prediction |
|---|---|---|---|
| 006 | "Contract duration (in months): 1 to 6" | 1 | null |
| 018 | title "Stagiaire en analyse de données IT - Stage de 6 à 12 mois - 100%" | 6 | null |

**Likely cause:** the earlier impression was "Llama misses French durations", but the real pattern is **ranges**. Llama v1 gets all 8 durations stated as a single number right (003, 004, 008, 009, 016, 021, 025, 026). It misses 5 of the 6 durations stated as a range or period (005 "3–6 months", 006 "1 to 6", 013 "février à juillet", 018/019 "6 à 12 mois"). The only range it gets right is 014. All three French postings happen to state ranges. The schema asks for one integer, and v1 does not say which end of a range to take, so the model returns null. The guideline's lower-bound convention is a dataset choice that the model cannot guess.

## 6. Invented value

**How often:** rare in the best run, with 1 error (024: `english_required = true`, but the posting does not mention English at all). Much more frequent for Qwen v1: 8 errors, a duration of `6` on 002, 007, 010 and 012 with no duration stated, and `asap` on 002, 004, 007 and 010 with no start stated.

| run, posting | evidence in the posting | label | prediction |
|---|---|---|---|
| Qwen v1, 010 | no duration or start stated | duration null, start null | `6`, `asap` |

**Likely cause:** "6 months" and "asap" are the most typical values for an internship, so the model falls back on a prior when the text is silent. v2's "never fill in a typical or likely value" fixed Qwen's `asap` but not its durations (still `6` on 002, 007, 010 and 011).

## 7. Prompt example copied into the answer (prompt v2 only)

**How often:** Llama v2 alone has about 25 such values (9 location strings, 5 workloads, 8 start values, 3 durations). It is the main reason v2 scores lower than v1.

| run, posting | example in the v2 prompt | label | prediction |
|---|---|---|---|
| Llama v2, 003 | "Use [] for fully remote work …" | `["Lausanne"]` | `["Lausanne", "[ ]"]` (9 postings) |
| Llama v2, 004 | "\"60-80%\" gives 60 and 80" | workload null/null | `60/60` (5 postings with workload_min 60) |
| Qwen v2, 023 | the canonical-spelling list "power bi, excel, …, aws, gcp, azure, postgresql, git, c#, spark, react" | `[]` | `python, torch, tensorflow, aws, gcp, azure, postgresql, git, c#, spark, react` |

Other copies: `asap` on 8 Llama postings with no start, durations of 24 ("2 years gives 24") on 001 and 015 and 4 ("4-8 months gives 4") on 007, and `numpy` from "Python (NumPy)" on Qwen 010 and 019.

**Likely cause:** small models treat concrete values in the instructions as candidate answers, especially when the posting offers nothing for that field. That is exactly the case the examples were meant to cover. The leakage test checks that the prompt contains no test-set text, but this is leakage in the other direction: from the prompt into the output. **Fix for a next version:** describe rules in words or with obvious placeholders, keep reference lists (canonical spellings) out of the prompt, and never write a literal `[]` as an example.

## 8. Label debatable

9 of Llama's 58 errors involve a label that I would defend less firmly than the model's answer: degree and English on 014, skills on 020 and 021, German on 024, and the titles of 014, 018, 019 and 020. The labels were not changed. They are listed in [experiments.md](experiments.md#labels-i-think-are-debatable-or-wrong-not-changed). Two examples:

| posting | field | evidence in the posting | label | prediction (all runs) |
|---|---|---|---|---|
| 014 | degree_level | "Employment level: University internship"; "CHF 2,500 … for Bachelor … students or graduates"; requirements: "Bachelor's or Master's degree in …" | `graduate_only` | `bachelor_ok` (3 of 4 runs) |
| 020 | required_skills | "programmierst sicher in mindestens einer Programmiersprache für Datenanalyse wie R, Python oder Stata" | `[]` | `r, python, stata` (4 of 4 runs) |

**Why debatable:** on 014, the salary line explicitly addresses current students, which contradicts the reading that a completed degree is compulsory. On 020, the label treats "such as R, Python or Stata" as examples of a generic requirement, so the list is empty. Yet 001 ("one or more of AWS, Azure or GCP") is labelled as a set of alternatives. The line between an open and a closed list is thin. If 020 were labelled `r|python|stata`, all four runs would score F1 = 1 on it instead of 0. With 26 postings, a single labelling decision like this moves the skills score by about 0.04.

I think one label is actually wrong under the guidelines themselves. On 024, "Gute aktive Kenntnisse zweier Amtssprachen" makes German one of several acceptable languages, which the guidelines label `plus`. The label is `none`.

## Takeaways for the README

- The hardest fields (skills, degree) fail on **interpretation**, not on reading. The models find the right sentences but apply a different notion of "requirement" or "degree level" than the guidelines do.
- Some failures are **schema design** problems (category 3: one label mixing level and completion; category 5: one integer for a range). Changing the schema would fix them more reliably than adding prompt rules.
- Prompt instructions are not neutral. In 7–8B models, examples in the prompt turn into outputs (category 7).
- With 26 postings and one annotator, a single debatable label is worth as much as most of the prompt differences measured.
