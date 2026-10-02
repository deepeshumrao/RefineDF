"""Generate a realistic 'dirty' employee dataset for the Data Sanitation project.

The dataset intentionally contains the most common real-world data quality issues:
  1. Missing values (empty fields)
  2. Duplicate rows
  3. Inconsistent text (extra spaces, mixed case)
  4. Inconsistent categorical labels (HR vs human resources vs Hr)
  5. Invalid emails
  6. Phone numbers in mixed formats / invalid
  7. Dates in mixed formats / invalid
  8. Salary as strings with commas, negatives and extreme outliers
  9. Rating outside the valid 1-5 scale
"""

import csv
import random
from pathlib import Path

random.seed(42)  # reproducible dataset

OUT = Path(__file__).resolve().parent / "data" / "sample_dirty_data.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

first = ["Aarav", "Priya", "Ramesh", "Sneha", "Vikram", "Ananya", "Rohit",
         "Kavya", "Arjun", "Meera", "Karthik", "Divya", "Nikhil", "Pooja",
         "Aditya", "Shreya", "Manoj", "Ishaan", "Tanya", "Rahul"]
last = ["Sharma", "Iyer", "Kumar", "Reddy", "Singh", "Nair", "Gupta",
        "Patel", "Mehta", "Joshi", "Das", "Khan"]

dept_variants = ["HR", "Hr", "human resources", "IT", "it ", "Information Technology",
                 "Sales", "SALES", "Finance", "finance", "Marketing", "MARKETING"]

date_formats = [
    lambda d: f"{d[0]}-{d[1]:02d}-{d[2]:02d}",          # 2021-03-15
    lambda d: f"{d[2]:02d}/{d[1]:02d}/{d[0]}",          # 15/03/2021
    lambda d: f"{d[2]:02d}-{d[1]:02d}-{d[0]}",          # 15-03-2021
    lambda d: f"{d[0]}/{d[1]:02d}/{d[2]:02d}",          # 2021/03/15
]
month_names = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May",
               6: "June", 7: "July", 8: "August", 9: "September",
               10: "October", 11: "November", 12: "December"}

rows = []
for i in range(1, 61):
    f, l = random.choice(first), random.choice(last)
    name = f"{f} {l}"
    # mess up the name casing / spacing sometimes
    r = random.random()
    if r < 0.10:
        name = f"  {name}  "
    elif r < 0.20:
        name = name.upper()
    elif r < 0.30:
        name = name.lower()

    email = f"{f.lower()}.{l.lower()}{random.randint(1,99)}@example.com"
    if random.random() < 0.08:
        email = email.upper()                       # inconsistent case
    elif random.random() < 0.14:
        email = random.choice(["not-an-email", "user@.com", "user@example",
                               "user @example.com", ""])  # invalid / blank

    phone = f"9{random.randint(100000000, 999999999)}"
    pr = random.random()
    if pr < 0.15:
        phone = f"+91-{phone[:5]} {phone[5:]}"       # +91-98765 43210
    elif pr < 0.30:
        phone = f"0{phone}"                          # leading zero
    elif pr < 0.40:
        phone = random.choice(["12345", "9876543210123", ""])  # invalid / blank

    y = random.randint(2018, 2024)
    m = random.randint(1, 12)
    d = random.randint(1, 28)
    fmt = random.choice(date_formats)
    doj = fmt((y, m, d))
    dr = random.random()
    if dr < 0.08:
        doj = f"{month_names[m]} {d}, {y}"           # March 15, 2021
    elif dr < 0.14:
        doj = random.choice(["not-a-date", "32/13/2020", ""])  # invalid / blank

    salary = random.randint(30000, 120000)
    sr = random.random()
    if sr < 0.08:
        salary = f"{salary:,}"                       # "1,20,000" style string
    elif sr < 0.12:
        salary = 999999999                            # extreme outlier
    elif sr < 0.16:
        salary = -5000                                # impossible negative
    elif sr < 0.20:
        salary = ""                                   # missing

    rating = random.randint(1, 5)
    rr = random.random()
    if rr < 0.08:
        rating = random.choice([0, 7, -1])           # out of scale
    elif rr < 0.14:
        rating = random.choice(["N/A", ""])          # non-numeric / blank

    dept = random.choice(dept_variants)

    rows.append([f"EMP{i:03d}", name, dept, email, str(phone), doj,
                 str(salary), str(rating)])

# --- inject issues ---
# 1) exact duplicate rows
for idx in random.sample(range(len(rows)), 6):
    rows.append(list(rows[idx]))

# 2) rows with several missing fields
rows.append(["EMP901", "", "Sales", "", "", "", "", ""])       # almost empty
rows.append(["EMP902", "Test User", "", "test@example.com", "", "2020-01-01", "", "3"])

random.shuffle(rows)

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Employee_ID", "Name", "Department", "Email", "Phone",
                "Date_of_Joining", "Salary", "Rating"])
    w.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUT}")
