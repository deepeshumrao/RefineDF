"""
make_sample_formats.py
======================
Generate the sample dirty dataset in EVERY supported format (Excel, JSON,
XML) from the master CSV, so you can test each loader in the GUI:

    python3 make_sample_formats.py

The files land in data/: sample_dirty_data.xlsx / .json / .xml
"""

# Path: build file locations relative to THIS script, so it works no
# matter which folder you run it from.
from pathlib import Path

# pandas does all the converting; each to_* method is one line.
import pandas as pd

# The project root is the folder CONTAINING this script.
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"  # the data/ subfolder


def main():
    """Read the master CSV and re-export it in three more formats."""
    # Step 1: read the master CSV (dtype=str keeps every value as text,
    # exactly as the raw file stores it).
    df = pd.read_csv(DATA / "sample_dirty_data.csv", dtype=str)

    # Step 2a: Excel. index=False avoids writing a stray index column.
    # (Needs the 'openpyxl' package -- see requirements.txt.)
    df.to_excel(DATA / "sample_dirty_data.xlsx", index=False)

    # Step 2b: JSON as a list of records: [{"col": val}, ...].
    # orient="records" gives the most human-readable layout; indent=2
    # pretty-prints it with 2-space indentation.
    df.to_json(DATA / "sample_dirty_data.json", orient="records", indent=2)

    # Step 2c: XML with <data><row><Col>val</Col>...</row></data> structure,
    # which is exactly what pd.read_xml() (our XMLLoader) expects back.
    # (Needs the 'lxml' package -- see requirements.txt.)
    df.to_xml(DATA / "sample_dirty_data.xml", index=False)

    print("Wrote sample_dirty_data.xlsx / .json / .xml into data/")


# Standard entry-point guard: run main() only when executed directly.
if __name__ == "__main__":
    main()
