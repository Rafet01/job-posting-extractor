"""Prompt variants for the extraction task."""

import json

from extractor.schema import JobPosting

# v1 is frozen: its cached results were produced with exactly this text and the field
# descriptions in schema.py. tests/test_prompts.py checks a hash of the full prompt.
SYSTEM_PROMPT_V1 = """You extract structured information from job postings.
Answer with one JSON object that follows this JSON Schema exactly:

{schema}

Rules:
- Use null when information is not stated in the posting.
- Do not add fields that are not in the schema.
- Answer with JSON only, no explanation."""

# v2 restates docs/annotation_guidelines.md as instructions. The schema it embeds has
# no descriptions, so these rules are the only explanation of each field. All examples
# are invented; none is copied from a posting in data/postings.
SYSTEM_PROMPT_V2 = """You extract structured information from job postings.
Answer with one JSON object that follows this JSON Schema exactly:

{schema}

General rules:
- Use only what the posting states. Never fill in a typical or likely value.
- The first three lines are the job title, the employer and the location from the job page. Read them together with the body.
- A requirement is something the candidate must already bring, usually listed under a profile heading such as "What you bring", "Das bringen Sie mit" or "Votre profil".
- A task is not a requirement: "you will build Looker reports" requires nothing.
- A preference is not a requirement. Preference signals include: a plus, preferred, ideally, von Vorteil, wünschenswert, idealerweise, souhaité, idéalement, un atout, and similar wording.
- A qualifier applies only to the phrase it modifies: in "Java required, Kotlin preferred" only Java is required.

Fields:
- company: the employer from the second line, without a legal suffix such as AG, GmbH, SA or Ltd.
- role_title: the first line, copied exactly in its original language. Do not translate, shorten or reorder it. Remove only a separate gender marker such as (m/w/d), (w/m/d) or (all genders).
- locations: every distinct place where this job can be based: the location line plus further workplaces the body offers. Keep a country or region only when it is the most specific workplace. Leave out a country that only qualifies a city, work arrangements such as hybrid or home office, markets served, travel destinations and company addresses given as background. Use [] for fully remote work with no geographic restriction.
- workload_min, workload_max: percent of full time as whole numbers. "60-80%" gives 60 and 80, "90%" gives 90 and 90, "at least 60%" gives only workload_min 60. Null when no percentage is given.
- duration_months: the stated length of the position in whole months, from the title line or the body. For a range use the lower bound ("4-8 months" gives 4), "2 years" gives 24, and weeks count as four per month ("16 weeks" gives 4). Null for a permanent position or when no length is stated.
- start: the shortest phrase that gives the start date or period, in the original language. "Starting in March 2028" gives "March 2028". Write "asap" for as soon as possible, immediately, ab sofort or dès que possible. Drop additions such as "or by agreement", "oder nach Vereinbarung" or "ou à convenir". Null when no start is given or the start is "to be discussed". Dates of other events, such as when the posting was published or the application deadline, are not start dates.
- german_level: "required" if the candidate must know German. "plus" if German is preferred or is one of several acceptable languages ("German or Italian"). "none" if the posting states no German qualification. The language the posting is written in is no evidence.
- english_required: true only if the candidate must know English. False if English is preferred, is one of several acceptable languages ("English or Italian"), or is not stated as a requirement. The language the posting is written in is no evidence.
- degree_level: decide from what the posting says about studies or degrees, not from the job title. The labels describe who may apply:
  - "graduate_only": a completed degree is compulsory, at any level. A required master's degree also counts here. Also for roles restricted to recent graduates.
  - "master_only": current master's or PhD students can apply (master's graduates may also be welcome), but bachelor students cannot.
  - "bachelor_ok": students still in a bachelor's programme can apply. This includes postings open to both bachelor and master students, enrolled students with no level given, and postings for students or recent graduates when bachelor students are among them.
  - "unknown": no study or degree requirement, a degree that is only preferred, or only a field such as "a background in economics".
- is_internship: true for an internship, Praktikum, Hochschulpraktikum or French stage, also when it is fixed-term. False for working-student roles, trainee and graduate programmes, thesis positions and other jobs. Internships the candidate did before do not count.
- required_skills: named technical tools the candidate must already know: programming languages, libraries, frameworks, databases, cloud platforms, and data or BI tools.
  - Leave out tools that appear only in tasks, preferred tools, and tools the candidate may still learn.
  - Leave out tools named only as examples of a general requirement: "a visualisation tool such as Looker or Qlik" gives nothing, and so does "Go, Rust or similar languages".
  - When any one of several named tools satisfies a requirement ("one of Java, Go or Rust"), list each of them.
  - A library named with its language counts separately: "Python (NumPy)" gives python and numpy.
  - Leave out soft skills, spoken languages, degrees, years of experience, and general fields such as machine learning, AI, LLMs, statistics or data analysis. Include Excel when it is required; leave out PowerPoint, Word and Outlook.
  - Lowercase, in order of first mention, without duplicates. Canonical spellings: power bi, excel, javascript, typescript, aws, gcp, azure, postgresql, git (also for GitHub or GitLab experience), c#, spark (also for PySpark), react.
  - Use [] when no named tool is mandatory.

Answer with JSON only, no explanation."""

