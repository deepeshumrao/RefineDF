"""
sanitizer.py
============
PURPOSE: the CLEANING ENGINE -- every method fixes one class of data defect.

DESIGN NOTES (senior-developer practices used here):
  * FLUENT INTERFACE: every cleaning method returns `self`, so calls can be
    CHAINED in one readable line:
        DataSanitizer(df).drop_duplicates().strip_whitespace().cap_outliers_iqr(["Salary"])
  * DEFENSIVE COPY: the engine works on df.copy(), never on the caller's
    original DataFrame, so the raw data is always safe.
  * ACTION LOG: every method appends a human-readable entry to self.log,
    which the GUI shows in its console and saves into the exported report.
    You always know EXACTLY what was done to your data, in order.

NumPy vs pandas in this file:
  * pandas handles the DataFrame-level operations (dropna, fillna, ...).
  * NumPy handles the raw-number crunching (nanmean, percentile, z-scores...)
    via .to_numpy(), which exposes the underlying arrays.
"""

# numpy: fast array math + NaN-aware statistics (nanmean, nanpercentile...)
import numpy as np

# pandas: DataFrame operations + dtype inspection helpers
import pandas as pd


class DataSanitizer:
    """
    Cleaning engine for one DataFrame.

    Usage:
        cleaner = DataSanitizer(df)          # wrap your DataFrame
        cleaner.drop_duplicates()           # one fix...
        cleaner.fill_missing_statistic("median")  # ...another fix (chainable)
        clean_df = cleaner.get_dataframe()  # take the result
        print(cleaner.get_log())            # see everything that was done
    """

    def __init__(self, df):
        # .copy() makes a FULL independent duplicate of the DataFrame.
        # Without this, cleaning would modify the caller's original data too
        # (DataFrames are mutable objects passed by reference).
        self.df = df.copy()
        # The action log: a plain list of strings, one per cleaning step.
        self.log = []

    # ------------------------------------------------------------------
    # Internal helpers (not part of the public API -- hence the _ prefix)
    # ------------------------------------------------------------------
    def _log(self, message):
        """Append one human-readable entry to the action log."""
        self.log.append(message)

    def _resolve(self, columns, numeric_only=False):
        """
        Turn the user's `columns` argument into a clean list of REAL columns.

        Rules:
          * None            -> every column in the DataFrame
          * a single name   -> that one column (as a one-item list)
          * a list of names -> only the names that actually exist
            (typos are silently ignored instead of crashing)
          * numeric_only=True -> keep only columns with a numeric dtype
        """
        # Step 1: normalise the input into a list of EXISTING column names.
        if columns is None:
            # No selection -> work on ALL columns.
            cols = list(self.df.columns)
        elif isinstance(columns, str):
            # A single string like "Salary" -> wrap it in a list.
            cols = [columns] if columns in self.df.columns else []
        else:
            # A list/tuple -> keep only names that really exist.
            cols = [c for c in columns if c in self.df.columns]

        # Step 2 (optional): drop every column that is not numeric.
        if numeric_only:
            # pd.api.types.is_numeric_dtype is pandas' official dtype test.
            cols = [c for c in cols
                    if pd.api.types.is_numeric_dtype(self.df[c])]

        return cols

    def get_dataframe(self):
        """Return the cleaned DataFrame (the current working copy)."""
        return self.df

    def get_log(self):
        """Return the action log as a list of strings, in order."""
        return self.log

    # ================================================================
    # 1. MISSING VALUES
    # ================================================================
    def drop_missing(self, axis=0, how="any", thresh=None, subset=None):
        """
        Delete rows/columns that contain missing values.

        axis   : 0 = drop ROWS, 1 = drop COLUMNS
        how    : "any" = drop if AT LEAST one value missing;
                 "all" = drop only if EVERY value missing
        thresh : keep the row/column only if it has AT LEAST this many
                 non-missing values (overrides `how` when given)
        subset : only look at these columns when deciding (rows only)
        """
        before = len(self.df)  # remember the row count for the log message
        # pandas dropna does the real work; every parameter maps 1:1.
        self.df = self.df.dropna(axis=axis, how=how, thresh=thresh,
                                  subset=subset)
        removed = before - len(self.df)  # how many rows disappeared
        self._log(f"Dropped {removed} row(s) with missing values "
                  f"(axis={axis}, how='{how}').")
        return self  # <- returning self is what makes chaining possible

    def fill_missing_constant(self, value, columns=None):
        """
        Fill every missing cell with ONE fixed value you choose,
        e.g. fill_missing_constant(0) or fill_missing_constant("Unknown").

        columns: which columns to fix (None = all columns).
        """
        cols = self._resolve(columns)  # normalise the column selection
        total = 0  # count every cell we actually fill, for the log
        for col in cols:
            filled = int(self.df[col].isna().sum())  # gaps BEFORE filling
            # .fillna(value) returns a new Series with gaps replaced.
            self.df[col] = self.df[col].fillna(value)
            total += filled
        self._log(f"Filled {total} missing value(s) with constant '{value}' "
                  f"in columns {cols}.")
        return self

    def fill_missing_statistic(self, strategy="mean", columns=None):
        """
        Fill missing NUMERIC values with a statistic of the column itself.

        strategy: "mean" | "median" | "mode"
          * mean   -> good for symmetric data (uses np.nanmean: ignores NaN)
          * median -> ROBUST to outliers/skew (uses np.nanmedian)
          * mode   -> most frequent value; also works on TEXT columns
        """
        cols = self._resolve(columns)  # start from the user's selection
        # Mode works on any dtype, but mean/median need numbers, so:
        if strategy in ("mean", "median"):
            cols = [c for c in cols
                    if pd.api.types.is_numeric_dtype(self.df[c])]
        total = 0
        for col in cols:
            filled = int(self.df[col].isna().sum())
            if strategy == "mean":
                # .to_numpy(dtype=float) exposes the raw NumPy array;
                # np.nanmean computes the mean IGNORING NaN (plain .mean()
                # on the array would return NaN if ANY value is missing).
                value = float(np.nanmean(self.df[col].to_numpy(dtype=float)))
            elif strategy == "median":
                # np.nanmedian: same idea, median ignoring NaN.
                value = float(np.nanmedian(self.df[col].to_numpy(dtype=float)))
            else:  # mode
                # .mode() returns the most frequent value(s); [0] takes the
                # first one. Works for numbers AND text.
                value = self.df[col].mode().iloc[0]
            self.df[col] = self.df[col].fillna(value)
            total += filled
        self._log(f"Filled {total} missing value(s) with '{strategy}' "
                  f"in columns {cols}.")
        return self

    def fill_missing_ffill(self, columns=None):
        """
        FORWARD FILL: copy each missing cell from the value ABOVE it
        (the previous row). Natural for time-series data, e.g. a sensor
        that briefly stopped reporting.
        """
        cols = self._resolve(columns)
        total = sum(int(self.df[c].isna().sum()) for c in cols)
        # .ffill() = "forward fill": propagate last valid value downward.
        self.df[cols] = self.df[cols].ffill()
        self._log(f"Forward-filled {total} missing value(s) in {cols}.")
        return self

    def fill_missing_bfill(self, columns=None):
        """
        BACKWARD FILL: copy each missing cell from the value BELOW it
        (the next row). The mirror image of forward fill.
        """
        cols = self._resolve(columns)
        total = sum(int(self.df[c].isna().sum()) for c in cols)
        # .bfill() = "backward fill": propagate next valid value upward.
        self.df[cols] = self.df[cols].bfill()
        self._log(f"Backward-filled {total} missing value(s) in {cols}.")
        return self

    def interpolate_missing(self, columns=None, method="linear"):
        """
        INTERPOLATION: estimate missing numbers from their NEIGHBOURS,
        e.g. the gap between 10 and 20 becomes 15 with linear interpolation.
        Smoother than forward-fill for gradually changing data.

        method: "linear" (straight line) is the default; pandas also offers
        "nearest", "quadratic", "cubic", ...
        """
        cols = self._resolve(columns, numeric_only=True)  # numbers only
        total = sum(int(self.df[c].isna().sum()) for c in cols)
        # .interpolate() fills NaN by the chosen mathematical method.
        self.df[cols] = self.df[cols].interpolate(method=method)
        self._log(f"Interpolated ({method}) {total} missing value(s) "
                  f"in {cols}.")
        return self

    # ================================================================
    # 2. DUPLICATES
    # ================================================================
    def drop_duplicates(self, subset=None, keep="first"):
        """
        Remove duplicate rows.

        subset: check only these columns (None = the whole row must match)
        keep  : "first" keeps the first occurrence, "last" keeps the last,
                False drops ALL copies including the original
        """
        before = len(self.df)
        # .drop_duplicates() does the work; parameters map 1:1.
        self.df = self.df.drop_duplicates(subset=subset, keep=keep)
        removed = before - len(self.df)
        self._log(f"Removed {removed} duplicate row(s) "
                  f"(subset={subset}, keep='{keep}').")
        return self

    # ================================================================
    # 3. DATA TYPE CONVERSION
    # ================================================================
    def convert_types(self):
        """
        Let pandas GUESS the best dtype for every column
        (convert_dtypes): e.g. a column of whole numbers stored as text
        becomes Int64, true/false text becomes boolean.
        """
        self.df = self.df.convert_dtypes()  # in-place style reassignment
        self._log("Auto-converted column dtypes via convert_dtypes().")
        return self

    def to_numeric(self, columns, errors="coerce"):
        """
        Force text columns to numbers, e.g. "1,200" -> 1200 needs the
        commas stripped first (see wrangler/replace or do it manually).

        errors: "coerce" = turn unparseable text into NaN (safe default);
                "raise"  = crash on the first bad value (strict mode).
        """
        cols = self._resolve(columns)
        for col in cols:
            # pd.to_numeric tries to parse each value; bad ones become NaN.
            self.df[col] = pd.to_numeric(self.df[col], errors=errors)
        self._log(f"Converted {cols} to numeric (errors='{errors}').")
        return self

    def to_datetime(self, columns):
        """
        Parse text columns into real datetime values, e.g.
        "15/03/2021" -> Timestamp('2021-03-15'). Mixed formats in one
        column are handled automatically; garbage becomes NaT
        (Not-a-Time, the datetime version of NaN).
        """
        cols = self._resolve(columns)
        for col in cols:
            # format="mixed" lets pandas infer EACH value's format
            # individually; errors="coerce" turns garbage into NaT.
            self.df[col] = pd.to_datetime(self.df[col], format="mixed",
                                          errors="coerce")
        self._log(f"Parsed {cols} to datetime.")
        return self

    # ================================================================
    # 4. TEXT CLEANING (pandas .str accessor)
    # ================================================================
    def strip_whitespace(self, columns=None):
        """
        Remove leading/trailing spaces: "  hello " -> "hello".
        One of the most common (and most overlooked) data defects.
        Only text columns are touched.
        """
        # Keep only columns whose dtype is text-like ("object" or "string").
        cols = [c for c in self._resolve(columns)
                if self.df[c].dtype == object
                or str(self.df[c].dtype) == "string"]
        for col in cols:
            # .str.strip() applies Python's strip() to every value, fast.
            self.df[col] = self.df[col].str.strip()
        self._log(f"Stripped whitespace in text columns {cols}.")
        return self

    def change_case(self, columns, case="lower"):
        """
        Standardise text casing so "HR", "Hr", "hr" stop being 3 categories.

        case: "lower" | "upper" | "title" (First Letter Capitalised)
              | "capitalize" (Only first letter of the whole string)
        """
        cols = [c for c in self._resolve(columns)
                if self.df[c].dtype == object
                or str(self.df[c].dtype) == "string"]
        for col in cols:
            if case == "lower":
                self.df[col] = self.df[col].str.lower()
            elif case == "upper":
                self.df[col] = self.df[col].str.upper()
            elif case == "title":
                self.df[col] = self.df[col].str.title()
            elif case == "capitalize":
                self.df[col] = self.df[col].str.capitalize()
        self._log(f"Changed case to '{case}' in text columns {cols}.")
        return self

    def replace_text(self, columns, pattern, replacement, regex=True):
        """
        Find-and-replace inside text, e.g. remove all digits from names:
            replace_text(["Name"], r"[0-9]", "", regex=True)

        pattern    : text (or regex) to find
        replacement: text to put in its place
        regex      : True  -> pattern is a regular expression (powerful)
                     False -> pattern is a literal string (safe & simple)
        """
        cols = [c for c in self._resolve(columns)
                if self.df[c].dtype == object
                or str(self.df[c].dtype) == "string"]
        for col in cols:
            # .str.replace is vectorised: it processes the whole column at
            # C speed, far faster than a Python for-loop over rows.
            self.df[col] = self.df[col].str.replace(pattern, replacement,
                                                    regex=regex)
        self._log(f"Replaced '{pattern}' -> '{replacement}' "
                  f"(regex={regex}) in {cols}.")
        return self

    # ================================================================
    # 5. OUTLIERS (NumPy + pandas quantile)
    # ================================================================
    def _iqr_fences(self, column, factor=1.5):
        """
        Helper: compute Tukey's fences for one numeric column.

        Q1 = 25th percentile, Q3 = 75th percentile (via NumPy, NaN-aware).
        IQR = Q3 - Q1 (the spread of the middle 50% of the data).
        Anything below Q1 - factor*IQR or above Q3 + factor*IQR is an outlier.
        factor=1.5 is Tukey's classic choice; 3.0 = only extreme outliers.

        Returns (lower_fence, upper_fence).
        """
        # .to_numpy(dtype=float) -> raw NumPy array of the column.
        values = self.df[column].to_numpy(dtype=float)
        # np.nanpercentile: percentiles that IGNORE NaN values.
        q1 = float(np.nanpercentile(values, 25))
        q3 = float(np.nanpercentile(values, 75))
        iqr = q3 - q1  # inter-quartile range
        lower = q1 - factor * iqr
        upper = q3 + factor * iqr
        return lower, upper

    def detect_outliers_iqr(self, column, factor=1.5):
        """
        COUNT outliers in a column using the IQR method WITHOUT changing
        anything. Returns a dict: {"count": n, "lower": fence, "upper": fence}.
        Use this to INSPECT before deciding to cap or remove.
        """
        lower, upper = self._iqr_fences(column, factor)
        values = self.df[column].to_numpy(dtype=float)
        # A value is an outlier if it is outside EITHER fence.
        # np.isnan(values) is excluded so missing data is never "an outlier".
        mask = ((values < lower) | (values > upper)) & ~np.isnan(values)
        count = int(np.sum(mask))  # np.sum counts the True values
        self._log(f"IQR outlier scan on '{column}': {count} outlier(s) "
                  f"(fences {lower:.2f} to {upper:.2f}).")
        return {"count": count, "lower": lower, "upper": upper}

    def cap_outliers_iqr(self, columns, factor=1.5):
        """
        CAP (winsorize) outliers: pull extreme values IN to the nearest fence
        instead of deleting the rows. The row (and its other valid fields)
        is preserved -- usually preferable to deletion.
        """
        cols = self._resolve(columns, numeric_only=True)
        for col in cols:
            lower, upper = self._iqr_fences(col, factor)
            # .clip(lower, upper): values below lower become lower,
            # values above upper become upper. One clean vectorised call.
            self.df[col] = self.df[col].clip(lower, upper)
        self._log(f"Capped IQR outliers in {cols} (factor={factor}).")
        return self

    def remove_outliers_iqr(self, columns, factor=1.5):
        """
        DELETE every row containing an IQR outlier in the given columns.
        Stronger than capping: use only when you are sure the extreme
        values are errors, not genuine rare events.
        """
        cols = self._resolve(columns, numeric_only=True)
        before = len(self.df)
        for col in cols:
            lower, upper = self._iqr_fences(col, factor)
            values = self.df[col].to_numpy(dtype=float)
            # Keep rows that are INSIDE the fences (or are NaN -- missing
            # data is handled by the missing-value methods, not here).
            keep = ((values >= lower) & (values <= upper)) | np.isnan(values)
            self.df = self.df[keep]  # boolean mask filters the rows
        removed = before - len(self.df)
        self._log(f"Removed {removed} row(s) with IQR outliers in {cols}.")
        return self

    def detect_outliers_zscore(self, column, threshold=3.0):
        """
        COUNT outliers using the Z-SCORE method: how many standard
        deviations is each value from the mean?
            z = (x - mean) / std
        |z| > threshold (default 3.0) -> outlier. Best for roughly
        bell-shaped data; IQR is safer for skewed data.
        Returns {"count": n}.
        """
        values = self.df[column].to_numpy(dtype=float)
        # np.nanmean / np.nanstd: mean & std IGNORING missing values.
        mean = float(np.nanmean(values))
        std = float(np.nanstd(values))
        # The z-score formula, applied to the WHOLE array at once
        # (this is NumPy "vectorisation": no Python loop needed).
        z_scores = (values - mean) / std
        mask = (np.abs(z_scores) > threshold) & ~np.isnan(values)
        count = int(np.sum(mask))
        self._log(f"Z-score outlier scan on '{column}': {count} outlier(s) "
                  f"(threshold={threshold}).")
        return {"count": count}

    # ================================================================
    # 6. VALIDATION (find bad values; optionally fix them)
    # ================================================================
    def validate_regex(self, column, pattern):
        """
        Check a text column against a regular expression; return the
        NUMBER of values that FAIL the check (without changing anything).

        Example -- find invalid emails:
            validate_regex("Email", r"^[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}$")
        """
        # .str.match returns True where the value fits the pattern;
        # na=False treats missing values as "not matching" (they get
        # counted, because a missing email IS a problem to report).
        valid = self.df[column].str.match(pattern, na=False)
        invalid = int((~valid).sum())  # ~ flips True<->False, then count
        self._log(f"Regex validation on '{column}': {invalid} invalid "
                  f"value(s) for pattern '{pattern}'.")
        return invalid

    def validate_range(self, column, min_value, max_value):
        """
        Check a numeric column against an allowed [min, max] range; return
        the NUMBER of values outside it (without changing anything).
        Example: validate_range("Rating", 1, 5)
        """
        values = self.df[column].to_numpy(dtype=float)
        # Outside the range = below min OR above max; NaN is not "invalid".
        mask = ((values < min_value) | (values > max_value)) \
            & ~np.isnan(values)
        invalid = int(np.sum(mask))
        self._log(f"Range validation on '{column}': {invalid} value(s) "
                  f"outside [{min_value}, {max_value}].")
        return invalid

    def clip_to_range(self, column, min_value, max_value):
        """
        FORCE a numeric column into [min_value, max_value] by clipping:
        anything smaller becomes min_value, anything larger becomes max_value.
        The fixing counterpart of validate_range() above.
        """
        cols = self._resolve(column, numeric_only=True)
        for col in cols:
            self.df[col] = self.df[col].clip(min_value, max_value)
        self._log(f"Clipped {cols} to range [{min_value}, {max_value}].")
        return self
