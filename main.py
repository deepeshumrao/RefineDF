"""
main.py
=======
ENTRY POINT of the Data Sanitation Studio application.

Run the whole program with:
    python3 main.py

What happens, line by line:
  1. Import the SanitizerApp class (our Tkinter window) from src/app.py.
  2. Define main(): create ONE app window object...
  3. ...and start its event loop with .mainloop().
     mainloop() is Tkinter's heartbeat: it waits for mouse clicks and
     key presses and calls the right button callbacks, until you close
     the window. Nothing after mainloop() runs until the app quits.
  4. The `if __name__ == "__main__":` guard means main() runs ONLY when
     you execute THIS file directly (python3 main.py). If some other
     file imports main.py, the app does NOT auto-launch -- a standard
     Python best practice.
"""

# Import our application window class from the src package.
from src.app import SanitizerApp


def main():
    """Create the app window and hand control to Tkinter's event loop."""
    app = SanitizerApp()  # build the entire window (see src/app.py)
    app.mainloop()        # start listening for clicks/keys until quit


# Standard Python entry-point guard (explained in the docstring above).
if __name__ == "__main__":
    main()
