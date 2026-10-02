# RefineDF

**Team HexaMind** — Team Leader: Divyanshi Srivastava · Members: Lavanya,
Lakshya Rampal, Himanshu Singh, Deepesh Umrao, Bhumi Chaurasiya

> RefineDF is a universal data engine that allows users from any industry
> to upload flawed CSV files for instant removal of duplicates, error
> correction & automated missing value handling.

A **Tkinter desktop application** for data sanitation **and** data wrangling,
built with professional OOP design. It uses **NumPy and Pandas heavily**
for all data work, with a light **Matplotlib** layer for charts.

**Official use cases:**
- Healthcare — Patient Health Record Purification
- E-commerce — Product Sale & Review Cleaner
- HR & Recruitment — Applicant Data Standardizer

## Run the app

```bash
pip install -r requirements.txt
python3 main.py
```

(`tkinter` comes with Python itself. On some Linux systems: `sudo apt install python3-tk`)

## Project structure

```
data-sanitation/
├── main.py                  # entry point: python3 main.py
├── src/
│   ├── __init__.py          # package exports
│   ├── theme.py             # visual identity: dark-minimal palette, fonts, widget styler
│   ├── loaders.py           # DataLoader ABC + CSV/Excel/JSON/XML loaders (Strategy+Factory)
│   ├── profiler.py          # DataProfiler: read-only health reports
│   ├── sanitizer.py         # DataSanitizer: cleaning engine (fluent interface)
│   ├── wrangler.py          # DataWrangler: manipulation engine (fluent interface)
│   ├── visualizer.py        # Visualizer: Matplotlib figures for the GUI
│   └── app.py               # SanitizerApp: the Tkinter GUI (zero cleaning logic)
├── data/
│   ├── sample_dirty_data.csv   # 68-row messy dataset (master copy)
│   ├── sample_dirty_data.xlsx  # same data as Excel  (make_sample_formats.py)
│   ├── sample_dirty_data.json  # same data as JSON
│   ├── sample_dirty_data.xml   # same data as XML
│   ├── healthcare_patients.csv # use-case demo: patient records (messy)
│   ├── ecommerce_products.csv  # use-case demo: product catalog (messy)
│   └── hr_applicants.csv       # use-case demo: job applicants (messy)
├── make_dataset.py          # regenerates the dirty CSV (seeded, reproducible)
├── make_sample_formats.py   # converts the CSV to xlsx/json/xml
├── make_use_case_datasets.py # generates healthcare/e-commerce/HR demo datasets
├── data_cleaner.py          # earlier pandas-pipeline prototype (kept for reference)
├── PROJECT_REPORT.md        # project report (prototype version)
└── README.md
```

## What the app does

**Inspect tab** — full data profile: shape, memory, dtypes, missing values,
duplicates, unique counts, NumPy numeric summary.

**Clean tab** — missing values (drop / mean / median / mode / ffill / bfill /
interpolate / custom), duplicates, type conversion (auto / numeric / datetime),
text cleanup (strip, lower/upper/title/capitalize), IQR outlier capping &
removal, regex & range validation.

**Wrangle tab** — query filtering, top/bottom N, sorting, ranking, column
select/drop/rename, melt, pivot, groupby aggregation, merge & concat (with a
second file), one-hot & label encoding, date-part extraction, and NumPy-powered
`np.where` conditional columns plus vectorized math columns.

**Visualize tab** — missing-value bars, before/after histograms & boxplots,
dtype pie chart, correlation heatmap. Before/after charts compare the data
as-loaded against its current state.

Every action is written to the **Action Log** console, and **Export Report**
saves the profile plus the full log as a text file.

## Design notes

- `theme.py` holds the entire visual identity (minimalistic dark theme:
  near-black backgrounds, electric-blue accent, white typography,
  pill-shaped gradient buttons, rounded card panels, blue glow header).
  To re-theme the app, edit that one file. Rounded corners and gradients
  are generated natively with Pillow + Canvas drawing (Tkinter can't use
  CSS) -- see the module docstring.
- `DataLoader` uses the Strategy + Factory patterns: new file formats plug in
  with one new class, no if/else chains anywhere.
- `DataSanitizer` / `DataWrangler` use a fluent interface (`obj.a().b()`)
  and work on defensive copies — your raw file is never modified.
- The GUI (`app.py`) contains no cleaning logic; it only calls the engines.
  The engines are fully usable and testable without any GUI.
- Nearly every line is commented so the code doubles as a learning resource.
