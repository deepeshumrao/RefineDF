# Data Sanitation: Cleaning Raw Data for Analysis

**Project report**

---

## Abstract

Real-world datasets are rarely analysis-ready: they contain missing values,
duplicates, inconsistent formats and invalid entries. This project builds a
complete, reproducible data-cleaning pipeline in Python (pandas) that takes a
raw employee dataset with nine categories of deliberately introduced data-quality
issues and produces a validated, analysis-ready dataset. The pipeline reduced
68 raw rows to 61 clean rows, eliminated all duplicates, standardised 13
department label variants into 6 canonical values, and enforced valid ranges on
every column.

---

## 1. Introduction

"Data sanitation" (data cleaning) is the process of detecting and correcting
corrupt, inaccurate or irrelevant records in a dataset. Industry studies
consistently find that data scientists spend the majority of their time
cleaning data rather than modelling it — because analysis performed on dirty
data produces misleading results ("garbage in, garbage out"). This project
demonstrates the core sanitation techniques on a realistic dataset.

## 2. Problem Statement

Given a raw employee-records CSV collected from multiple inconsistent sources,
produce a clean dataset that satisfies:

- No duplicate records
- No missing values in critical fields (name, department, salary, rating)
- Consistent text formatting and categorical labels
- Valid emails, phone numbers, dates, salaries and ratings

## 3. Objectives

1. Identify and categorise the data-quality issues present in the raw dataset.
2. Implement an automated, repeatable cleaning pipeline (one function per issue).
3. Apply statistically sound treatments: median imputation, IQR outlier capping,
   regex validation and canonical-format mapping.
4. Produce a before/after quality report proving the dataset is analysis-ready.

## 4. Dataset Description

`data/sample_dirty_data.csv` — 68 employee records, 8 columns, generated with a
fixed random seed so the experiment is fully reproducible (`make_dataset.py`).

| Column | Type | Intended issues |
|---|---|---|
| Employee_ID | string | key, always present |
| Name | string | extra whitespace, random UPPER/lower casing, 1 missing |
| Department | category | 13 label variants (`HR`, `Hr`, `human resources`, `it `, …) |
| Email | string | invalid formats (`not-an-email`, `user@.com`), wrong case, missing |
| Phone | string | 4 formats (`+91-98765 43210`, `09876543210`, `12345`, …), missing |
| Date_of_Joining | date | 5 formats (`2021-03-15`, `15/03/2021`, `March 15, 2021`, …), invalid, missing |
| Salary | numeric | comma-formatted strings, a negative value, extreme outlier (999,999,999), missing |
| Rating | 1–5 scale | out-of-range values (0, 7, −1), `N/A` strings, missing |

Additionally, 6 exact duplicate rows were injected.

## 5. Methodology

The pipeline (`data_cleaner.py`) applies one technique per issue, in an order
that matters — e.g. duplicates are removed before statistics like the median
are computed, so duplicates cannot distort imputation values.

1. **Duplicate removal** — exact row duplicates dropped (`pandas.drop_duplicates`).
2. **Text normalisation** — names stripped of surrounding whitespace and converted
   to title case; the single nameless record was dropped (a record with no name
   cannot be analysed or joined).
3. **Categorical standardisation** — a mapping dictionary collapses all 13 raw
   department labels to canonical values (`HR`, `IT`, `Sales`, `Finance`,
   `Marketing`); anything unmapped becomes `Unknown` rather than being deleted.
4. **Email validation** — lowercased, then checked against a standard email regex;
   invalid entries are flagged as missing instead of silently kept.
5. **Phone normalisation** — all non-digit characters removed; `+91` country code
   and `0` trunk prefix handled; only 10-digit numbers kept, formatted as
   `+91-XXXXXXXXXX`.
6. **Date parsing** — `pandas.to_datetime` with mixed-format inference parses all
   five formats into ISO `YYYY-MM-DD`; unparseable strings become missing.
7. **Salary treatment** — commas stripped, coerced to numeric; the negative value
   discarded; outliers **capped** (not deleted) at Tukey's upper fence
   Q3 + 1.5·IQR; missing values imputed with the **median** (robust to skew,
   unlike the mean).
8. **Rating validation** — coerced to numeric; values outside 1–5 discarded;
   missing values imputed with the median rating.

A deliberate design choice: fields that are genuinely unrecoverable (an invalid
email, an unparseable date) are left as missing and reported, rather than
fabricated — inventing data is worse than admitting it is absent.

## 6. Implementation

- Language: Python 3.12; libraries: pandas 2.1.4, numpy 1.26.4.
- Each cleaning step is an independent, documented function, so steps can be
  reordered, tested or extended individually.
- The script prints a full before/after summary and saves it to
  `cleaning_summary.txt`; the cleaned dataset is written to
  `data/cleaned_data.csv`.

Run with:

```bash
pip install -r requirements.txt
python3 data_cleaner.py
```

## 7. Results

Actual pipeline output:

| Metric | Before | After |
|---|---|---|
| Total rows | 68 | **61** |
| Duplicate rows | 6 | **0** |
| Department labels | 13 variants | **6 canonical** |
| Missing names | 1 | **0** (row dropped) |
| Invalid/missing emails | 8 flagged | reported, not fabricated |
| Invalid/missing phones | 6 | reported, rest in `+91-XXXXXXXXXX` format |
| Unparseable/missing dates | 3 | reported, rest ISO `YYYY-MM-DD` |
| Salary issues | 1 negative, 3 outliers, 2 missing | negative removed, outliers capped at **178,709**, missing imputed with median **65,774** |
| Rating issues | 4 out-of-range, 9 missing/invalid | all in **1–5**, missing imputed with median **3** |

Post-cleaning verification confirmed: 0 duplicates, salary range 34,117–178,709,
ratings strictly within 1–5, and every date in ISO format. The dataset is now
fit for analysis (e.g. average salary by department, rating distributions).

## 8. Observations and Limitations

- Median imputation preserves the sample size but slightly reduces variance;
  for a production system, model-based imputation could be compared.
- Outlier capping keeps the records (and their other valid fields) instead of
  deleting rows — preferable when data is scarce.
- Unrecoverable fields (8 emails, 6 phones, 3 dates) remain missing; any
  downstream analysis must handle or exclude them explicitly.

## 9. Conclusion

The project demonstrates that data sanitation is a systematic engineering
process, not manual fixing: each class of defect maps to a specific,
automatable technique, applied in a principled order, with every decision
logged in a reproducible report. The resulting pipeline turns 68 messy records
into 61 trustworthy ones.

## 10. Future Scope

- Interactive HTML quality dashboard (before/after charts per column).
- Configurable rules file (YAML) so the pipeline works on any CSV without code changes.
- Fuzzy duplicate detection (near-duplicates, not just exact matches).
- Automated anomaly detection for streaming data.

## References

- pandas documentation — https://pandas.pydata.org/docs/
- Tukey, J. W. *Exploratory Data Analysis* (IQR outlier fences), 1977.
- Rahm, E. & Do, H. H. "Data Cleaning: Problems and Current Approaches",
  *IEEE Data Engineering Bulletin*, 2000.
