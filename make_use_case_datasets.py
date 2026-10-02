"""
make_use_case_datasets.py
=========================
Generate THREE dirty sample datasets -- one per official RefineDF use case
from the team brief (team HexaMind):

  1. healthcare_patients.csv  - Healthcare: Patient Health Record Purification
  2. ecommerce_products.csv   - E-commerce: Product Sale & Review Cleaner
  3. hr_applicants.csv        - HR & Recruitment: Applicant Data Standardizer

Each file is DELIBERATELY messy (missing values, duplicates, inconsistent
labels, mixed formats, outliers...) so the team can demo RefineDF's
cleaning on realistic domain data.

Run:
    python3 make_use_case_datasets.py
"""

# csv: writing the datasets row by row.
import csv

# random: generating the messy values (seeded -> reproducible every run).
import random

# Path: locate the data/ folder relative to THIS script.
from pathlib import Path

# Fixed seed: the same "random" mess is generated on every run, so demos
# and tests are reproducible.
random.seed(2026)

# The data/ subfolder next to this script; created if missing.
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(filename, header, rows):
    """Write one dataset: header row + data rows into data/<filename>."""
    path = DATA_DIR / filename
    # newline="" avoids blank lines on Windows; utf-8 handles names safely.
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)  # the column names first...
        writer.writerows(rows)   # ...then every data row.
    print(f"Wrote {len(rows)} rows -> {path.name}")


def messy_name(first, last):
    """Return a name with random casing/spacing defects (shared helper)."""
    name = f"{first} {last}"
    r = random.random()  # one dice roll decides the defect (or none)
    if r < 0.12:
        name = f"  {name}  "   # stray spaces
    elif r < 0.22:
        name = name.upper()     # ALL CAPS
    elif r < 0.32:
        name = name.lower()     # all lowercase
    return name


def messy_phone():
    """Return an Indian mobile number in a random (sometimes bad) format."""
    digits = f"9{random.randint(100000000, 999999999)}"  # 10-digit number
    r = random.random()
    if r < 0.20:
        return f"+91-{digits[:5]} {digits[5:]}"  # +91-98765 43210
    if r < 0.35:
        return f"0{digits}"                      # leading zero
    if r < 0.42:
        return random.choice(["12345", ""])      # invalid / missing
    return digits                                # clean format


def messy_date(year_lo=2022, year_hi=2024):
    """Return a date in a random format (sometimes invalid/missing)."""
    y = random.randint(year_lo, year_hi)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    r = random.random()
    if r < 0.30:
        return f"{y}-{m:02d}-{d:02d}"      # 2023-04-15 (ISO)
    if r < 0.55:
        return f"{d:02d}/{m:02d}/{y}"      # 15/04/2023
    if r < 0.70:
        return f"{d:02d}-{m:02d}-{y}"      # 15-04-2023
    if r < 0.80:
        return f"{m:02d}/{d:02d}/{y}"      # 04/15/2023 (US style!)
    if r < 0.86:
        return random.choice(["not-a-date", ""])  # garbage / missing
    return f"{y}-{m:02d}-{d:02d}"


# ---------------------------------------------------------------------------
# USE CASE 1: Healthcare -- Patient Health Record Purification
# ---------------------------------------------------------------------------
def make_healthcare():
    """Build a messy patient-records dataset."""
    first = ["Aarav", "Priya", "Rohan", "Sneha", "Vikram", "Ananya",
             "Rahul", "Kavya", "Arjun", "Meera", "Ishaan", "Divya"]
    last = ["Sharma", "Patel", "Khan", "Reddy", "Gupta", "Nair",
            "Singh", "Joshi", "Das", "Mehta"]
    # Same blood group written many ways -- the classic standardisation demo.
    blood_variants = ["O+", "o+", "O +", "O Positive", "A+", "a+",
                      "B+", "b +", "AB-", "ab-", "AB -", "O-", ""]
    # Same gender written many ways.
    gender_variants = ["M", "Male", "male", "MALE", "F", "Female",
                       "female", "FEMALE", ""]
    diagnoses = ["Diabetes", "diabetes", "DIABETES", "Type 2 Diabetes",
                 "Hypertension", "hypertension", "Asthma", "asthma",
                 "Migraine", ""]

    header = ["Patient_ID", "Name", "Age", "Gender", "Blood_Group", "Phone",
              "Admission_Date", "Diagnosis", "Bill_Amount"]
    rows = []
    for i in range(1, 56):
        # Age: mostly fine, sometimes missing, once in a while impossible.
        age = random.randint(5, 90)
        r = random.random()
        if r < 0.08:
            age = ""
        elif r < 0.12:
            age = random.choice([200, -5])  # impossible ages

        # Bill: comma strings, one extreme outlier, one negative, missing.
        bill = random.randint(5000, 200000)
        r = random.random()
        if r < 0.10:
            bill = f"{bill:,}"      # "45,000" style string
        elif r < 0.14:
            bill = 99999999         # extreme outlier
        elif r < 0.17:
            bill = -1000            # impossible negative
        elif r < 0.22:
            bill = ""

        rows.append([
            f"PAT{i:03d}",
            messy_name(random.choice(first), random.choice(last)),
            str(age),
            random.choice(gender_variants),
            random.choice(blood_variants),
            messy_phone(),
            messy_date(),
            random.choice(diagnoses),
            str(bill),
        ])
    # Inject exact duplicates (a classic hospital-merge defect).
    for idx in random.sample(range(len(rows)), 5):
        rows.append(list(rows[idx]))
    random.shuffle(rows)
    write_csv("healthcare_patients.csv", header, rows)