# v3 is v1 (schema with field descriptions) plus short rules for the errors v1 made on
# the development set (data/dev). Every example is invented; none is copied from a posting.
SYSTEM_PROMPT_V3 = """You extract structured information from job postings.
Answer with one JSON object that follows this JSON Schema exactly:

{schema}

Rules:
- Use null when information is not stated in the posting.
- Do not add fields that are not in the schema.
- Use only what the posting states. The language a posting is written in is never evidence that a language is required.
- The first three lines are the job title, the employer and the location.

Field rules:
- role_title: copy the first line exactly, with every number, percentage and bracket in it. Remove only a gender marker such as (m/w/d), (f/m/x) or (all genders).
- company: the employer on the second line, without a legal suffix such as AG, SA, GmbH or Ltd. Never replace it with a department or team.
- duration_months: also look in the body. "for 4 to 8 months" gives 4, "8-12 Monate" gives 8, "a 24-month programme" gives 24.
- start: only the date or period, in the posting's language, without words around it. "ab 1. März 2028 oder nach Vereinbarung" gives "1. März 2028". Write "asap" for immediately, as soon as possible, ab sofort or dès que possible.
- german_level: "required" only if the posting says the candidate needs German. "plus" if German is preferred, or if one of several languages is enough ("German or French", "one national language"). Otherwise "none".
- english_required: true only if the posting says the candidate needs English, for example "fluent English". False if English is a plus or not mentioned.
- degree_level, decided from what the posting says about studies:
  - "graduate_only": a finished degree is compulsory ("completed Master's", "abgeschlossenes Studium", "titulaire d'un diplôme", "you hold a degree").
  - "master_only": current master's or PhD students can apply, bachelor students cannot.
  - "bachelor_ok": current students can apply and bachelor students are not excluded, also when recent graduates are welcome too.
  - "unknown": no study requirement, or only a field of study or a background.
- is_internship: true only for an internship, Praktikum or stage. False for graduate programmes, trainee programmes, working-student roles and other jobs.
- required_skills: named tools the candidate must already know, lowercase, with spaces instead of underscores ("power bi").
  - Leave out general fields and methods: machine learning, AI, NLP, deep learning, statistics, data mining, MLOps, forecasting methods.
  - Leave out tools that appear only in the tasks, tools that are a plus, and tools named only as examples ("such as", "like", "e.g.", "z. B.", "wie", "par exemple", "or similar", "oder ähnliche").
  - When any one of several named tools is enough ("Go, Rust or Kotlin"), list each of them.
  - Use [] when no named tool is required.

Answer with JSON only, no explanation."""

PROMPTS = {
    "v1": SYSTEM_PROMPT_V1,
    "v2": SYSTEM_PROMPT_V2,
    # The v1 request with one change: the answer is constrained to the JSON Schema while the
    # model generates it, instead of only being required to be some JSON object.
    "v1-schema": SYSTEM_PROMPT_V1,
    # v1-schema with every field required in the decoding schema. In v1-schema the fields
    # with a default (workload, duration, start, ...) are optional, so the grammar lets
    # the model close the object without them.
    "v1-strict": SYSTEM_PROMPT_V1,
    "v3": SYSTEM_PROMPT_V3,
}

# Versions whose schema in the prompt keeps the field descriptions (see schema_for).
DESCRIBED_SCHEMA = {"v1", "v1-schema", "v1-strict", "v3"}
# Versions that ask the API for schema-constrained decoding instead of plain JSON mode.
SCHEMA_DECODING = {"v1-schema", "v1-strict"}
# Schema-decoding versions that list every property as required. Optional values are
# still possible, because those fields also accept null.
ALL_FIELDS_REQUIRED = {"v1-strict"}


def without_descriptions(node: object) -> object:
    """Return a copy of a JSON Schema with every 'description' key removed."""
    if isinstance(node, dict):
        return {key: without_descriptions(value) for key, value in node.items() if key != "description"}
    if isinstance(node, list):
        return [without_descriptions(value) for value in node]
    return node


def schema_for(version: str) -> str:
    """The JSON Schema text embedded in the system prompt of a prompt version."""
    schema = JobPosting.model_json_schema()
    if version not in DESCRIBED_SCHEMA:
        # Later versions explain the fields in their rules instead of in the schema.
        schema = without_descriptions(schema)
    return json.dumps(schema, indent=2)


def build_messages(posting_text: str, version: str = "v1") -> list[dict[str, str]]:
    """Build the chat messages for one posting with the given prompt version."""
    if version not in PROMPTS:
        raise ValueError(f"Unknown prompt version {version!r}. Choose from: {', '.join(PROMPTS)}")
    system_prompt = PROMPTS[version].format(schema=schema_for(version))
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": posting_text},
    ]


def response_format_for(version: str) -> dict:
    """The response_format of the chat request: JSON mode, or decoding constrained by the schema.

    Ollama turns a JSON Schema into a grammar, so the model cannot produce a token that breaks
    the structure. Rules the schema cannot express, such as workload_min <= workload_max,
    are still checked by Pydantic afterwards.
    """
    if version not in SCHEMA_DECODING:
        return {"type": "json_object"}
    schema = JobPosting.model_json_schema()
    if version in ALL_FIELDS_REQUIRED:
        schema["required"] = list(schema["properties"])
    return {"type": "json_schema", "json_schema": {"name": "job_posting", "schema": schema}}
