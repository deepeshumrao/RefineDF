"""
profiler.py
===========
PURPOSE: inspect a DataFrame and produce a "health report" about it.

The DataProfiler class is deliberately READ-ONLY: every method only READS
the DataFrame, never changes it. Profiling (asking "what is wrong?") and
cleaning (actually fixing it) are kept as separate responsibilities --
this is the "separation of concerns" principle from good OOP design.

Usage:
    profiler = DataProfiler(df)      # wrap any DataFrame
    print(profiler.basic_info())     # quick numbers as a dict
    print(profiler.full_report())    # pretty multi-line text for the GUI
"""

# numpy is used for fast numeric summaries (means, standard deviations...)
import numpy as np

# pandas is imported for type hints / explicit pandas API usage.
import pandas as pd


class DataProfiler:
    """
    A read-only inspector for a pandas DataFrame.

    Create it with the DataFrame you want to examine; then call any of the
    methods below. The DataFrame itself is never modified.
    """

    def __init__(self, df):
        # We store a REFERENCE to the DataFrame, not a copy.
        # Copying would double the memory for no benefit, because we promise
        # never to modify it (all methods below are read-only).
        self.df = df

    # ------------------------------------------------------------------
    # Basic shape / size information
    # ------------------------------------------------------------------
    def basic_info(self):
        """
        Return a dictionary with the fundamental facts about the DataFrame.

        Keys:
            rows         - number of rows (records)
            columns      - number of columns (fields)
            shape        - the (rows, columns) tuple, e.g. (68, 8)
            total_cells  - rows * columns, i.e. every single cell
            dimensions   - always 2 for a DataFrame (it is a 2-D table)
            memory_bytes - RAM used, counting the real text inside strings
        """
        # .shape        -> tuple (n_rows, n_columns)
        # .size         -> total number of cells (rows * columns)
        # .ndim         -> number of dimensions (2 for DataFrame)
        # .memory_usage(deep=True) -> bytes per column; deep=True also measures
        #   the actual characters inside text columns; .sum() adds them up.
        return {
            "rows": self.df.shape[0],
            "columns": self.df.shape[1],
            "shape": self.df.shape,
            "total_cells": self.df.size,
            "dimensions": self.df.ndim,
            "memory_bytes": int(self.df.memory_usage(deep=True).sum()),
        }

    # ------------------------------------------------------------------
    # Column data types
    # ------------------------------------------------------------------
    def dtypes_summary(self):
        """
        Return {column_name: dtype_as_string}, e.g. {"Age": "int64"}.

        Knowing the dtype of each column is the FIRST step of sanitation:
        a "Salary" column stored as text (object) cannot be averaged until
        it is converted to a number.
        """
        # .dtypes is a Series of dtype OBJECTS; .astype(str) converts each to
        # a readable string like "int64" / "float64" / "object"; .to_dict()
        # turns the Series into a plain Python dictionary.
        return self.df.dtypes.astype(str).to_dict()

    # ------------------------------------------------------------------
    # Missing values
    # ------------------------------------------------------------------
    def missing_summary(self):
        """
        Return {column_name: missing_count}, but ONLY for columns that
        actually have missing values (clean columns are left out so the
        report stays short and focused).
        """
        # .isna()  -> a True/False table, True where the cell is missing
        #            (None, NaN, NaT all count as missing).
        # .sum()   -> adds up the True values column-wise (True == 1).
        missing = self.df.isna().sum()
        # missing > 0 keeps only columns with at least one gap; .to_dict()
        # converts the filtered Series to a dictionary.
        return missing[missing > 0].to_dict()

    def missing_percent(self):
        """
        Same as missing_summary(), but as a PERCENTAGE of total rows,
        rounded to 2 decimals. 50% missing means something very different
        from 0.5% missing -- percentages give that context instantly.
        """
        missing = self.df.isna().sum()          # raw counts per column
        percent = (missing / len(self.df) * 100).round(2)  # to %
        return percent[percent > 0].to_dict()   # keep only columns with gaps

    # ------------------------------------------------------------------
    # Duplicates
    # ------------------------------------------------------------------
    def duplicate_count(self):
        """
        Return how many rows are EXACT duplicates of an earlier row.

        Example: if rows 5 and 9 are identical, the count is 1
        (the first occurrence is the "original", later ones are duplicates).
        """
        # .duplicated() -> True for every row that repeats an earlier row.
        # .sum() counts the True values; int() converts numpy int -> Python int.
        return int(self.df.duplicated().sum())

    # ------------------------------------------------------------------
    # Uniqueness
    # ------------------------------------------------------------------
    def unique_counts(self):
        """
        Return {column_name: number_of_distinct_values}.

        This quickly reveals the NATURE of a column:
          unique == rows   -> probably an ID column
          unique == 1      -> constant column (maybe useless)
          unique small     -> categorical column (e.g. Department)
        """
        # .nunique() counts distinct non-missing values per column.
        return self.df.nunique().to_dict()

    # ------------------------------------------------------------------
    # Numeric summaries via NumPy
    # ------------------------------------------------------------------
    def numeric_summary(self):
        """
        Return {column: {mean, median, std, min, max}} for numeric columns,
        computed with NumPy's NaN-aware functions (they SKIP missing values
        instead of crashing on them -- the "nan" in nanmean means "ignore NaN").

        This shows NumPy working directly on the DataFrame's underlying
        arrays via .to_numpy().
        """
        result = {}  # we will fill this dict column by column
        # .select_dtypes(include="number") keeps ONLY numeric columns,
        # because mean/std make no sense on text.
        for col in self.df.select_dtypes(include="number").columns:
            # .to_numpy() extracts the column as a raw NumPy array --
            # this is the bridge between pandas and NumPy.
            values = self.df[col].to_numpy(dtype=float)
            result[col] = {
                # np.nanmean / nanmedian / nanstd / nanmin / nanmax:
                # same as mean/median/std/min/max but they IGNORE NaN.
                "mean": float(np.nanmean(values)),
                "median": float(np.nanmedian(values)),
                "std": float(np.nanstd(values)),
                "min": float(np.nanmin(values)),
                "max": float(np.nanmax(values)),
            }
        return result

    # ------------------------------------------------------------------
    # Full statistical description (pandas)
    # ------------------------------------------------------------------
    def describe(self):
        """
        Return pandas' describe() table: count/mean/std/min/max for numbers
        plus count/unique/top/frequency for text columns.

        include="all" is what makes text columns appear too (by default
        describe() only shows numeric columns).
        """
        return self.df.describe(include="all")

    # ------------------------------------------------------------------
    # One combined human-readable report
    # ------------------------------------------------------------------
    def full_report(self):
        """
        Combine every check above into ONE pretty multi-line string.

        The GUI's "Inspect" tab displays exactly this text, and the
        "Export Report" button saves it to a file.
        """
        info = self.basic_info()  # grab the basic numbers once, reuse below
        lines = []                # collect output line by line, join at end

        lines.append("=== DATA PROFILE ===")
        lines.append(f"Shape: {info['rows']} rows x {info['columns']} columns")
        lines.append(f"Total cells: {info['total_cells']:,}")
        lines.append(f"Memory usage: {info['memory_bytes']:,} bytes")
        lines.append("")  # blank line separates sections visually

        lines.append("--- Data types ---")
        for col, dtype in self.dtypes_summary().items():
            lines.append(f"  {col}: {dtype}")
        lines.append("")

        lines.append("--- Missing values ---")
        missing = self.missing_summary()  # {col: count} for gappy columns
        if missing:  # a non-empty dict is truthy -> there ARE gaps
            for col, count in missing.items():
                pct = self.missing_percent()[col]  # matching percentage
                lines.append(f"  {col}: {count} missing ({pct}%)")
        else:
            lines.append("  None -- every cell is filled.")
        lines.append("")

        dupes = self.duplicate_count()
        lines.append(f"--- Duplicates: {dupes} exact duplicate row(s) ---")
        lines.append("")

        lines.append("--- Unique values per column ---")
        for col, count in self.unique_counts().items():
            lines.append(f"  {col}: {count} unique")
        lines.append("")

        lines.append("--- Numeric summary (NumPy) ---")
        for col, stats in self.numeric_summary().items():
            lines.append(
                f"  {col}: mean={stats['mean']:.2f}, median={stats['median']:.2f}, "
                f"std={stats['std']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}"
            )

        # "\n".join() glues the list into ONE string with line breaks.
        return "\n".join(lines)
