"""
app.py
======
PURPOSE: the Tkinter DESKTOP user interface of Data Sanitation Studio.

ARCHITECTURE NOTE (very important):
  This file contains ZERO cleaning logic. Every button you see here just:
    1. reads tiny inputs from the widgets (which columns are selected...),
    2. calls ONE method on DataSanitizer / DataWrangler / DataProfiler,
    3. takes the resulting DataFrame back and refreshes the screen.
  All the real work lives in sanitizer.py / wrangler.py / profiler.py.
  That separation is what professionals call "separation of concerns":
  the GUI can be replaced tomorrow (e.g. by a web UI) without touching
  a single line of engine code.

WIDGET GLOSSARY (Tkinter basics used here):
  * Tk       - the main application window (our class inherits from it)
  * Frame    - an invisible box that groups widgets together for layout
  * Label    - static text
  * Button   - clickable button; `command=` says what function to run
  * Entry    - a one-line text input box
  * Listbox  - a scrollable list the user can select from
  * Combobox - a drop-down list (from ttk, the "themed" widget set)
  * Checkbutton - a tick box
  * Notebook - tabbed panels (Inspect | Clean | Wrangle | Visualize)
  * ScrolledText - a multi-line text box with a scrollbar (our log console)
  * PanedWindow - resizable split panes
  * filedialog - the operating system's Open/Save file popups
  * messagebox - small warning/info popups
"""

# tkinter is Python's STANDARD GUI toolkit (comes with Python itself).
import tkinter as tk
# ttk = "themed tk": modern-looking versions of classic widgets.
# filedialog / messagebox / scrolledtext are ready-made dialog helpers.
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Path: locate the bundled sample dataset no matter where the app is run from.
from pathlib import Path

# pandas is only needed here for one tiny job: checking dtypes.
import pandas as pd

# FigureCanvasTkAgg is THE bridge between Matplotlib and Tkinter:
# it turns a Matplotlib Figure into a widget you can pack() into a window.
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Our own engine modules (the . means "from the same src package").
from .loaders import load_file
from .profiler import DataProfiler
from .sanitizer import DataSanitizer
from .wrangler import DataWrangler
from .visualizer import Visualizer
# theme: the minimalistic dark visual identity (palette, fonts, styler).
from . import theme

# File types shown in the Open dialog. Each tuple is (description, pattern).
SUPPORTED_FILETYPES = [
    ("All supported", "*.csv *.xlsx *.xls *.json *.xml"),
    ("CSV files", "*.csv"),
    ("Excel files", "*.xlsx *.xls"),
    ("JSON files", "*.json"),
    ("XML files", "*.xml"),
]

# Path to the sample dataset shipped with the project, resolved relative
# to THIS file: src/app.py -> parent (src) -> parent (project root) / data/...
SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_dirty_data.csv"


