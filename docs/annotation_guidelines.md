# Annotation guidelines

Use these rules to label each vacancy in `data/postings/` with one row in `data/labels.csv`. Two annotators reading the same posting should produce equivalent labels. When a new case changes a rule, add an example here and recheck earlier rows affected by that decision.

## Reading a posting

The first three lines contain the job title, employer and location copied from the job page. Read them together with the body. Use only information stated in the posting.

For requirements, identify what the **candidate must already bring**. Headings such as “What you bring”, “Das bringen Sie mit” and “Votre profil” help locate this evidence. An explicit requirement anywhere in the posting counts. “You must know Power BI” establishes a skill requirement. “You will build Power BI dashboards” describes a task and by itself establishes none.

Read qualifiers with the phrase they modify. In “Python required, R preferred”, only Python is mandatory. Preference signals include *a plus, preferred, ideally, von Vorteil, wünschenswert, idealerweise, souhaité, idéalement* and *un atout*.

## CSV format

Use UTF-8, comma-separated columns and one row per posting. Preserve the leading zeros in `id`. Quote any cell containing a comma or a double quote according to standard CSV rules. Use the following header.

```csv
id,language,company,role_title,locations,workload_min,workload_max,duration_months,start,german_level,english_required,degree_level,is_internship,required_skills,notes
```

- `id` is the three-digit posting filename without the extension, e.g. `001`.
- `language` is the main language of the posting body, one of `en`, `de` or `fr`. It is dataset metadata.
- `notes` is optional annotator metadata for ambiguity or review. Leave it empty when no note is needed. Quote a note containing a comma, e.g. `"German or French required, check"`.
- Write booleans as `true` or `false`. Use the field-specific defaults below for missing information. An empty list is an empty CSV cell.
- Use `;` between locations or separate skill requirements. Use `|` between skills that satisfy the same requirement. Keep spaces inside names such as `power bi` and omit spaces around separators.

## Fields

### company

Use the hiring employer's name from the header and remove a trailing legal suffix such as `AG`, `GmbH`, `SA` or `Ltd`. Keep meaningful words in the name. In posting 001, the header gives the brand as `Deloitte`. In 003, keep the full name `Losinger Marazzi`.

### role_title

Copy the header title in its original language. Remove a separate gender marker such as `(m/w/d)`, `(w/m/d)` or `(all genders)`. Preserve wording within the title, including forms such as `Praktikant/in`. “Praktikant/in Data (m/w/d)” becomes `Praktikant/in Data`.

### locations

**Record every distinct place where this particular job can be based.** Read the header first, then add any further workplaces explicitly offered in the body. Use the spelling and order of first mention. Record a place only once, including when the body repeats it in another spelling.

| Wording | CSV cell | Reason |
|---|---|---|
| Basel, Zurich, Geneva | `Basel;Zurich;Geneva` | All three cities are offered for the role. |
| Solothurn oder Zürich | `Solothurn;Zürich` | Either city is a valid base. |
| Zürich/Kloten | `Zürich/Kloten` | Posting 014 uses one combined label and gives no indication of separate workplaces. A slash alone is insufficient evidence to split it. |
| Poland | `Poland` | Keep a country or region when it is the most specific workplace given. |
| Based in Lausanne, Switzerland | `Lausanne` | The country qualifies the city. Both refer to one workplace. |
| Hybrid in Geneva | `Geneva` | “Hybrid” describes the work arrangement. |
| Remote within Switzerland | `Switzerland` | The posting explicitly limits where the candidate can work. |
| Fully remote, with no geographic restriction stated | *(empty)* | No geographic workplace is given. |

Exclude markets served, travel destinations, and office or headquarters addresses mentioned only as company background. Posting 004, for example, names the Swiss and Spanish financial markets and gives no workplace. Its location cell is empty.

For evaluation, compare locations as **sets** after spelling normalisation, so `Zurich` and `Zürich` match and list order has no effect. A prediction containing only Basel for posting 001 is missing two locations.

### workload_min and workload_max

Record the percentage of a full-time schedule as whole numbers without the percent sign. For an exact percentage, use it for both bounds. For a one-sided bound, fill only the stated side.

| Wording | workload_min | workload_max |
|---|---|---|
| 80–100% | 80 | 100 |
| 100% | 100 | 100 |
| Teilzeit 60% | 60 | 60 |
| At least 80% | 80 | *(empty)* |
| Part-time, no percentage given | *(empty)* | *(empty)* |

### duration_months

Record the stated length of the position in whole months. For a range, use the lower bound. “6-monatiges Praktikum” gives `6`, “6–12 months” gives `6`, and “1 year” gives `12`. For durations expressed in weeks, use the dataset convention of four weeks per month, so “12 weeks” gives `3`. Flag a conversion that does not yield a whole month for review. Leave the cell empty for a permanent position or an unspecified duration.

### start

Keep the shortest phrase that preserves the stated start date or period, in the original language. “Starting February 2027” gives `February 2027`. Normalise “as soon as possible”, “immediately”, “ab sofort” and “dès que possible” to `asap`. Leave the cell empty when no start is given. An application deadline belongs to a different event.