# ---------------------------------------------------------------------------
# USE CASE 2: E-commerce -- Product Sale & Review Cleaner
# ---------------------------------------------------------------------------
def make_ecommerce():
    """Build a messy product-catalog dataset."""
    products = [("boAt Headphones", "Electronics"), ("Kurti Set", "Fashion"),
                ("Mixer Grinder", "Home & Kitchen"), ("Running Shoes", "Fashion"),
                ("Smart Watch", "Electronics"), ("Cooker 5L", "Home & Kitchen"),
                ("Backpack", "Fashion"), ("LED Bulb Pack", "Electronics")]
    # Same category written many ways.
    cat_map = {"Electronics": ["Electronics", "electronics", "ELECTRONICS", "Elec."],
               "Fashion": ["Fashion", "fashion", "FASHION", "Apparel"],
               "Home & Kitchen": ["Home & Kitchen", "home & kitchen",
                                  "HOME & KITCHEN", "Home and Kitchen"]}
    sellers = ["SellerA", "sellera", "SELLERA", "BestDeals", "bestdeals",
               "QuickKart", "quickkart", ""]

    header = ["Product_ID", "Product_Name", "Category", "Price", "Rating",
              "Reviews_Count", "Seller", "Listed_Date"]
    rows = []
    for i in range(1, 56):
        name, cat = random.choice(products)
        # Price: rupee symbols, commas, missing.
        price = random.randint(199, 49999)
        r = random.random()
        if r < 0.12:
            price = f"₹{price:,}"   # "₹1,299" style string
        elif r < 0.18:
            price = f"{price:,}"
        elif r < 0.22:
            price = ""

        # Rating: 1-5 scale, but with out-of-range and text junk.
        rating = random.randint(1, 5)
        r = random.random()
        if r < 0.08:
            rating = random.choice([0, 6, -1])
        elif r < 0.14:
            rating = random.choice(["N/A", ""])

        # Reviews: comma-formatted counts, missing.
        reviews = random.randint(0, 50000)
        if random.random() < 0.15:
            reviews = f"{reviews:,}"
        elif random.random() < 0.22:
            reviews = ""

        rows.append([
            f"PRD{i:03d}",
            messy_name(name, "").strip(),  # reuse the casing/spacing helper
            random.choice(cat_map[cat]),
            str(price),
            str(rating),
            str(reviews),
            random.choice(sellers),
            messy_date(2021, 2024),
        ])
    for idx in random.sample(range(len(rows)), 5):
        rows.append(list(rows[idx]))
    random.shuffle(rows)
    write_csv("ecommerce_products.csv", header, rows)


# ---------------------------------------------------------------------------
# USE CASE 3: HR & Recruitment -- Applicant Data Standardizer
# ---------------------------------------------------------------------------
def make_hr():
    """Build a messy job-applicant dataset."""
    first = ["Aarav", "Priya", "Rohan", "Sneha", "Vikram", "Ananya",
             "Rahul", "Kavya", "Arjun", "Meera", "Ishaan", "Divya"]
    last = ["Sharma", "Patel", "Khan", "Reddy", "Gupta", "Nair",
            "Singh", "Joshi", "Das", "Mehta"]
    # Same degree written many ways -- the standardisation demo.
    degrees = ["B.Tech", "BTech", "b.tech", "Bachelor of Technology",
               "M.Tech", "mtech", "MBA", "mba", "BCA", "bca", ""]
    universities = ["IIT Delhi", "iit delhi", "IIT DELHI", "Mumbai University",
                    "mumbai university", "Anna University", "ANNA UNIVERSITY",
                    "Delhi University", ""]
    # Same status written many ways.
    statuses = ["Selected", "selected", "SELECTED", "Rejected", "rejected",
                "REJECTED", "On Hold", "on_hold", "On hold", ""]

    header = ["Applicant_ID", "Name", "Email", "Phone", "Degree",
              "University", "Experience_Years", "Applied_Date", "Status"]
    rows = []
    for i in range(1, 56):
        f, l = random.choice(first), random.choice(last)
        # Email: mostly fine, sometimes broken.
        email = f"{f.lower()}.{l.lower()}{random.randint(1, 99)}@example.com"
        if random.random() < 0.12:
            email = random.choice(["not-an-email", "user@.com", ""])

        # Experience: numbers, "N years" text, "Fresher" variants, missing.
        exp = random.randint(0, 12)
        r = random.random()
        if r < 0.12:
            exp = f"{exp} years"
        elif r < 0.20:
            exp = random.choice(["Fresher", "fresher", "FRESHER"])
        elif r < 0.24:
            exp = ""

        rows.append([
            f"APP{i:03d}",
            messy_name(f, l),
            email,
            messy_phone(),
            random.choice(degrees),
            random.choice(universities),
            str(exp),
            messy_date(2023, 2024),
            random.choice(statuses),
        ])
    for idx in random.sample(range(len(rows)), 5):
        rows.append(list(rows[idx]))
    random.shuffle(rows)
    write_csv("hr_applicants.csv", header, rows)


# ---------------------------------------------------------------------------
# Run all three generators.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    make_healthcare()
    make_ecommerce()
    make_hr()
    print("All use-case datasets generated in data/")