class SanitizerApp(tk.Tk):
    """
    The main application window. Inheriting from tk.Tk makes our class
    BE a window: __init__ builds it, mainloop() (called in main.py)
    keeps it alive and responsive.
    """

    # ------------------------------------------------------------------
    # Construction: build the whole window once at startup
    # ------------------------------------------------------------------
    def __init__(self):
        # super().__init__() runs tk.Tk's own constructor -- this actually
        # CREATES the operating-system window. Always call it first.
        super().__init__()

        self.title("RefineDF")            # text in the OS title bar / taskbar
        self.geometry("1180x800")         # initial window size WxH

        # ---------------- Application STATE ----------------
        # self.df          : the WORKING DataFrame (every op updates this)
        # self.df_original : a pristine copy taken at load time, used for
        #                    BEFORE/AFTER chart comparisons
        # self.second_df   : optional second file, used by merge/concat
        self.df = None
        self.df_original = None
        self.second_df = None
        # Combined action history (engine logs are mirrored here too).
        self.action_log = []
        # Keep a reference to the embedded Matplotlib canvas so Python's
        # garbage collector never deletes it while it is on screen.
        self._canvas = None

        # Build the window in sections, top to bottom.
        self._build_glow_header()  # blue gradient aura + title (poster echo)
        self._build_toolbar()    # row of file buttons at the very top
        self._build_main_area()  # columns list | tabbed workspace
        self._build_log_panel()  # console showing every action taken
        self._build_statusbar()  # "Rows: 68 | Cols: 8" line at the bottom

        # Flag the call-to-action buttons BEFORE theming: the theme walk
        # reads these flags to paint blue-gradient pills (styling them here
        # directly would be overwritten by the walk, so the flag is the
        # reliable handoff).
        for btn in (self.btn_open, self.btn_export, self.btn_profile):
            theme.make_primary(btn)

        # Paint the whole window: pill buttons, rounded cards, dark widgets.
        # Must run AFTER every widget exists (it walks the widget tree).
        theme.apply_theme(self)

        self._log("Welcome to RefineDF. "
                  "Open a file (or press 'Load Sample') to begin.")

    # ------------------------------------------------------------------
    # THEME: the blue "glow" header (the poster's aura, as a UI band)
    # ------------------------------------------------------------------
    def _build_glow_header(self):
        """
        A 64px band across the top: a vertical electric-blue -> black
        gradient with the spaced white title on it -- the reference
        poster's blue aura translated into a desktop header.

        A Canvas is used (not a Label) because only a canvas lets us paint
        a per-pixel gradient. It redraws on every <Configure> (resize) so
        the gradient always spans the full window width.
        """
        self.glow = tk.Canvas(self, height=64, bg=theme.PALETTE["bg"],
                              highlightthickness=0, bd=0)
        self.glow.pack(side="top", fill="x")
        self.glow.bind("<Configure>", self._draw_glow)

    def _draw_glow(self, event=None):
        """Paint the gradient + title. Called on every header resize."""
        c = self.glow
        w = c.winfo_width()   # current width in pixels (tracks resizing)
        h = 64                # fixed band height, matches the Canvas
        if w < 10:
            return  # window still opening -- nothing sensible to draw yet
        c.delete("all")  # wipe the previous drawing before repainting
        # One horizontal line per pixel row, lerped blue -> black.
        # The **0.85 easing makes the blue linger near the top, then fall
        # off -- like the poster's glow dissolving into darkness.
        for y in range(h):
            t = (y / (h - 1)) ** 0.85
            c.create_line(0, y, w, y, fill=theme.mix(theme.PALETTE["blue"],
                                                     theme.PALETTE["bg"], t))
        # The title in the poster's wide spaced capitals, vertically
        # centered, in white. (App name: RefineDF.)
        c.create_text(24, h // 2, text="R E F I N E D F",
                      anchor="w", fill="white", font=theme.FONTS["title"])

    def _on_theme_change(self, event=None):
        """
        THEME SWITCHER callback: repaint the live window in the newly
        selected theme -- no restart needed.

        Steps, in order:
          1. theme.set_theme(key) -- swap the palette's CONTENTS in place.
          2. theme.apply_theme(self) -- re-walk the widget tree: every
             widget is recolored and every pill button gets a FRESH
             gradient image baked in the new theme's colors.
          3. self._draw_glow() -- the header gradient is canvas art, not a
             widget, so it needs an explicit repaint.
          4. theme.refresh_cards(self) -- same for the rounded cards.
        (Charts keep their old colors until re-rendered -- they read the
        palette live, so the NEXT chart you draw uses the new theme.)
        """
        # Map the drop-down's display names to theme.py's internal keys.
        key = {"Dark": "dark", "Light": "light",
               "High Contrast": "high_contrast"}[self.theme_choice.get()]
        theme.set_theme(key)        # 1. swap palette contents
        theme.apply_theme(self)     # 2. repaint every widget
        self._draw_glow()           # 3. repaint the header gradient
        theme.refresh_cards(self)   # 4. repaint the rounded cards
        self._log(f"Theme switched to '{self.theme_choice.get()}'.")

    # ------------------------------------------------------------------
    # SECTION 1: the toolbar (file operations)
    # ------------------------------------------------------------------
    def _build_toolbar(self):
        """Create the top strip with Open / Export buttons."""
        # Frame = invisible container; pack(side="top", fill="x") docks it
        # across the top of the window. relief="flat" keeps it minimal --
        # the blue accent strip above already provides the visual edge.
        bar = tk.Frame(self, relief="flat", bd=0)
        bar.pack(side="top", fill="x")

        # Each Button shows `text` and runs `command` (a method) on click.
        # Two key buttons are stored as attributes so __init__ can flag
        # them as primary (blue) BEFORE the theme walk paints everything.
        self.btn_open = tk.Button(bar, text="Open File",
                                  command=self._open_file)
        self.btn_open.pack(side="left", padx=4, pady=4)
        tk.Button(bar, text="Open 2nd File (for merge)",
                  command=self._open_second_file).pack(side="left", padx=4,
                                                       pady=4)
        tk.Button(bar, text="Load Sample",
                  command=self._load_sample).pack(side="left", padx=4, pady=4)
        self.btn_export = tk.Button(bar, text="Export Cleaned",
                                    command=self._export_cleaned)
        self.btn_export.pack(side="left", padx=4, pady=4)
        tk.Button(bar, text="Export Report",
                  command=self._export_report).pack(side="left", padx=4,
                                                    pady=4)

        # ---- Theme switcher (docked right) ----
        # A read-only drop-down listing the three themes. Packing with
        # side="right" AFTER the left-packed buttons docks it at the far
        # right edge of the toolbar. <<ComboboxSelected>> fires whenever
        # the user picks a different theme.
        tk.Label(bar, text="Theme:").pack(side="right", padx=(4, 2))
        self.theme_choice = ttk.Combobox(
            bar, values=["Dark", "Light", "High Contrast"],
            width=13, state="readonly")
        self.theme_choice.set("Dark")  # the default theme at startup
        self.theme_choice.pack(side="right", padx=4)
        self.theme_choice.bind("<<ComboboxSelected>>",
                               self._on_theme_change)

    # ------------------------------------------------------------------
    # SECTION 2: main area -- column list on the left, tabs on the right
    # ------------------------------------------------------------------
    def _build_main_area(self):
        """Left = column picker; right = Notebook with 4 tabs."""
        # PanedWindow lets the USER drag the divider to resize the panes.
        panes = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        panes.pack(side="top", fill="both", expand=True)

        # ---- LEFT pane: the column picker ----
        left = tk.Frame(panes, width=200)
        panes.add(left)  # add() docks the frame into the PanedWindow
        tk.Label(left, text="Columns (click to select)",
                 font=("Arial", 10, "bold")).pack(pady=4)
        # Listbox shows one row per column; EXTENDED = multi-select with
        # Ctrl/Shift; exportselection=False keeps the highlight even when
        # you click somewhere else in the window.
        self.col_listbox = tk.Listbox(left, selectmode=tk.EXTENDED,
                                      exportselection=False)
        self.col_listbox.pack(fill="both", expand=True, padx=4)
        tk.Button(left, text="Refresh Columns",
                  command=self._refresh_columns).pack(pady=4)

        # ---- RIGHT pane: the tabbed workspace ----
        right = tk.Frame(panes)
        panes.add(right)
        # Notebook = the tab bar widget ("Inspect | Clean | Wrangle | ...").
        self.tabs = ttk.Notebook(right)
        self.tabs.pack(fill="both", expand=True)

        # Create one Frame per tab, then fill each with its own widgets.
        self.tab_inspect = tk.Frame(self.tabs)
        self.tab_clean = tk.Frame(self.tabs)
        self.tab_wrangle = tk.Frame(self.tabs)
        self.tab_visual = tk.Frame(self.tabs)
        self.tabs.add(self.tab_inspect, text="Inspect")
        self.tabs.add(self.tab_clean, text="Clean")
        self.tabs.add(self.tab_wrangle, text="Wrangle")
        self.tabs.add(self.tab_visual, text="Visualize")

        self._build_inspect_tab()
        self._build_clean_tab()
        self._build_wrangle_tab()
        self._build_visual_tab()

    # ------------------------------------------------------------------
    # SECTION 3: the log console (bottom)
    # ------------------------------------------------------------------
    def _build_log_panel(self):
        """A read-only scrolling console that narrates every action."""
        frame = tk.Frame(self, height=140)
        # pack_propagate(False) stops the frame shrinking to fit its child;
        # combined with fill="x" it keeps a fixed 140px height strip.
        frame.pack_propagate(False)
        frame.pack(side="bottom", fill="x")
        tk.Label(frame, text="Action Log",
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=4)
        # ScrolledText = Text widget + scrollbar, state="disabled" makes it
        # read-only (we briefly enable it only while writing a line).
        self.log_box = scrolledtext.ScrolledText(frame, height=6,
                                                 state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=4, pady=2)

    # ------------------------------------------------------------------
    # SECTION 4: the status bar (very bottom line)
    # ------------------------------------------------------------------
    def _build_statusbar(self):
        """One-line status: shape of the working DataFrame."""
        # relief="flat": on the dark theme a sunken grey bar would look
        # dated; the hairline is implied by the layout itself (minimalism).
        self.status = tk.Label(self, text="No file loaded",
                               relief="flat", anchor="w")
        self.status.pack(side="bottom", fill="x")

    # ================================================================
    # TAB 1: INSPECT -- profile the data
    # ================================================================
    def _build_inspect_tab(self):
        """One button + one big text area showing the profiler report."""
        # Stored as an attribute so _apply_accents() can make it a primary
        # (blue) button after theming.
        self.btn_profile = tk.Button(self.tab_inspect, text="Run Full Profile",
                                     command=self._run_profile)
        self.btn_profile.pack(pady=8)
        # The report text lives in a ScrolledText so long reports scroll.
        self.inspect_box = scrolledtext.ScrolledText(self.tab_inspect,
                                                     state="disabled")
        self.inspect_box.pack(fill="both", expand=True, padx=8, pady=4)

    def _run_profile(self):
        """Build the health report and display it in the Inspect tab."""
        if not self._need_df():      # guard: nothing loaded -> warn & stop
            return
        report = DataProfiler(self.df).full_report()  # engine does the work
        self._set_text(self.inspect_box, report)      # GUI shows the result
        self._log("Profile generated.")

    # ================================================================
    # TAB 2: CLEAN -- every DataSanitizer operation as buttons
    # ================================================================
    def _build_clean_tab(self):
        """Groups of controls, one group per cleaning family."""
        tab = self.tab_clean  # short alias to keep the code readable

        # ---- group: missing values ----
        g1 = theme.RoundedFrame(tab, title="Missing values")
        g1.pack(fill="x", padx=8, pady=4)
        # Combobox = drop-down; values lists every strategy; the first one
        # is pre-selected with .set() so the button always has a default.
        self.miss_strategy = ttk.Combobox(
            g1, values=["Drop rows", "Fill mean", "Fill median", "Fill mode",
                        "Forward fill", "Backward fill", "Interpolate",
                        "Custom value"], width=16, state="readonly")
        self.miss_strategy.set("Fill median")
        self.miss_strategy.pack(side="left", padx=4)
        # Entry for the "Custom value" strategy (ignored by other strategies).
        self.miss_custom = tk.Entry(g1, width=12)
        self.miss_custom.pack(side="left", padx=4)
        self.miss_custom.insert(0, "0")  # placeholder default text
        tk.Button(g1, text="Apply",
                  command=self._apply_missing).pack(side="left", padx=4)

        # ---- group: duplicates ----
        g2 = theme.RoundedFrame(tab, title="Duplicates")
        g2.pack(fill="x", padx=8, pady=4)
        # IntVar is Tkinter's observable integer; the Checkbutton flips it
        # between 0 (unticked) and 1 (ticked); we read it with .get().
        self.dupe_subset_var = tk.IntVar()
        tk.Checkbutton(g2, text="Only selected columns",
                       variable=self.dupe_subset_var).pack(side="left",
                                                           padx=4)
        tk.Button(g2, text="Remove duplicates",
                  command=self._apply_dedup).pack(side="left", padx=4)

        # ---- group: data types ----
        g3 = theme.RoundedFrame(tab, title="Data types")
        g3.pack(fill="x", padx=8, pady=4)
        tk.Button(g3, text="Auto-convert types",
                  command=lambda: self._run_sanitizer_op(
                      "convert_types")).pack(side="left", padx=4)
        tk.Button(g3, text="To numeric (selected)",
                  command=self._apply_to_numeric).pack(side="left", padx=4)
        tk.Button(g3, text="To datetime (selected)",
                  command=self._apply_to_datetime).pack(side="left", padx=4)

        # ---- group: text ----
        g4 = theme.RoundedFrame(tab, title="Text")
        g4.pack(fill="x", padx=8, pady=4)
        tk.Button(g4, text="Strip whitespace",
                  command=lambda: self._run_sanitizer_op(
                      "strip_whitespace",
                      self._selected_columns())).pack(side="left", padx=4)
        self.case_choice = ttk.Combobox(g4, values=["lower", "upper",
                                                   "title", "capitalize"],
                                        width=10, state="readonly")
        self.case_choice.set("lower")
        self.case_choice.pack(side="left", padx=4)
        tk.Button(g4, text="Change case",
                  command=self._apply_case).pack(side="left", padx=4)

        # ---- group: outliers ----
        g5 = theme.RoundedFrame(tab, title="Outliers (IQR, numeric cols)")
        g5.pack(fill="x", padx=8, pady=4)
        tk.Button(g5, text="Cap outliers",
                  command=lambda: self._run_sanitizer_op(
                      "cap_outliers_iqr",
                      self._numeric_selected())).pack(side="left", padx=4)
        tk.Button(g5, text="Remove outlier rows",
                  command=lambda: self._run_sanitizer_op(
                      "remove_outliers_iqr",
                      self._numeric_selected())).pack(side="left", padx=4)

        # ---- group: validation ----
        g6 = theme.RoundedFrame(tab, title="Validation")
        g6.pack(fill="x", padx=8, pady=4)
        tk.Label(g6, text="Regex:").pack(side="left")
        self.regex_entry = tk.Entry(g6, width=28)
        self.regex_entry.pack(side="left", padx=4)
        # A ready-made email pattern so you can try it in one click.
        self.regex_entry.insert(0, r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")
        tk.Button(g6, text="Check (selected col)",
                  command=self._apply_regex_check).pack(side="left", padx=4)
        tk.Label(g6, text="Range min:").pack(side="left")
        self.range_min = tk.Entry(g6, width=6)
        self.range_min.pack(side="left", padx=2)
        tk.Label(g6, text="max:").pack(side="left")
        self.range_max = tk.Entry(g6, width=6)
        self.range_max.pack(side="left", padx=2)
        tk.Button(g6, text="Clip to range",
                  command=self._apply_clip).pack(side="left", padx=4)

    # ================================================================
    # TAB 3: WRANGLE -- every DataWrangler operation as buttons
    # ================================================================
    def _build_wrangle_tab(self):
        """Groups of controls, one group per wrangling family."""
        tab = self.tab_wrangle

        # ---- group: filter rows ----
        g1 = theme.RoundedFrame(tab, title="Filter rows")
        g1.pack(fill="x", padx=8, pady=4)
        tk.Label(g1, text="Query:").pack(side="left")
        self.query_entry = tk.Entry(g1, width=30)
        self.query_entry.pack(side="left", padx=4)
        self.query_entry.insert(0, "Salary > 50000")  # example to edit
        tk.Button(g1, text="Apply query",
                  command=self._apply_query).pack(side="left", padx=4)
        tk.Label(g1, text="N:").pack(side="left")
        self.topn_entry = tk.Entry(g1, width=5)
        self.topn_entry.pack(side="left", padx=2)
        self.topn_entry.insert(0, "5")
        tk.Button(g1, text="Top N",
                  command=lambda: self._apply_topn(True)).pack(side="left",
                                                                padx=2)
        tk.Button(g1, text="Bottom N",
                  command=lambda: self._apply_topn(False)).pack(side="left",
                                                                 padx=2)

        # ---- group: sort & rank ----
        g2 = theme.RoundedFrame(tab, title="Sort & rank (selected col)")
        g2.pack(fill="x", padx=8, pady=4)
        tk.Button(g2, text="Sort ascending",
                  command=lambda: self._apply_sort(True)).pack(side="left",
                                                               padx=4)
        tk.Button(g2, text="Sort descending",
                  command=lambda: self._apply_sort(False)).pack(side="left",
                                                                padx=4)
        tk.Button(g2, text="Add rank column",
                  command=self._apply_rank).pack(side="left", padx=4)

        # ---- group: columns ----
        g3 = theme.RoundedFrame(tab, title="Columns")
        g3.pack(fill="x", padx=8, pady=4)
        tk.Button(g3, text="Drop selected",
                  command=lambda: self._run_wrangler_op(
                      "drop_columns",
                      self._selected_columns())).pack(side="left", padx=4)
        tk.Label(g3, text="Rename to:").pack(side="left")
        self.rename_entry = tk.Entry(g3, width=14)
        self.rename_entry.pack(side="left", padx=4)
        tk.Button(g3, text="Rename selected",
                  command=self._apply_rename).pack(side="left", padx=4)

        # ---- group: reshape ----
        g4 = theme.RoundedFrame(tab, title="Reshape")
        g4.pack(fill="x", padx=8, pady=4)
        tk.Button(g4, text="Melt (selected = id cols)",
                  command=lambda: self._run_wrangler_op(
                      "melt",
                      self._selected_columns())).pack(side="left", padx=4)
        tk.Label(g4, text="Pivot idx:").pack(side="left")
        self.pivot_idx = tk.Entry(g4, width=10)
        self.pivot_idx.pack(side="left", padx=2)
        tk.Label(g4, text="cols:").pack(side="left")
        self.pivot_cols = tk.Entry(g4, width=10)
        self.pivot_cols.pack(side="left", padx=2)
        tk.Label(g4, text="vals:").pack(side="left")
        self.pivot_vals = tk.Entry(g4, width=10)
        self.pivot_vals.pack(side="left", padx=2)
        tk.Button(g4, text="Pivot",
                  command=self._apply_pivot).pack(side="left", padx=4)

        # ---- group: groupby ----
        g5 = theme.RoundedFrame(tab, title="GroupBy")
        g5.pack(fill="x", padx=8, pady=4)
        tk.Label(g5, text="Target col:").pack(side="left")
        self.groupby_target = tk.Entry(g5, width=12)
        self.groupby_target.pack(side="left", padx=4)
        self.groupby_func = ttk.Combobox(g5, values=["mean", "sum", "count",
                                                     "min", "max", "std",
                                                     "median"],
                                         width=8, state="readonly")
        self.groupby_func.set("mean")
        self.groupby_func.pack(side="left", padx=4)
        tk.Button(g5, text="Aggregate by selected col",
                  command=self._apply_groupby).pack(side="left", padx=4)

        # ---- group: combine (needs 2nd file) ----
        g6 = theme.RoundedFrame(tab, title="Combine (needs 2nd file)")
        g6.pack(fill="x", padx=8, pady=4)
        tk.Label(g6, text="Key:").pack(side="left")
        self.merge_key = tk.Entry(g6, width=12)
        self.merge_key.pack(side="left", padx=4)
        self.merge_how = ttk.Combobox(g6, values=["inner", "left", "right",
                                                  "outer"],
                                      width=8, state="readonly")
        self.merge_how.set("inner")
        self.merge_how.pack(side="left", padx=4)
        tk.Button(g6, text="Merge",
                  command=self._apply_merge).pack(side="left", padx=4)
        tk.Button(g6, text="Concat rows",
                  command=self._apply_concat).pack(side="left", padx=4)

        # ---- group: encode categoricals ----
        g7 = theme.RoundedFrame(tab, title="Encode categoricals (selected)")
        g7.pack(fill="x", padx=8, pady=4)
        tk.Button(g7, text="One-hot encode",
                  command=lambda: self._run_wrangler_op(
                      "one_hot_encode",
                      self._selected_columns())).pack(side="left", padx=4)
        tk.Button(g7, text="Label encode",
                  command=lambda: self._run_wrangler_op(
                      "label_encode",
                      self._selected_columns())).pack(side="left", padx=4)
        tk.Button(g7, text="Extract date parts",
                  command=self._apply_date_parts).pack(side="left", padx=4)

        # ---- group: NumPy column math ----
        g8 = theme.RoundedFrame(tab, title="NumPy: new columns")
        g8.pack(fill="x", padx=8, pady=4)
        tk.Label(g8, text="New col:").pack(side="left")
        self.np_new = tk.Entry(g8, width=10)
        self.np_new.pack(side="left", padx=2)
        tk.Label(g8, text="IF selected").pack(side="left")
        self.np_op = ttk.Combobox(g8, values=[">", "<", ">=", "<=", "==",
                                              "!="],
                                  width=4, state="readonly")
        self.np_op.set(">")
        self.np_op.pack(side="left", padx=2)
        self.np_val = tk.Entry(g8, width=8)
        self.np_val.pack(side="left", padx=2)
        tk.Label(g8, text="THEN").pack(side="left")
        self.np_true = tk.Entry(g8, width=8)
        self.np_true.pack(side="left", padx=2)
        tk.Label(g8, text="ELSE").pack(side="left")
        self.np_false = tk.Entry(g8, width=8)
        self.np_false.pack(side="left", padx=2)
        tk.Button(g8, text="np.where col",
                  command=self._apply_np_where).pack(side="left", padx=4)

    # ================================================================
    # TAB 4: VISUALIZE -- Matplotlib charts embedded in Tkinter
    # ================================================================
    def _build_visual_tab(self):
        """A row of chart buttons + a frame where the chart appears."""
        top = tk.Frame(self.tab_visual)
        top.pack(side="top", fill="x", pady=6)
        tk.Button(top, text="Missing-value chart",
                  command=self._chart_missing).pack(side="left", padx=4)
        tk.Button(top, text="Histogram before/after",
                  command=self._chart_hist).pack(side="left", padx=4)
        tk.Button(top, text="Boxplot before/after",
                  command=self._chart_box).pack(side="left", padx=4)
        tk.Button(top, text="Dtype pie",
                  command=self._chart_dtype).pack(side="left", padx=4)
        tk.Button(top, text="Correlation heatmap",
                  command=self._chart_corr).pack(side="left", padx=4)
        # Short hint: the full explanation lives in the Visualizer docstrings;
        # the label is kept brief so it never clips at small window widths.
        tk.Label(top, text="(before = as loaded, after = current)",
                 font=("Helvetica", 8)).pack(side="left", padx=8)
        # The empty frame that will host the embedded Matplotlib canvas.
        self.chart_frame = tk.Frame(self.tab_visual)
        self.chart_frame.pack(fill="both", expand=True, padx=8, pady=4)

    # ================================================================
    # Small GUI utilities used by many callbacks
    # ================================================================
    def _log(self, message):
        """Write one line to the action console AND the stored history."""
        self.action_log.append(message)          # keep permanent history
        self.log_box.config(state="normal")    # temporarily unlock...
        self.log_box.insert(tk.END, message + "\n")  # ...append the line...
        self.log_box.see(tk.END)               # ...scroll to the bottom...
        self.log_box.config(state="disabled")  # ...and lock it again.

    def _set_text(self, widget, text):
        """Replace ALL text inside a (read-only) ScrolledText widget."""
        widget.config(state="normal")   # unlock
        widget.delete("1.0", tk.END)    # "1.0" = line 1, char 0 (the start)
        widget.insert("1.0", text)      # insert the new content
        widget.config(state="disabled")  # lock again

    def _need_df(self):
        """
        Guard used by every data button: if no file is loaded yet,
        pop a warning and return False so the caller can `return` early.
        """
        if self.df is None:
            messagebox.showwarning("No data",
                                   "Open a file or press 'Load Sample' first.")
            return False
        return True

    def _selected_columns(self):
        """Return the list of column names highlighted in the left listbox."""
        # curselection() -> tuple of selected INDICES, e.g. (0, 3);
        # we map each index back to its column name via .get(i).
        return [self.col_listbox.get(i)
                for i in self.col_listbox.curselection()]

    def _one_selected(self):
        """
        Return the FIRST selected column name, or warn + return None if
        the user selected nothing (many ops need exactly one column).
        """
        cols = self._selected_columns()
        if not cols:
            messagebox.showwarning("No column",
                                   "Select a column in the left panel first.")
            return None
        return cols[0]

    def _numeric_selected(self):
        """
        Selected columns that are numeric; if none selected, ALL numeric
        columns. Used by outlier buttons so they never crash on text.
        """
        cols = self._selected_columns()
        if not cols:  # nothing highlighted -> fall back to every column
            cols = list(self.df.columns)
        # pd.api.types.is_numeric_dtype is pandas' official dtype check.
        return [c for c in cols
                if pd.api.types.is_numeric_dtype(self.df[c])]

    def _refresh_columns(self):
        """Rebuild the left listbox from the CURRENT DataFrame columns."""
        self.col_listbox.delete(0, tk.END)  # clear all existing rows
        if self.df is not None:
            for col in self.df.columns:    # one row per column name
                self.col_listbox.insert(tk.END, col)

    def _refresh_status(self):
        """Update the bottom status bar with the current shape."""
        if self.df is None:
            self.status.config(text="No file loaded")
        else:
            rows, cols = self.df.shape  # unpack the (rows, cols) tuple
            second = (f" | 2nd file: {self.second_df.shape}"
                      if self.second_df is not None else "")
            self.status.config(text=f"Rows: {rows} | Cols: {cols}{second}")

    def _after_engine(self, engine, label):
        """
        Shared "finish line" after ANY engine operation:
          1. take the new DataFrame back from the engine,
          2. mirror the engine's log lines into the GUI console,
          3. refresh the column list + status bar.
        """
        self.df = engine.get_dataframe()   # pull the result back
        for entry in engine.get_log():     # mirror every engine log line
            self._log(f"[{label}] {entry}")
        self._refresh_columns()
        self._refresh_status()

    def _run_sanitizer_op(self, method_name, *args, **kwargs):
        """
        Generic runner for DataSanitizer methods: create the engine around
        the current DataFrame, call the named method, and finish up.
        getattr(engine, "convert_types") fetches the METHOD OBJECT by name,
        then (...) calls it -- this is how one runner serves all buttons.
        """
        if not self._need_df():
            return
        engine = DataSanitizer(self.df)          # wrap current data
        method = getattr(engine, method_name)    # look up the method by name
        result = method(*args, **kwargs)        # CALL it with the arguments
        # Some methods (validate_*) return a NUMBER, not self -- only
        # finish the UI update when we got the engine back (chainable ops).
        if result is engine:
            self._after_engine(engine, "Clean")

    def _run_wrangler_op(self, method_name, *args, **kwargs):
        """Same generic runner, but for DataWrangler methods."""
        if not self._need_df():
            return
        engine = DataWrangler(self.df)
        method = getattr(engine, method_name)
        result = method(*args, **kwargs)
        if result is engine:
            self._after_engine(engine, "Wrangle")

    # ================================================================
    # Toolbar callbacks: open / export files
    # ================================================================
    def _open_file(self):
        """Show the OS Open dialog, load the chosen file via load_file()."""
        path = filedialog.askopenfilename(  # returns "" if user cancels
            title="Open data file", filetypes=SUPPORTED_FILETYPES)
        if not path:  # empty string = user pressed Cancel -> do nothing
            return
        try:
            # load_file() picks the right loader (CSV/Excel/JSON/XML) by
            # extension and returns a DataFrame -- one line, no if/else.
            self.df = load_file(path)
        except Exception as exc:  # noqa: BLE001 - show ANY load error nicely
            # Catch-all is deliberate here: a GUI must never crash with a
            # traceback; it shows a friendly popup instead.
            messagebox.showerror("Load failed", str(exc))
            return
        # Keep a PRISTINE copy for before/after chart comparisons.
        self.df_original = self.df.copy()
        self._refresh_columns()
        self._refresh_status()
        self._log(f"Opened '{Path(path).name}': shape {self.df.shape}.")

    def _open_second_file(self):
        """Load an optional SECOND file, used by merge / concat."""
        path = filedialog.askopenfilename(
            title="Open second data file", filetypes=SUPPORTED_FILETYPES)
        if not path:
            return
        try:
            self.second_df = load_file(path)
        except Exception as exc:  # noqa: BLE001 - friendly popup, no crash
            messagebox.showerror("Load failed", str(exc))
            return
        self._refresh_status()
        self._log(f"Second file '{Path(path).name}': "
                  f"shape {self.second_df.shape}.")

    def _load_sample(self):
        """Load the sample_dirty_data.csv bundled with the project."""
        if not SAMPLE_PATH.exists():  # the file should always be there...
            messagebox.showerror("Missing sample",
                                 f"Sample file not found:\n{SAMPLE_PATH}")
            return
        self.df = load_file(str(SAMPLE_PATH))
        self.df_original = self.df.copy()
        self._refresh_columns()
        self._refresh_status()
        self._log(f"Loaded sample dataset: shape {self.df.shape}.")

    def _export_cleaned(self):
        """Save the CURRENT (cleaned/wrangled) DataFrame to a new file."""
        if not self._need_df():
            return
        path = filedialog.asksaveasfilename(
            title="Export cleaned data",
            defaultextension=".csv",  # added automatically if user omits it
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx"),
                       ("JSON", "*.json")])
        if not path:
            return
        # Pick the writer from the chosen extension -- mirrors loaders.py.
        suffix = Path(path).suffix.lower()
        if suffix == ".xlsx":
            self.df.to_excel(path, index=False)  # index=False: no extra col
        elif suffix == ".json":
            # orient="records": [{"a":1},{"a":2}] -- the readable layout.
            self.df.to_json(path, orient="records", indent=2)
        else:
            self.df.to_csv(path, index=False)
        self._log(f"Exported cleaned data to '{Path(path).name}'.")

    def _export_report(self):
        """Save the profiler report + full action log as a .txt file."""
        if not self._need_df():
            return
        path = filedialog.asksaveasfilename(
            title="Export report", defaultextension=".txt",
            filetypes=[("Text", "*.txt")])
        if not path:
            return
        # Compose the report: current health profile, then everything done.
        report = DataProfiler(self.df).full_report()
        report += "\n\n=== ACTION LOG ===\n" + "\n".join(self.action_log)
        Path(path).write_text(report, encoding="utf-8")
        self._log(f"Exported report to '{Path(path).name}'.")

    # ================================================================
    # Clean-tab callbacks (each reads its widgets, then runs the engine)
    # ================================================================
    def _apply_missing(self):
        """Translate the strategy drop-down into the right engine call."""
        if not self._need_df():
            return
        strategy = self.miss_strategy.get()  # text of the selected option
        cols = self._selected_columns() or None  # None = all columns
        engine = DataSanitizer(self.df)
        # One branch per drop-down option -- each calls the matching method.
        if strategy == "Drop rows":
            engine.drop_missing()
        elif strategy == "Fill mean":
            engine.fill_missing_statistic("mean", cols)
        elif strategy == "Fill median":
            engine.fill_missing_statistic("median", cols)
        elif strategy == "Fill mode":
            engine.fill_missing_statistic("mode", cols)
        elif strategy == "Forward fill":
            engine.fill_missing_ffill(cols)
        elif strategy == "Backward fill":
            engine.fill_missing_bfill(cols)
        elif strategy == "Interpolate":
            engine.interpolate_missing(cols)
        else:  # "Custom value"
            engine.fill_missing_constant(self.miss_custom.get(), cols)
        self._after_engine(engine, "Clean")

    def _apply_dedup(self):
        """Remove duplicates; tick-box decides whole-row vs selected cols."""
        if not self._need_df():
            return
        # If the box is ticked AND columns are selected, dedupe on those;
        # otherwise dedupe on the entire row.
        subset = (self._selected_columns()
                  if self.dupe_subset_var.get() and self._selected_columns()
                  else None)
        self._run_sanitizer_op("drop_duplicates", subset)

    def _apply_to_numeric(self):
        """Convert selected columns (or all) to numeric, coercing errors."""
        if not self._need_df():
            return
        self._run_sanitizer_op("to_numeric",
                               self._selected_columns() or None)

    def _apply_to_datetime(self):
        """Parse selected columns (or all) as datetimes."""
        if not self._need_df():
            return
        self._run_sanitizer_op("to_datetime",
                               self._selected_columns() or None)

    def _apply_case(self):
        """Apply the chosen casing to selected text columns."""
        if not self._need_df():
            return
        self._run_sanitizer_op("change_case",
                               self._selected_columns() or None,
                               self.case_choice.get())

    def _apply_regex_check(self):
        """Count values in the selected column failing the regex."""
        if not self._need_df():
            return
        col = self._one_selected()
        if col is None:
            return
        engine = DataSanitizer(self.df)
        # validate_regex RETURNS a number (not self), so we handle it
        # directly instead of using _run_sanitizer_op.
        invalid = engine.validate_regex(col, self.regex_entry.get())
        self._log(f"[Clean] Regex check on '{col}': "
                  f"{invalid} invalid value(s).")

    def _apply_clip(self):
        """Force the selected numeric column into [min, max]."""
        if not self._need_df():
            return
        col = self._one_selected()
        if col is None:
            return
        try:
            # float() converts the text; ValueError if the user typed junk.
            lo = float(self.range_min.get())
            hi = float(self.range_max.get())
        except ValueError:
            messagebox.showwarning("Bad range",
                                   "Min and max must be numbers.")
            return
        self._run_sanitizer_op("clip_to_range", col, lo, hi)

    # ================================================================
    # Wrangle-tab callbacks
    # ================================================================
    def _apply_query(self):
        """Filter rows with the pandas query typed in the entry box."""
        if not self._need_df():
            return
        try:
            self._run_wrangler_op("filter_query", self.query_entry.get())
        except Exception as exc:  # noqa: BLE001 - bad query syntax -> popup
            messagebox.showwarning("Bad query", str(exc))

    def _apply_topn(self, largest):
        """Keep the N largest/smallest rows of the selected column."""
        if not self._need_df():
            return
        col = self._one_selected()
        if col is None:
            return
        try:
            n = int(self.topn_entry.get())
        except ValueError:
            messagebox.showwarning("Bad N", "N must be a whole number.")
            return
        self._run_wrangler_op("top_n", col, n, largest)

    def _apply_sort(self, ascending):
        """
        Sort by the selected column. The None-guard matters: _one_selected()
        warns and returns None when nothing is highlighted, and passing None
        into sort_values would crash -- so we stop early instead.
        """
        if not self._need_df():
            return
        col = self._one_selected()
        if col is None:  # user selected nothing -> warning already shown
            return
        self._run_wrangler_op("sort_values", col, ascending)

    def _apply_rank(self):
        """Add a rank column for the selected column."""
        if not self._need_df():
            return
        col = self._one_selected()
        if col is None:
            return
        self._run_wrangler_op("add_rank", col)

    def _apply_rename(self):
        """Rename the selected column to the name in the entry box."""
        if not self._need_df():
            return
        col = self._one_selected()
        if col is None:
            return
        new_name = self.rename_entry.get().strip()  # strip() removes spaces
        if not new_name:
            messagebox.showwarning("Empty name",
                                   "Type the new column name first.")
            return
        self._run_wrangler_op("rename_columns", {col: new_name})

    def _apply_pivot(self):
        """Build a pivot table from the three entry boxes."""
        if not self._need_df():
            return
        idx, cols, vals = (self.pivot_idx.get().strip(),
                           self.pivot_cols.get().strip(),
                           self.pivot_vals.get().strip())
        if not (idx and cols and vals):  # all three are required
            messagebox.showwarning("Missing input",
                                   "Fill index, columns AND values.")
            return
        self._run_wrangler_op("pivot", idx, cols, vals)

    def _apply_groupby(self):
        """Aggregate the target column, grouped by the selected column."""
        if not self._need_df():
            return
        by = self._one_selected()
        if by is None:
            return
        target = self.groupby_target.get().strip()
        if not target:
            messagebox.showwarning("Missing input",
                                   "Type the target column name.")
            return
        # Guard against typos: aggregating a column that does not exist
        # would raise KeyError and crash the app -- warn instead.
        if target not in self.df.columns:
            messagebox.showwarning("Unknown column",
                                   f"No column named '{target}'.")
            return
        self._run_wrangler_op("groupby_aggregate", by, target,
                              self.groupby_func.get())

    def _apply_merge(self):
        """Join with the second file on the typed key column."""
        if not self._need_df():
            return
        if self.second_df is None:  # merge NEEDS two tables
            messagebox.showwarning("No second file",
                                   "Open a 2nd file from the toolbar first.")
            return
        key = self.merge_key.get().strip()
        if not key:
            messagebox.showwarning("Missing key",
                                   "Type the join key column name.")
            return
        self._run_wrangler_op("merge_with", self.second_df, key,
                              self.merge_how.get())

    def _apply_concat(self):
        """Stack the second file's rows underneath the current data."""
        if not self._need_df():
            return
        if self.second_df is None:
            messagebox.showwarning("No second file",
                                   "Open a 2nd file from the toolbar first.")
            return
        self._run_wrangler_op("concat_with", self.second_df)

    def _apply_date_parts(self):
        """Split the selected datetime column into Year/Month/Day/Weekday."""
        if not self._need_df():
            return
        col = self._one_selected()
        if col is None:
            return
        self._run_wrangler_op("extract_date_parts", col)

    def _apply_np_where(self):
        """Build an IF/ELSE column with np.where from the entry boxes."""
        if not self._need_df():
            return
        cond_col = self._one_selected()
        if cond_col is None:
            return
        new_col = self.np_new.get().strip()
        if not new_col:
            messagebox.showwarning("Missing name",
                                   "Type the new column's name.")
            return
        # The compare value might be a number or text: try float first,
        # fall back to the raw string (so text comparisons work too).
        raw = self.np_val.get().strip()
        try:
            compare = float(raw)
        except ValueError:
            compare = raw
        self._run_wrangler_op("conditional_column", new_col, cond_col,
                              self.np_op.get(), compare,
                              self.np_true.get(), self.np_false.get())

    # ================================================================
    # Visualize-tab callbacks
    # ================================================================
    def _show_figure(self, fig):
        """
        Embed a Matplotlib Figure into the chart frame.

        Steps: 1) delete any previous chart widgets,
               2) wrap the figure in a FigureCanvasTkAgg (the Tk widget),
               3) draw it and pack it to fill the frame.
        """
        if fig is None:  # engine returned None = "nothing to draw"
            messagebox.showinfo("Nothing to show",
                                "This chart needs data that isn't present "
                                "(e.g. no missing values, or fewer than 2 "
                                "numeric columns).")
            return
        # Destroy old chart widgets so charts never pile on top of each other.
        for child in self.chart_frame.winfo_children():
            child.destroy()
        # The canvas IS a Tkinter widget displaying our figure.
        self._canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self._canvas.draw()  # render the figure into the widget...
        canvas_widget = self._canvas.get_tk_widget()
        # ...then blend the canvas itself into the dark theme (it is created
        # AFTER apply_theme() ran, so the theme walk never saw it -- we
        # style it manually here).
        canvas_widget.configure(bg=theme.PALETTE["bg"],
                                highlightthickness=0, bd=0)
        # ...and pack it to fill the whole frame, expanding with the window.
        canvas_widget.pack(fill="both", expand=True)
        self._log("[Visualize] Chart rendered.")

    def _chart_missing(self):
        """Bar chart of missing values per column (current data)."""
        if not self._need_df():
            return
        self._show_figure(Visualizer.missing_values_bar(self.df))

    def _numeric_one_selected(self):
        """
        The selected column, verified to contain PLOTTABLE numbers.

        NOTE: this deliberately does NOT require a numeric dtype. Raw data
        often stores numbers as TEXT ("87,154"), and the Visualizer already
        coerces safely -- so we only reject columns with NO numeric values
        at all (e.g. pure names), instead of blocking everyday use.
        """
        col = self._one_selected()
        if col is None:
            return None
        # Coerce like the Visualizer does; empty = nothing to plot.
        plottable = pd.to_numeric(self.df[col], errors="coerce").dropna()
        if plottable.empty:
            messagebox.showwarning("Not chartable",
                                   f"'{col}' has no numeric values to plot.")
            return None
        return col

    def _chart_hist(self):
        """Histogram: selected column, as-loaded vs current."""
        if not self._need_df():
            return
        col = self._numeric_one_selected()
        if col is None or col not in self.df_original.columns:
            return
        self._show_figure(Visualizer.histogram_comparison(
            self.df_original[col], self.df[col], col))

    def _chart_box(self):
        """Boxplot: selected column, as-loaded vs current."""
        if not self._need_df():
            return
        col = self._numeric_one_selected()
        if col is None or col not in self.df_original.columns:
            return
        self._show_figure(Visualizer.boxplot_comparison(
            self.df_original[col], self.df[col], col))

    def _chart_dtype(self):
        """Pie chart of column data-type families."""
        if not self._need_df():
            return
        self._show_figure(Visualizer.dtype_breakdown(self.df))

    def _chart_corr(self):
        """Correlation heatmap of numeric columns."""
        if not self._need_df():
            return
        self._show_figure(Visualizer.correlation_heatmap(self.df))