### german_level

| Label | When to use it |
|---|---|
| `required` | German itself is mandatory, e.g. “Fluent in German and English” or “sehr gute Deutschkenntnisse” in the candidate profile. |
| `plus` | German is explicitly preferred, e.g. “Deutsch von Vorteil” or “German and/or French highly preferred”. |
| `none` | The posting states no German-language qualification. The language of the posting is irrelevant. |

“German or French required” is an alternative language requirement. German alone is neither mandatory nor described as a preference. Flag such a case for review before assigning a label, because the three current values cannot express it exactly.

### english_required

Use `true` when the candidate must know English. Use `false` when English is preferred, is one of several acceptable language alternatives, or has no stated requirement. An English-language posting alone is insufficient evidence.

### degree_level

Read the eligibility wording. A job title such as *Hochschulpraktikum* can refer to internships with different admission requirements.

| Label | Evidence |
|---|---|
| `bachelor_ok` | Bachelor students can apply. This includes “Bachelor’s or Master’s student”, general enrolment with no advanced degree specified, and “student or recent graduate” when bachelor students are eligible. The dataset also accepts a general higher-education training requirement naming FH or university without a completed degree, as in 003. |
| `master_only` | The posting restricts eligibility to current master’s students, e.g. “enrolled in a Master’s programme”. |
| `graduate_only` | A completed degree is compulsory, e.g. “Bachelor- oder Masterabschluss”, “completed Master’s” or a role restricted to recent graduates. |
| `unknown` | No study or degree requirement is stated, or the posting gives only a field such as “engineering background”. |

Posting 009 asks for enrolment in a bachelor’s or master’s programme and receives `bachelor_ok`. Posting 024 asks for a completed bachelor’s or master’s degree and receives `graduate_only`.

### is_internship

Use `true` when the advertised role is an internship, including *Praktikum*, *Hochschulpraktikum* and French *stage*. Use `false` for working-student roles, trainee or graduate programmes, thesis positions and other jobs. A fixed-term internship still receives `true`. A mention of a candidate’s previous internship does not classify the advertised role.

### required_skills

Record mandatory technical skills in lowercase, using the canonical spellings below. Include named programming languages, libraries, frameworks, databases, cloud platforms, and data or BI tools. Keep the order of first mention as a requirement and remove duplicates.

| Requirement | CSV cell | Interpretation |
|---|---|---|
| Python and SQL | `python;sql` | Both are required. |
| Python and experience with at least one of AWS, Azure or GCP | `python;aws\|azure\|gcp` | Python is required, plus any one of the three cloud platforms. |
| Python (pandas) | `python;pandas` | The requirement names the language and its library. |
| Python required, SQL a plus | `python` | The preference applies only to SQL. |
| Experience with a BI tool, e.g. Power BI or Tableau | *(empty)* | The requirement is generic. The named products are examples. |

Leave out task-only mentions, preferred skills, soft skills, spoken languages, degrees and years of experience. Also leave out general fields such as machine learning, AI, LLMs, statistics and data analysis. Among general office applications include Excel when required and exclude PowerPoint, Word and Outlook.

| Variants in the posting | Canonical label |
|---|---|
| PowerBI, Power-BI, MS Power BI | `power bi` |
| MS Excel, Microsoft Excel | `excel` |
| JS, JavaScript | `javascript` |
| TS, TypeScript | `typescript` |
| Amazon Web Services | `aws` |
| Google Cloud, Google Cloud Platform | `gcp` |
| Microsoft Azure | `azure` |
| Postgres, PostgreSQL | `postgresql` |
| GitHub, GitLab when used to describe version-control experience | `git` |
| C-Sharp | `c#` |
| PySpark, Apache Spark | `spark` |
| React.js, ReactJS | `react` |

Add a row when a new spelling refers to an existing canonical skill.

## Worked examples

These complete rows follow the CSV header above. In the first row, the skills cell literally contains `python;aws|azure|gcp`.

```csv
001,en,Deloitte,AI & Analytics Consulting Manager,Basel;Zurich;Geneva,80,100,,,plus,true,unknown,false,python;aws|azure|gcp,
003,de,Losinger Marazzi,Data & AI Intern,Lausanne,,,6,,plus,false,bachelor_ok,true,sql;power bi;python;pandas,
```

**001 · Deloitte.** The header lists three cities, and the body repeats them. The role requires English and prefers German and/or French. An engineering or mathematics background and six years of experience establish no particular degree. Python and experience with one or more of the three named cloud providers are mandatory. R, the listed workbench tools and the visualisation tools are preferences.

**003 · Losinger Marazzi.** “6-monatigen Praktikums” gives the duration and role type. French is compulsory, German is a plus and English has no stated requirement. “Unverzichtbare Kenntnisse” introduces SQL, Power BI and Python, with pandas named under Python. JS and React appear under tasks. Git and Snowflake appear under “Von Vorteil”.
