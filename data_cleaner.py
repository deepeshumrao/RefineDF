"""
Data Sanitation - Data Cleaning Pipeline
=========================================
College project: "Data Sanitation"

Cleans a raw employee dataset so it is fit for analysis. Every cleaning step
is a separate, well-documented function, and the script prints a full
before/after data-quality summary.

Cleaning techniques demonstrated:
  1. Missing-value handling (drop / median imputation / explicit flags)
  2. Duplicate removal
  3. Text normalisation (whitespace stripping, consistent casing)
  4. Categorical standardisation (mapping variant labels to one canonical form)
  5. Format validation with regular expressions (email)
  6. Phone-number normalisation
  7. Multi-format date parsing
  8. Numeric coercion + outlier treatment with the IQR method
  9. Range validation (rating scale 1-5)

Usage:
    python3 data_cleaner.py
"""

import re
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "data" / "sample_dirty_data.csv"
OUTPUT_FILE = BASE_DIR / "data" / "cleaned_data.csv"
SUMMARY_FILE = BASE_DIR / "cleaning_summary.txt"

EMAIL_RE = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")

DEPARTMENT_MAP = {
    "hr": "HR",
    "human resources": "HR",
    "it": "IT",
    "information technology": "IT",
    "sales": "Sales",
    "finance": "Finance",
    "marketing": "Marketing",
}


