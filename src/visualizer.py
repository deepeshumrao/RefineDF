"""
visualizer.py
=============
PURPOSE: build Matplotlib charts that the GUI embeds in its Visualize tab.

Every function RETURNS a matplotlib Figure object and never shows it
directly -- the GUI decides where to display it (embedded in Tkinter via
FigureCanvasTkAgg). Returning figures (instead of plotting globally) is
the clean, testable pattern: these functions work headlessly too.

Charts provided:
  * missing_values_bar  - which columns have gaps, and how many
  * histogram_comparison - one column BEFORE vs AFTER cleaning
  * boxplot_comparison   - same, as boxplots (great for outlier work)
  * dtype_breakdown      - pie chart of column data-type families
  * correlation_heatmap  - which numeric columns move together
"""

# Figure: the object that holds a whole chart (axes, titles, labels).
from matplotlib.figure import Figure

# pandas: pd.to_numeric(errors="coerce") safely parses messy text columns
import pandas as pd

# numpy: histogram binning and correlation math
import numpy as np

# theme: the app's dark-minimal palette, so charts match the window.
from .theme import PALETTE, CHART_BLUES


class Visualizer:
    """
    A collection of chart builders. All methods are @staticmethod because
    they need NO stored state -- they just take data in and return a
    Figure out. Call them like: Visualizer.missing_values_bar(df)
    """

    @staticmethod
    def _style_dark(fig):
        """
        Repaint a finished Figure in the app's minimalistic dark theme:
        near-black figure background, slightly lighter axes, white tick
        labels and titles, hairline grey spines.

        It is called at the end of EVERY chart builder below, so no chart
        can accidentally keep Matplotlib's default white background and
        clash with the dark window it is embedded in.
        """
        # The figure's own background = the area OUTSIDE the chart axes.
        fig.patch.set_facecolor(PALETTE["bg"])
        for ax in fig.axes:  # visit every subplot in the figure...
            # ...the axes background = the area INSIDE the chart frame.
            ax.set_facecolor(PALETTE["surface"])
            # Tick labels in white so they stay readable on dark axes.
            ax.tick_params(colors=PALETTE["text"], labelsize=8)
            # Title white, axis labels quiet grey (visual hierarchy:
            # title shouts, labels whisper -- minimalism).
            ax.title.set_color(PALETTE["text"])
            ax.xaxis.label.set_color(PALETTE["muted"])
            ax.yaxis.label.set_color(PALETTE["muted"])
            # The four hairline borders of each chart: barely-visible grey.
            for spine in ax.spines.values():
                spine.set_color(PALETTE["border"])

    @staticmethod
    def missing_values_bar(df):
        """
        Bar chart: number of missing values per column.
        Columns with zero missing are skipped to keep the chart clean.
        """
        # Count gaps per column, keep only columns that HAVE gaps.
        missing = df.isna().sum()
        missing = missing[missing > 0]
        # If NOTHING is missing, there is nothing to draw.
        if missing.empty:
            return None  # the GUI shows "no missing values" instead

        # Create a Figure 8 inches wide x 4 tall, with 100 dots per inch.
        fig = Figure(figsize=(8, 4), dpi=100)
        # add_subplot(1,1,1) = "a grid of 1 row x 1 col, use cell 1"
        # i.e. one single chart filling the figure.
        ax = fig.add_subplot(111)
        # Draw one bar per column in the theme's electric blue.
        ax.bar(missing.index.astype(str), missing.values,
               color=CHART_BLUES[0])
        ax.set_title("Missing values per column")  # chart title
        ax.set_ylabel("Count")                     # y-axis label
        # Rotate x labels 45 degrees so long column names don't overlap.
        ax.tick_params(axis="x", rotation=45)
        # Dark-theme repaint BEFORE tight_layout (order doesn't matter much,
        # but styling first keeps every builder's ending identical).
        Visualizer._style_dark(fig)
        # tight_layout() auto-adjusts padding so nothing is cut off.
        fig.tight_layout()
        return fig

    @staticmethod
    def histogram_comparison(before, after, column_name):
        """
        Two histograms side by side: the column BEFORE cleaning vs AFTER.
        Perfect for showing what outlier capping or imputation changed.
        `before` / `after` are pandas Series of the same column.
        """
        # A figure with TWO charts side by side: add_subplot(1,2,1) and (1,2,2)
        # mean "1 row, 2 columns, cell 1" and "cell 2".
        fig = Figure(figsize=(9, 4), dpi=100)
        ax1 = fig.add_subplot(121)  # left chart
        ax2 = fig.add_subplot(122)  # right chart

        # Drop missing values first: histograms can't bin NaN.
        # pd.to_numeric(errors="coerce") is used INSTEAD of a raw astype(float)
        # because real "before" data often contains text like "87,154":
        # coerce turns unparseable values into NaN instead of crashing.
        b = pd.to_numeric(before, errors="coerce").dropna().to_numpy(dtype=float)
        a = pd.to_numeric(after, errors="coerce").dropna().to_numpy(dtype=float)
        # Use the SAME bin edges for both charts (np.histogram_bin_edges on
        # the combined data) so the two histograms are directly comparable.
        bins = np.histogram_bin_edges(np.concatenate([b, a]), bins=20)

        ax1.hist(b, bins=bins, color=CHART_BLUES[0])  # deep blue = before
        ax1.set_title(f"{column_name} - BEFORE")
        ax1.set_ylabel("Frequency")
        ax2.hist(a, bins=bins, color=CHART_BLUES[2])  # light blue = after
        ax2.set_title(f"{column_name} - AFTER")
        Visualizer._style_dark(fig)  # repaint both subplots dark
        fig.tight_layout()
        return fig

    @staticmethod
    def boxplot_comparison(before, after, column_name):
        """
        Two boxplots side by side: BEFORE vs AFTER.
        Boxplots show median, quartiles and outliers at a glance --
        the ideal visual proof that outlier treatment worked.
        """
        fig = Figure(figsize=(7, 4), dpi=100)
        ax = fig.add_subplot(111)
        # Same safe parsing as in histogram_comparison (see above): coerce
        # messy text to NaN instead of crashing on values like "87,154".
        b = pd.to_numeric(before, errors="coerce").dropna().to_numpy(dtype=float)
        a = pd.to_numeric(after, errors="coerce").dropna().to_numpy(dtype=float)
        # boxplot takes a LIST of datasets; labels names them on the x-axis.
        ax.boxplot([b, a], labels=["BEFORE", "AFTER"])
        ax.set_title(f"{column_name} - boxplot before vs after")
        ax.set_ylabel(column_name)
        Visualizer._style_dark(fig)  # dark repaint (box artists stay visible)
        fig.tight_layout()
        return fig

    @staticmethod
    def dtype_breakdown(df):
        """
        Pie chart of column data-type families: how many columns are
        numeric vs text vs datetime vs other.
        """
        # Map every column's dtype to a FAMILY name.
        families = []
        for col in df.columns:
            dtype = df[col].dtype  # the dtype object of this column
            # kind is a one-letter code: 'i'/'u'/'f' = integer/unsigned/float
            # (all numeric), 'M' = datetime, 'O' = object (usually text).
            kind = dtype.kind
            if kind in "iufc":      # i=int, u=unsigned, f=float, c=complex
                families.append("numeric")
            elif kind == "M":       # M = datetime64
                families.append("datetime")
            elif kind == "b":       # b = boolean
                families.append("boolean")
            else:                   # object / string / category -> text-ish
                families.append("text/categorical")
        # Count how many columns fell into each family.
        unique, counts = np.unique(families, return_counts=True)

        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        # autopct="%1.1f%%" writes the percentage on each slice.
        # colors=CHART_BLUES keeps the pie in the theme's blue family;
        # textprops paints every label white; wedgeprops draws a thin
        # near-black edge between slices so they stay distinct on dark.
        ax.pie(counts, labels=unique, autopct="%1.1f%%", startangle=90,
               colors=CHART_BLUES,
               textprops={"color": PALETTE["text"], "fontsize": 9},
               wedgeprops={"edgecolor": PALETTE["bg"], "linewidth": 2})
        ax.set_title("Column data-type breakdown")
        Visualizer._style_dark(fig)
        fig.tight_layout()
        return fig

    @staticmethod
    def correlation_heatmap(df):
        """
        Correlation matrix of numeric columns, drawn with matshow
        (a pure-Matplotlib heatmap -- no seaborn needed).
        Values near +1 / -1 (dark) mean columns move together / oppositely.
        Returns None when there are fewer than 2 numeric columns.
        """
        # Keep only numeric columns; correlation needs numbers.
        numeric = df.select_dtypes(include="number")
        if numeric.shape[1] < 2:
            return None  # a 1x1 "heatmap" would be meaningless
        # .corr() = Pearson correlation between every pair of columns.
        corr = numeric.corr().to_numpy()
        cols = numeric.columns.astype(str).tolist()

        fig = Figure(figsize=(7, 6), dpi=100)
        ax = fig.add_subplot(111)
        # matshow draws the 2-D array as coloured cells; vmin/vmax fix the
        # colour scale to the correlation range [-1, +1]; cmap="Blues" keeps
        # the heatmap inside the theme's blue family.
        cax = ax.matshow(corr, vmin=-1, vmax=1, cmap="Blues")
        # The colour bar legend on the side explains the colours; its tick
        # labels are painted white to stay readable on the dark figure.
        cb = fig.colorbar(cax)
        cb.ax.tick_params(colors=PALETTE["text"], labelsize=8)
        # Tick labels: name every row/column of the matrix.
        ax.set_xticks(range(len(cols)))
        ax.set_yticks(range(len(cols)))
        ax.set_xticklabels(cols, rotation=45, ha="left")
        ax.set_yticklabels(cols)
        ax.set_title("Correlation heatmap (numeric columns)")
        Visualizer._style_dark(fig)  # dark repaint incl. the colorbar ticks
        fig.tight_layout()
        return fig
