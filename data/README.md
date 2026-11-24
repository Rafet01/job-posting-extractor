# Data

## postings/

26 real job advertisements for internships and junior data or AI roles, mostly in Switzerland. They were copied by hand from public job listings (company career pages and job boards) in October and November 2026, during my own internship search. Each file is plain text: the first three lines are the job title, the employer and the location as shown on the job page, followed by the body of the ad. 15 are in English, 8 in German and 3 in French.

**What they are used for:** only as an evaluation set for this non-commercial learning project. They are not used to train a model and are not offered as a dataset. The text remains the property of the employers. Contact details of individual people are not included. If you are the employer of a posting and want it removed, please open an issue.

## labels.csv

One hand-made label per posting, written according to [docs/annotation_guidelines.md](../docs/annotation_guidelines.md). `scripts/check_labels.py` validates the file. The column `notes` records ambiguous cases.

## dev/

The development set for prompt work: 26 paraphrases of real Swiss job ads with their labels and source pages. See [dev/README.md](dev/README.md) for how it was made.
