"""
loaders.py
==========
PURPOSE: read data files of different formats into pandas DataFrames.

DESIGN PATTERN: Strategy + Factory.
  * Strategy: each file format gets its OWN loader class, but all loaders
    share the exact same interface (a load() method). They are interchangeable.
  * Factory: get_loader() looks at the file extension and hands you the right
    loader object. The rest of the program never writes if/else chains for
    file types.

To support a NEW format later you only need to:
  1. Write one small class (see CSVLoader below as a template).
  2. Append it to the _LOADERS list at the bottom.
Nothing else in the program changes. That is the power of this pattern.
"""

# ABC = "Abstract Base Class". It lets us define a *contract* (an interface):
# "every loader MUST have a load() method". Python enforces this for us.
from abc import ABC, abstractmethod

# Path gives us an object-oriented way to work with file paths
# (much safer than slicing strings to find ".csv").
from pathlib import Path

# pandas is the library that represents tabular data as a DataFrame.
import pandas as pd


class DataLoader(ABC):
    """
    Abstract base class -- the "contract" every loader must follow.

    You can NEVER do DataLoader() directly; Python raises TypeError.
    Any child class that forgets to implement load() also cannot be created.
    This guarantees that every loader in the program behaves identically
    from the outside, no matter what format it reads inside.
    """

    # A tuple of file extensions this loader understands, e.g. (".csv",).
    # Each child class OVERRIDES this with its own extensions.
    extensions = ()

    @abstractmethod
    def load(self, path):
        """
        Read the file at `path` and return a pandas DataFrame.

        Declared here but intentionally left EMPTY (just `pass` below):
        every child class provides its own real implementation.
        @abstractmethod is what makes this class impossible to instantiate
        until children fill in this method.
        """
        pass  # children must override this -- see CSVLoader for an example

    @classmethod
    def supports(cls, path):
        """
        Return True if this loader can handle the given file.

        How it works, step by step:
          1. Path(path) turns "data/SALES.CSV" into a Path object.
          2. .suffix grabs just the extension: ".CSV".
          3. .lower() makes it ".csv" so upper/lower case never matters.
          4. `in cls.extensions` checks membership in this class's tuple.

        It is a @classmethod (not a normal method) because we need to ask
        the question WITHOUT creating a loader object first, e.g.:
            CSVLoader.supports("a.csv")  -> True
        """
        suffix = Path(path).suffix.lower()  # normalise the extension
        return suffix in cls.extensions     # True / False


class CSVLoader(DataLoader):
    """Loader for Comma-Separated Values files (.csv)."""

    # This loader claims every file ending in .csv
    extensions = (".csv",)

    def load(self, path):
        # pd.read_csv() is pandas' built-in CSV reader.
        # It parses the header row into column names and returns a DataFrame.
        return pd.read_csv(path)


class ExcelLoader(DataLoader):
    """Loader for Excel workbooks (.xlsx and the older .xls)."""

    # One class can claim MULTIPLE extensions -- just list them all.
    extensions = (".xlsx", ".xls")

    def load(self, path):
        # pd.read_excel() reads the FIRST sheet of the workbook by default.
        # NOTE: .xlsx files need the 'openpyxl' package installed
        # (it is listed in requirements.txt).
        return pd.read_excel(path)


class JSONLoader(DataLoader):
    """Loader for JSON files (.json) stored as a list of record objects."""

    extensions = (".json",)

    def load(self, path):
        # pd.read_json() understands a JSON array like:
        #     [{"Name": "Asha", "Age": 21}, {"Name": "Ravi", "Age": 22}]
        # and turns each object into one DataFrame row.
        return pd.read_json(path)


class XMLLoader(DataLoader):
    """Loader for XML files (.xml) with a simple flat structure."""

    extensions = (".xml",)

    def load(self, path):
        # pd.read_xml() parses XML shaped like:
        #     <data><row><Name>Asha</Name></row>...</data>
        # NOTE: needs the 'lxml' package installed (in requirements.txt).
        return pd.read_xml(path)


# ---------------------------------------------------------------------------
# REGISTRY of every loader class the program knows about.
# get_loader() (below) simply loops over this list, so registering a new
# format is a one-line change: append your class here.
# ---------------------------------------------------------------------------
_LOADERS = [CSVLoader, ExcelLoader, JSONLoader, XMLLoader]


def get_loader(path):
    """
    FACTORY FUNCTION: pick the right loader for a file and return it.

    Example:
        loader = get_loader("sales.xlsx")   # -> an ExcelLoader() object
        df = loader.load("sales.xlsx")      # -> a pandas DataFrame

    Raises:
        ValueError: if no known loader supports this file's extension.
    """
    # Try each registered loader class, one by one...
    for loader_cls in _LOADERS:
        # ...ask it "can you handle this file?" (no object created yet --
        # supports() is a classmethod, remember).
        if loader_cls.supports(path):
            return loader_cls()  # yes -> build the object and hand it back

    # If the loop finishes, NOBODY claimed the file, so we raise a helpful
    # error listing every extension we DO support.
    supported = [ext for cls in _LOADERS for ext in cls.extensions]
    raise ValueError(
        f"Unsupported file type '{Path(path).suffix}'. "
        f"Supported types: {', '.join(supported)}"
    )


def load_file(path):
    """
    Convenience shortcut: choose the loader AND read the file in one call.

    Example:
        df = load_file("employees.csv")

    This is what the GUI calls when you press "Open File".
    """
    loader = get_loader(path)  # step 1: factory picks the right loader
    return loader.load(path)   # step 2: the loader reads the file