# --------------------------------------------------------------------------
# Step 0 - Load & initial profiling
# --------------------------------------------------------------------------
def load_data(path: Path) -> pd.DataFrame:
    """Load the CSV as strings; treat blank fields as missing (NaN)."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return df.replace(r"^\s*$", pd.NA, regex=True)


def profile(df: pd.DataFrame) -> dict:
    """Snapshot of data-quality metrics used for the before/after report."""
    return {
        "rows": len(df),
        "missing_per_column": df.isna().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
    }


# --------------------------------------------------------------------------
# Step 1 - Duplicates
# --------------------------------------------------------------------------
def remove_duplicates(df: pd.DataFrame, log: list) -> pd.DataFrame:
    n = int(df.duplicated().sum())
    df = df.drop_duplicates(keep="first").reset_index(drop=True)
    log.append(f"Removed {n} exact duplicate row(s).")
    return df


# --------------------------------------------------------------------------
# Step 2 - Text normalisation (Name)
# --------------------------------------------------------------------------
def clean_names(df: pd.DataFrame, log: list) -> pd.DataFrame:
    df["Name"] = df["Name"].str.strip().str.title()
    dropped = int(df["Name"].isna().sum())
    df = df.dropna(subset=["Name"]).reset_index(drop=True)
    log.append(f"Normalised names (strip + title case); dropped {dropped} row(s) with no name.")
    return df


# --------------------------------------------------------------------------
# Step 3 - Categorical standardisation (Department)
# --------------------------------------------------------------------------
def standardise_departments(df: pd.DataFrame, log: list) -> pd.DataFrame:
    before = df["Department"].nunique(dropna=False)
    df["Department"] = (
        df["Department"].str.strip().str.lower().map(DEPARTMENT_MAP)
    )
    unmapped = int(df["Department"].isna().sum())
    df["Department"] = df["Department"].fillna("Unknown")
    log.append(
        f"Mapped {before} raw department label(s) to canonical values; "
        f"{unmapped} unmapped -> 'Unknown'."
    )
    return df


# --------------------------------------------------------------------------
# Step 4 - Email validation
# --------------------------------------------------------------------------
def clean_emails(df: pd.DataFrame, log: list) -> pd.DataFrame:
    df["Email"] = df["Email"].str.strip().str.lower()
    valid = df["Email"].str.match(EMAIL_RE, na=False)
    n_invalid = int((~valid).sum())
    df.loc[~valid, "Email"] = pd.NA
    log.append(f"Validated emails with regex; flagged {n_invalid} invalid/missing email(s).")
    return df


# --------------------------------------------------------------------------
# Step 5 - Phone normalisation
# --------------------------------------------------------------------------
def normalise_phone(raw) -> str | None:
    """Return a canonical +91-XXXXXXXXXX number, or None if invalid."""
    if pd.isna(raw):
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 12 and digits.startswith("91"):   # +91 country code
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):  # trunk prefix 0
        digits = digits[1:]
    if len(digits) == 10:
        return f"+91-{digits}"
    return None


def clean_phones(df: pd.DataFrame, log: list) -> pd.DataFrame:
    before_valid = df["Phone"].notna().sum()
    df["Phone"] = df["Phone"].apply(normalise_phone)
    n_invalid = int(df["Phone"].isna().sum())
    log.append(
        f"Normalised phone numbers to +91-XXXXXXXXXX; {n_invalid} invalid/missing "
        f"(was {before_valid} non-blank before validation)."
    )
    return df


# --------------------------------------------------------------------------
# Step 6 - Date parsing (multiple formats)
# --------------------------------------------------------------------------
def clean_dates(df: pd.DataFrame, log: list) -> pd.DataFrame:
    df["Date_of_Joining"] = pd.to_datetime(
        df["Date_of_Joining"], format="mixed", errors="coerce"
    )
    n_bad = int(df["Date_of_Joining"].isna().sum())
    df["Date_of_Joining"] = df["Date_of_Joining"].dt.strftime("%Y-%m-%d")
    log.append(f"Parsed mixed date formats to ISO (YYYY-MM-DD); {n_bad} unparseable/missing date(s).")
    return df


# --------------------------------------------------------------------------
# Step 7 - Salary: numeric coercion + IQR outlier capping
# --------------------------------------------------------------------------
def clean_salary(df: pd.DataFrame, log: list) -> pd.DataFrame:
    df["Salary"] = df["Salary"].str.replace(",", "", regex=False)
    df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce")
    n_negative = int((df["Salary"] < 0).sum())
    df.loc[df["Salary"] < 0, "Salary"] = pd.NA  # negative salary is impossible

    q1 = df["Salary"].quantile(0.25)
    q3 = df["Salary"].quantile(0.75)
    upper = q3 + 1.5 * (q3 - q1)  # Tukey upper fence
    n_outliers = int((df["Salary"] > upper).sum())
    df.loc[df["Salary"] > upper, "Salary"] = upper  # cap, don't delete

    median = df["Salary"].median()
    n_missing = int(df["Salary"].isna().sum())
    df["Salary"] = df["Salary"].fillna(median).round(0).astype(int)

    log.append(
        f"Coerced salary to numeric; fixed {n_negative} negative value(s); "
        f"capped {n_outliers} outlier(s) at IQR upper fence ({upper:,.0f}); "
        f"imputed {n_missing} missing value(s) with median ({median:,.0f})."
    )
    return df


# --------------------------------------------------------------------------
# Step 8 - Rating: range validation + median imputation
# --------------------------------------------------------------------------
def clean_ratings(df: pd.DataFrame, log: list) -> pd.DataFrame:
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
    out_of_range = int(((df["Rating"] < 1) | (df["Rating"] > 5)).sum())
    df.loc[(df["Rating"] < 1) | (df["Rating"] > 5), "Rating"] = pd.NA
    median = int(df["Rating"].median())
    n_missing = int(df["Rating"].isna().sum())
    df["Rating"] = df["Rating"].fillna(median).astype(int)
    log.append(
        f"Validated rating scale 1-5; fixed {out_of_range} out-of-range value(s); "
        f"imputed {n_missing} missing/invalid value(s) with median ({median})."
    )
    return df


# --------------------------------------------------------------------------
# Main pipeline
# --------------------------------------------------------------------------
def main() -> None:
    log: list[str] = []

    df = load_data(INPUT_FILE)
    before = profile(df)
    print(f"Loaded {before['rows']} rows from {INPUT_FILE.name}\n")

    df = remove_duplicates(df, log)
    df = clean_names(df, log)
    df = standardise_departments(df, log)
    df = clean_emails(df, log)
    df = clean_phones(df, log)
    df = clean_dates(df, log)
    df = clean_salary(df, log)
    df = clean_ratings(df, log)

    after = profile(df)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    # ---- summary report ----
    lines = [
        "DATA SANITATION - CLEANING SUMMARY",
        "=" * 40,
        "",
        f"Input rows : {before['rows']}",
        f"Output rows: {after['rows']}",
        "",
        "Missing values per column (before -> after):",
    ]
    for col in df.columns:
        lines.append(f"  {col:<16}: {before['missing_per_column'][col]:>3} -> {after['missing_per_column'][col]:>3}")
    lines += ["", "Cleaning actions:"]
    lines += [f"  - {entry}" for entry in log]
    lines += ["", f"Clean dataset written to: {OUTPUT_FILE.name}"]

    summary = "\n".join(lines)
    SUMMARY_FILE.write_text(summary + "\n", encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
