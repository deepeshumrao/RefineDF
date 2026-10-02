"""
wrangler.py
===========
PURPOSE: the MANIPULATION ENGINE -- reshape, transform and combine data
to fit YOUR needs (this is "data wrangling", the second half of the project).

Same senior-developer conventions as sanitizer.py:
  * FLUENT INTERFACE: every method returns `self` for chaining.
  * DEFENSIVE COPY: works on df.copy(); your original is never touched.
  * ACTION LOG: every step is recorded in self.log.

pandas does the DataFrame reshaping; NumPy powers the vectorised
column math (np.where, arithmetic on whole columns at once).
"""

# operator gives us function versions of symbols: operator.gt is ">",
# operator.add is "+", ... This lets the GUI pass ">" as a STRING and we
# convert it to a real comparison function -- no eval(), no security risk.
import operator

# numpy: vectorised conditional logic (np.where) and array math
import numpy as np

# pandas: the reshaping / combining / groupby machinery
import pandas as pd


class DataWrangler:
    """
    Manipulation engine for one DataFrame.

    Usage:
        wrangler = DataWrangler(df)
        wrangler.filter_query("Age > 30").sort_values("Salary")
        result = wrangler.get_dataframe()
    """

    def __init__(self, df):
        # Defensive copy: wrangling must never corrupt the caller's data.
        self.df = df.copy()
        # Action log, same idea as in DataSanitizer.
        self.log = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _log(self, message):
        """Append one human-readable entry to the action log."""
        self.log.append(message)

    def get_dataframe(self):
        """Return the current (wrangled) DataFrame."""
        return self.df

    def get_log(self):
        """Return the action log as a list of strings, in order."""
        return self.log

    # ================================================================
    # 1. FILTERING ROWS
    # ================================================================
    def filter_query(self, query_string):
        """
        Keep ONLY rows matching a pandas query expression, e.g.
            filter_query("Age > 30 and Department == 'IT'")

        The query language supports: >, <, >=, <=, ==, !=, and, or, not,
        in, not in. Column names with spaces need backticks: `My Col` > 5.
        """
        before = len(self.df)
        # .query() parses the string and filters -- much more readable than
        # building boolean masks by hand for complex conditions.
        self.df = self.df.query(query_string)
        kept = len(self.df)
        self._log(f"Filtered with query \"{query_string}\": "
                  f"{kept}/{before} rows kept.")
        return self

    def top_n(self, column, n=5, largest=True):
        """
        Keep the n rows with the LARGEST (or SMALLEST) values in a column.
        Example: top_n("Salary", 10) -> the 10 highest-paid employees.
        """
        before = len(self.df)
        if largest:
            # .nlargest(n, col): the n rows with the biggest values in col.
            self.df = self.df.nlargest(n, column)
        else:
            # .nsmallest(n, col): the mirror image.
            self.df = self.df.nsmallest(n, column)
        self._log(f"Selected top {n} {'largest' if largest else 'smallest'} "
                  f"rows by '{column}' ({before} -> {len(self.df)} rows).")
        return self

    def sample_rows(self, n=5, random_state=42):
        """
        Keep n RANDOM rows -- handy for spot-checking a huge dataset
        without loading it all into your head.

        random_state=42 fixes the "randomness" so the sample is
        REPRODUCIBLE: you get the same rows every run.
        """
        self.df = self.df.sample(n=n, random_state=random_state)
        self._log(f"Sampled {n} random rows (random_state={random_state}).")
        return self

    # ================================================================
    # 2. SORTING & RANKING
    # ================================================================
    def sort_values(self, columns, ascending=True):
        """
        Sort rows by one or more columns, e.g.
            sort_values("Salary")                    # low -> high
            sort_values(["Dept", "Salary"], ascending=[True, False])
        """
        # .sort_values() reorders the rows; parameters map 1:1.
        self.df = self.df.sort_values(by=columns, ascending=ascending)
        self._log(f"Sorted by {columns} (ascending={ascending}).")
        return self

    def add_rank(self, column, new_column=None, ascending=False):
        """
        Add a RANK column: 1 for the best, 2 for second, ...
        Example: add_rank("Salary", "Salary_Rank") ranks employees by pay.

        ascending=False means the LARGEST value gets rank 1 (typical for
        "top" rankings); ties share the average rank by default.
        """
        # If the user didn't name the new column, invent a sensible one.
        new_column = new_column or f"{column}_Rank"
        # .rank(): converts values to their position in the sorted order.
        self.df[new_column] = self.df[column].rank(ascending=ascending)
        self._log(f"Added rank column '{new_column}' based on '{column}'.")
        return self

    # ================================================================
    # 3. COLUMNS: select / drop / rename / reorder
    # ================================================================
    def select_columns(self, columns):
        """
        Keep ONLY the listed columns, dropping everything else.
        Also useful for REORDERING: the result follows YOUR list's order.
        """
        # df[columns] with a list = "take these columns, in this order".
        self.df = self.df[columns]
        self._log(f"Selected columns {columns}.")
        return self

    def drop_columns(self, columns):
        """
        Delete the listed columns, e.g. drop_columns(["Temp_ID"]).
        Accepts a single name or a list of names.
        """
        # Normalise to a list first, so both "Col" and ["Col"] work.
        cols = [columns] if isinstance(columns, str) else list(columns)
        # axis=1 means "columns" (axis=0 would mean rows).
        self.df = self.df.drop(columns=cols)
        self._log(f"Dropped columns {cols}.")
        return self

    def rename_columns(self, mapping):
        """
        Rename columns via a dictionary, e.g.
            rename_columns({"Emp_ID": "ID", "Dept": "Department"})
        Columns NOT in the dict keep their names.
        """
        self.df = self.df.rename(columns=mapping)
        self._log(f"Renamed columns: {mapping}.")
        return self

    # ================================================================
    # 4. RESHAPING (pivot / melt / transpose)
    # ================================================================
    def melt(self, id_vars, value_vars=None):
        """
        UNPIVOT: turn wide data into long data.

        Wide (hard to plot):   ID | Jan | Feb | Mar
        Long (tidy):            ID | Month | Sales     <- melt produces this

        id_vars   : columns to KEEP as identifiers (e.g. ["ID"])
        value_vars: columns to fold into rows (None = all other columns)
        Two new columns appear: "variable" (old column name) and
        "value" (the cell value).
        """
        self.df = self.df.melt(id_vars=id_vars, value_vars=value_vars)
        self._log(f"Melted with id_vars={id_vars} -> "
                  f"shape now {self.df.shape}.")
        return self

    def pivot(self, index, columns, values, aggfunc="mean"):
        """
        PIVOT: turn long data into a cross-tab (like an Excel pivot table).

        Example: pivot(index="Dept", columns="Year", values="Salary")
        produces one row per department and one column per year.

        aggfunc decides how to combine duplicates: "mean", "sum", "count",
        "min", "max", ...
        """
        # .pivot_table() is the flexible pivot (plain .pivot() crashes if
        # the same index/columns pair appears twice; pivot_table aggregates).
        self.df = self.df.pivot_table(index=index, columns=columns,
                                      values=values, aggfunc=aggfunc)
        # Pivoting nests the columns; reset_index() flattens them back
        # into a normal, easy-to-use DataFrame.
        self.df = self.df.reset_index()
        # After reset_index the column labels can be a MultiIndex; flatten:
        self.df.columns = [str(c) for c in self.df.columns]
        self._log(f"Pivoted: index='{index}', columns='{columns}', "
                  f"values='{values}' (aggfunc='{aggfunc}').")
        return self

    def transpose(self):
        """
        Flip rows and columns (df.T): rows become columns and vice versa.
        Useful for matrix-style data where metrics are stored as rows.
        """
        # .T is the transpose property; .reset_index() keeps it a clean
        # DataFrame instead of leaving odd index labels behind.
        self.df = self.df.T.reset_index()
        self._log("Transposed the DataFrame (rows <-> columns).")
        return self

    # ================================================================
    # 5. COMBINING DATASETS (needs a SECOND DataFrame)
    # ================================================================
    def merge_with(self, other, on, how="inner"):
        """
        SQL-style JOIN of two DataFrames on shared key column(s).

        on : column name(s) present in BOTH tables, e.g. "Employee_ID"
        how: "inner" = only matching keys (default)
             "left"  = keep ALL rows of THIS table
             "right" = keep ALL rows of the OTHER table
             "outer" = keep everything from both (missing -> NaN)
        """
        before = self.df.shape
        self.df = self.df.merge(other, on=on, how=how)
        self._log(f"Merged ({how} join on '{on}'): {before} -> "
                  f"{self.df.shape}.")
        return self

    def concat_with(self, other, axis=0):
        """
        GLUE two DataFrames together.

        axis=0: stack ROWS (more records; columns must roughly match) --
                like appending one CSV under another.
        axis=1: stack COLUMNS side-by-side (more fields; row counts and
                ORDER must match, so use with care).
        """
        before = self.df.shape
        # ignore_index=True gives the result a fresh 0..n row numbering
        # instead of keeping the two original index sequences.
        self.df = pd.concat([self.df, other], axis=axis, ignore_index=True)
        self._log(f"Concatenated (axis={axis}): {before} -> {self.df.shape}.")
        return self

    # ================================================================
    # 6. GROUPBY AGGREGATION
    # ================================================================
    def groupby_aggregate(self, by, target, func="mean"):
        """
        Split-Apply-Combine: group rows, then aggregate each group.

        Example: groupby_aggregate("Department", "Salary", "mean")
                 -> average salary PER department (one row per department).

        by    : column(s) to group by
        target: numeric column to aggregate
        func  : "mean" | "sum" | "count" | "min" | "max" | "std" | "median"
        """
        # Coerce the target to numeric FIRST: raw files constantly store
        # numbers as TEXT ("87,154"), and aggregating text would crash.
        # errors="coerce" turns unparseable values into NaN, which the
        # aggregation then silently skips -- robust by design.
        self.df[target] = pd.to_numeric(self.df[target], errors="coerce")
        # .groupby(by) splits rows into groups; [target] picks the column;
        # .agg(func) applies the aggregation to every group at once.
        grouped = self.df.groupby(by)[target].agg(func)
        # .reset_index() turns the group labels back into a normal column,
        # so the result is a tidy DataFrame instead of a Series.
        self.df = grouped.reset_index()
        # Give the aggregated column a self-explanatory name.
        self.df = self.df.rename(columns={target: f"{target}_{func}"})
        self._log(f"Grouped by '{by}', aggregated '{target}' with "
                  f"'{func}' -> {len(self.df)} group(s).")
        return self

    # ================================================================
    # 7. APPLY / MAP / REPLACE (custom transformations)
    # ================================================================
    def apply_map(self, column, mapping, new_column=None):
        """
        Translate values through a DICTIONARY, e.g.
            apply_map("Dept_Code", {"HR": "Human Resources", "IT": "Tech"})

        Values missing from the dict become NaN (loud signal, not silent).
        Result goes into new_column (default: overwrites the same column).
        """
        new_column = new_column or column
        # .map(dict) looks up EVERY value in the dictionary -- vectorised.
        self.df[new_column] = self.df[column].map(mapping)
        self._log(f"Mapped '{column}' -> '{new_column}' with {mapping}.")
        return self

    def replace_values(self, to_replace, value):
        """
        Global find-and-replace across the WHOLE DataFrame, e.g.
            replace_values("N/A", np.nan)   # standardise a missing marker
            replace_values(-1, np.nan)      # -1 was being used as "unknown"
        """
        # df.replace scans every cell; np.nan is the standard missing marker.
        self.df = self.df.replace(to_replace, value)
        self._log(f"Replaced '{to_replace}' with '{value}' everywhere.")
        return self

    # ================================================================
    # 8. NUMPY-POWERED COLUMN MATH (vectorised -- no Python loops)
    # ================================================================
    def conditional_column(self, new_column, condition_column, op,
                           compare_value, true_value, false_value):
        """
        Build a new column with IF-ELSE logic on every row at once.

        Example: conditional_column("Level", "Salary", ">", 80000,
                                    "Senior", "Junior")
                 -> "Senior" where Salary > 80000, else "Junior".

        op: one of ">", "<", ">=", "<=", "==", "!="
        Implemented with np.where -- the NumPy vectorised if-else.
        """
        # Map the user's string (">") to a REAL function (operator.gt).
        # This avoids eval(), which would be a security hole in a GUI.
        ops = {
            ">": operator.gt, "<": operator.lt,
            ">=": operator.ge, "<=": operator.le,
            "==": operator.eq, "!=": operator.ne,
        }
        # Build the True/False mask for the whole column in one shot...
        mask = ops[op](self.df[condition_column], compare_value)
        # ...then np.where picks true_value / false_value per row.
        self.df[new_column] = np.where(mask, true_value, false_value)
        self._log(f"Created '{new_column}' = np.where({condition_column} "
                  f"{op} {compare_value}, '{true_value}', '{false_value}').")
        return self

    def math_column(self, new_column, col_a, operation, col_b_or_number):
        """
        Arithmetic between two columns (or a column and a number),
        computed for ALL rows simultaneously by NumPy.

        Example: math_column("Total", "Price", "*", "Qty")
                 math_column("Salary_k", "Salary", "/", 1000)

        operation: "+", "-", "*", "/"
        """
        ops = {"+": operator.add, "-": operator.sub,
               "*": operator.mul, "/": operator.truediv}
        # If col_b_or_number is a column name we take that column,
        # otherwise we treat it as a plain number (broadcasting: NumPy
        # automatically applies one number to every row).
        right = (self.df[col_b_or_number]
                 if col_b_or_number in self.df.columns
                 else col_b_or_number)
        self.df[new_column] = ops[operation](self.df[col_a], right)
        self._log(f"Created '{new_column}' = {col_a} {operation} "
                  f"{col_b_or_number}.")
        return self

    def unique_value_counts(self, column):
        """
        NumPy-powered frequency table: every distinct value in the column
        and how many times it appears. Returns a plain dict.
        (Also logged, so it shows up in the GUI console.)
        """
        # .dropna() removes missing values first: NaN has no meaningful
        # "frequency" and would otherwise pollute the counts.
        series = self.df[column].dropna()
        try:
            # np.unique(..., return_counts=True) returns TWO arrays in one
            # pass: the sorted distinct values, and how often each occurs.
            values, counts = np.unique(series.to_numpy(), return_counts=True)
            keys = values.tolist()  # NumPy array -> plain Python list
        except TypeError:
            # Mixed-type columns (e.g. text AND numbers in one column)
            # cannot be SORTED by NumPy, which raises TypeError. Fallback:
            # compare everything as text so the frequency table still works.
            values, counts = np.unique(series.astype(str).to_numpy(),
                                       return_counts=True)
            keys = values.tolist()
        # zip() pairs each distinct value with its count; dict() builds the
        # final {value: count} frequency table.
        result = dict(zip(keys, counts.tolist()))
        self._log(f"Value counts for '{column}': {result}.")
        return result

    # ================================================================
    # 9. ENCODING CATEGORICALS (make text ML-ready)
    # ================================================================
    def one_hot_encode(self, columns):
        """
        ONE-HOT ENCODING: turn each category into its own 0/1 column.
        "Dept" with {HR, IT} -> Dept_HR {1,0,...}, Dept_IT {0,1,...}.
        Machine-learning models need numbers; this is the standard way.
        """
        cols = [columns] if isinstance(columns, str) else list(columns)
        before = self.df.shape[1]
        # pd.get_dummies() builds the 0/1 columns automatically.
        self.df = pd.get_dummies(self.df, columns=cols, dtype=int)
        added = self.df.shape[1] - before
        self._log(f"One-hot encoded {cols}: +{added} new column(s).")
        return self

    def label_encode(self, columns):
        """
        LABEL ENCODING: replace each category with an integer code.
        {HR, IT, Sales} -> {0, 1, 2}. Compact, but implies a false
        ordering -- prefer one-hot unless memory is tight.
        """
        cols = [columns] if isinstance(columns, str) else list(columns)
        for col in cols:
            # pd.factorize returns (codes_array, unique_values); [0] takes
            # just the codes. NaN becomes -1 automatically.
            self.df[col] = pd.factorize(self.df[col])[0]
        self._log(f"Label-encoded {cols} via pd.factorize().")
        return self

    # ================================================================
    # 10. DATETIME FEATURES (pandas .dt accessor)
    # ================================================================
    def extract_date_parts(self, column):
        """
        Split a datetime column into Year / Month / Day / Weekday columns.
        Turns one date into four analysable numeric features.
        The column must already be datetime (use sanitizer.to_datetime
        first if it is still text).
        """
        # .dt gives access to datetime properties of EVERY value at once.
        self.df[f"{column}_Year"] = self.df[column].dt.year
        self.df[f"{column}_Month"] = self.df[column].dt.month
        self.df[f"{column}_Day"] = self.df[column].dt.day
        # weekday: Monday=0 ... Sunday=6 (handy for weekend analysis).
        self.df[f"{column}_Weekday"] = self.df[column].dt.weekday
        self._log(f"Extracted Year/Month/Day/Weekday from '{column}'.")
        return self

    def format_dates(self, column, fmt="%Y-%m-%d"):
        """
        Reformat datetime values as text, e.g. fmt="%d/%m/%Y" turns
        2021-03-15 into "15/03/2021". Common codes: %Y year, %m month,
        %d day, %H hour, %M minute.
        """
        # .dt.strftime applies the format string to the whole column.
        self.df[column] = self.df[column].dt.strftime(fmt)
        self._log(f"Reformatted dates in '{column}' as '{fmt}'.")
        return self
