"""
src package
===========
This package holds every building block of the Data Sanitation Studio app.

Modules inside:
    loaders.py     - reading CSV / Excel / JSON / XML files into DataFrames
    profiler.py    - inspecting a DataFrame and producing a health report
    sanitizer.py   - the cleaning engine (fixes bad data)
    wrangler.py    - the manipulation engine (reshapes/transforms data)
    visualizer.py  - Matplotlib charts for the GUI
    app.py         - the Tkinter desktop user interface

The engines (sanitizer / wrangler) never import the GUI, and the GUI never
contains cleaning logic -- this separation is what makes the design "modular".
"""

# Re-export the most useful names so users can do:
#     from src import DataSanitizer
# instead of the longer:
#     from src.sanitizer import DataSanitizer
from .loaders import DataLoader, get_loader, load_file
from .profiler import DataProfiler
from .sanitizer import DataSanitizer
from .wrangler import DataWrangler
from .visualizer import Visualizer

# __all__ tells Python exactly which names "from src import *" should bring in.
__all__ = [
    "DataLoader",
    "get_loader",
    "load_file",
    "DataProfiler",
    "DataSanitizer",
    "DataWrangler",
    "Visualizer",
]
