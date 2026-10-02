"""
theme.py
========
PURPOSE: the complete visual identity of Data Sanitation Studio.

The design is a MINIMALISTIC dark theme inspired by the reference poster:
  * near-black backgrounds with generous empty space,
  * electric-blue as the single accent color (the "glow"),
  * SOFT ROUNDED corners everywhere (pill buttons, rounded cards),
  * subtle GRADIENTS (blue glow header, gradient buttons),
  * white / muted-grey typography, nothing else competing for attention.

EVERYTHING visual lives in this ONE module:
  * PALETTE / CHART_BLUES / FONTS - colors and fonts, single source of truth.
  * mix() - blend two colors (used for every gradient).
  * RoundedFrame - a "card" panel with real rounded corners (Tkinter frames
    are always sharp rectangles, so this fakes the rounding -- see its docs).
  * make_primary(button) - flag a button as a blue call-to-action.
  * apply_theme(root) - one call restyling the ENTIRE window after it is built.

NOTE ON "JavaScript and CSS": those are WEB technologies -- a Tkinter
desktop app cannot run them. The rounded corners and gradients here are
built NATIVELY instead: Pillow (PIL) generates the rounded gradient button
images at runtime, and Tkinter Canvases draw the rounded cards and the
glow header. Same visual result, zero web stack needed.
"""

# tkinter core + themed widgets + font measuring (for auto-sizing buttons).
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

# Pillow: generates the rounded-corner gradient images at runtime.
# Image = the picture itself; ImageDraw = drawing on it; ImageTk = showing
# a Pillow image inside tkinter (tkinter can't display Pillow images directly).
from PIL import Image, ImageDraw, ImageTk


# ---------------------------------------------------------------------------
# 1. PALETTES -- three complete themes. Every theme defines the SAME keys,
#    so switching themes never breaks a widget that reads a color.
#
#    Keys: bg/surface/surface2/border = backgrounds, blue/blue_light/
#    blue_deep = the electric-blue accent family, text/muted = typography,
#    ghost_top/ghost_bottom (+hover variants) = the quiet button gradient.
# ---------------------------------------------------------------------------
THEMES = {
    # DARK -- the original poster look: near-black, electric blue glow.
    "dark": {
        "bg": "#07070d",
        "surface": "#0e0e17",
        "surface2": "#16161f",
        "border": "#23232f",
        "blue": "#2b4bff",
        "blue_light": "#5b74ff",
        "blue_deep": "#1a33c4",
        "text": "#f4f4f7",
        "muted": "#8b8b9c",
        "ghost_top": "#1d1d29",
        "ghost_bottom": "#14141d",
        "ghost_hover_top": "#2a2a3a",
        "ghost_hover_bottom": "#1a33c4",
    },
    # LIGHT -- airy daytime mode: paper background, white cards, same blue.
    "light": {
        "bg": "#eef0f6",
        "surface": "#ffffff",
        "surface2": "#e2e6f0",
        "border": "#c9cfe2",
        "blue": "#2b4bff",
        "blue_light": "#5b74ff",
        "blue_deep": "#1a33c4",
        "text": "#14141c",
        "muted": "#5f6579",
        "ghost_top": "#ffffff",
        "ghost_bottom": "#dfe4f0",
        "ghost_hover_top": "#ffffff",
        "ghost_hover_bottom": "#b9c6f5",
    },
    # HIGH CONTRAST -- maximum readability: pure black/white, brighter blue.
    "high_contrast": {
        "bg": "#000000",
        "surface": "#0d0d0d",
        "surface2": "#1f1f1f",
        "border": "#6e6e7e",
        "blue": "#4d6bff",
        "blue_light": "#8095ff",
        "blue_deep": "#2b4bff",
        "text": "#ffffff",
        "muted": "#d0d0dc",
        "ghost_top": "#2e2e2e",
        "ghost_bottom": "#1a1a1a",
        "ghost_hover_top": "#3d3d3d",
        "ghost_hover_bottom": "#2b4bff",
    },
}

# PALETTE is the LIVE palette the whole app reads (theme.PALETTE["bg"]...).
# It starts as a copy of "dark". set_theme() (below) swaps its CONTENTS
# in place -- never rebinds the name -- so every module that imported
# PALETTE (like visualizer.py) automatically sees the new theme.
PALETTE = dict(THEMES["dark"])

# Which theme is currently active ("dark" | "light" | "high_contrast").
CURRENT_THEME = "dark"


def set_theme(name):
    """
    Switch the active theme. The palette dict is mutated IN PLACE
    (clear + update) so existing references stay valid; afterwards call
    apply_theme(root) + refresh_cards(root) to repaint the live window.

    Raises ValueError for unknown theme names (fail loud, not silent).
    """
    global CURRENT_THEME  # we reassign the module-level tracker below
    if name not in THEMES:
        raise ValueError(f"Unknown theme '{name}'. "
                         f"Choose from: {', '.join(THEMES)}")
    PALETTE.clear()            # empty the live dict...
    PALETTE.update(THEMES[name])  # ...and refill it with the new theme
    CURRENT_THEME = name


def refresh_cards(root):
    """
    Redraw every RoundedFrame card in the window. Needed after set_theme()
    because cards paint themselves from PALETTE at draw time -- without a
    nudge they would keep their old colors until the next window resize.
    Recurses the whole widget tree like _style_tree does.
    """
    for child in root.winfo_children():
        if isinstance(child, RoundedFrame):
            child._redraw_card()  # repaint this card with the new palette
        refresh_cards(child)  # ...and keep descending for nested cards

# Chart blues: a small sequential scale so charts feel part of the theme.
CHART_BLUES = ["#2b4bff", "#5b74ff", "#8fa2ff", "#1a33c4", "#0f1f7a"]


# ---------------------------------------------------------------------------
# 2. FONTS -- the only fonts allowed in the app.
# ---------------------------------------------------------------------------
FONTS = {
    "title":   ("Helvetica", 13, "bold"),  # glow-header title, wide capitals
    "heading": ("Helvetica", 10, "bold"),  # section headings
    "body":    ("Helvetica", 9),           # buttons, labels, listboxes
    "small":   ("Helvetica", 8),           # card titles, helper labels
    "mono":    ("Courier", 9),              # log console & report text
}


# ---------------------------------------------------------------------------
# 3. COLOR MATH -- the foundation of every gradient in the app.
# ---------------------------------------------------------------------------
def _hex_to_rgb(hex_color):
    """Turn "#2b4bff" into the tuple (43, 75, 255) for arithmetic."""
    hex_color = hex_color.lstrip("#")  # strip the leading '#'
    # Slice the 6 hex digits into 3 pairs, convert each pair base-16 -> int.
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    """Turn (43, 75, 255) back into "#2b4bff" for tkinter."""
    # %02x = format as 2-digit lowercase hex, zero-padded.
    return "#%02x%02x%02x" % rgb


def mix(color_a, color_b, t):
    """
    Blend two colors. t=0.0 -> pure color_a, t=1.0 -> pure color_b,
    t=0.5 -> exactly halfway. Every gradient in the app is just this
    function sampled across pixels/rows.
    """
    ra, ga, ba = _hex_to_rgb(color_a)  # unpack color A into r, g, b
    rb, gb, bb = _hex_to_rgb(color_b)  # unpack color B into r, g, b
    # Linear interpolation per channel, rounded back to whole numbers.
    mixed = (round(ra + (rb - ra) * t),
             round(ga + (gb - ga) * t),
             round(ba + (bb - ba) * t))
    return _rgb_to_hex(mixed)


# ---------------------------------------------------------------------------
# 4. ROUNDED GRADIENT IMAGES -- pill buttons, generated by Pillow.
# ---------------------------------------------------------------------------
# Every PhotoImage tkinter displays MUST stay referenced somewhere in
# Python, or the garbage collector deletes it and the widget goes blank.
# This module-level list is that safe-keeping place (widgets ALSO keep
# their own references -- belt and suspenders).
_photo_cache = []


def _rounded_gradient_photo(width, height, radius,
                            top_color, bottom_color, parent_bg):
    """
    Build one rounded-corner vertical-gradient image for a button.

    width/height : exact pixel size of the button face.
    radius       : corner roundness (height//2 gives a full "pill").
    top_color -> bottom_color : the vertical gradient.
    parent_bg    : the color BEHIND the button; the rounded corners are
                   painted in this color so they blend invisibly into
                   whatever surface the button sits on.

    Returns a tkinter PhotoImage, already cached against garbage collection.
    """
    # Layer 1: a solid parent_bg rectangle (this shows through the
    # transparent rounded corners, making them "disappear").
    base = Image.new("RGB", (width, height), parent_bg)

    # Layer 2: the vertical gradient, one lerped color per pixel row.
    gradient = Image.new("RGB", (width, height))
    grad_draw = ImageDraw.Draw(gradient)
    for y in range(height):
        # t goes 0.0 (top row) -> 1.0 (bottom row).
        t = y / max(height - 1, 1)  # max() avoids divide-by-zero at height 1
        grad_draw.line([(0, y), (width, y)], fill=mix(top_color, bottom_color, t))

    # Layer 3: the rounded-rectangle MASK (white = visible, black = cut).
    # Pillow HAS a rounded_rectangle primitive (unlike tkinter's Canvas).
    mask = Image.new("L", (width, height), 0)  # "L" = 8-bit greyscale
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, width - 1, height - 1],
                                radius=radius, fill=255)

    # Paste the gradient onto the base THROUGH the mask: only the rounded
    # area survives; the corners keep the parent_bg from layer 1.
    base.paste(gradient, (0, 0), mask)

    # ImageTk.PhotoImage converts Pillow -> something tkinter can display.
    photo = ImageTk.PhotoImage(base)
    _photo_cache.append(photo)  # keep it alive forever
    return photo


def _pill_images_for(widget, primary):
    """
    Generate the (normal, hover) pill images for ONE button, auto-sized to
    its text. Returns (normal_photo, hover_photo, text_color, parent_bg).
    """
    text = widget.cget("text") or ""  # the button's label text
    # Measure the text with the real font so the pill hugs it perfectly.
    fnt = tkfont.Font(family="Helvetica", size=9)  # = FONTS["body"]
    pad_x, pad_y = 16, 8  # breathing room around the text
    width = fnt.measure(text) + pad_x * 2
    # linespace = the pixel height of one line in this font.
    height = fnt.metrics("linespace") + pad_y * 2
    radius = height // 2  # full pill: ends are perfect semicircles

    # The surface behind the button -- rounded corners are painted in this
    # color. Cards use "surface", everywhere else the window "bg".
    master = widget.master
    if isinstance(master, RoundedFrame):
        parent_bg = PALETTE["surface"]
    else:
        try:
            parent_bg = master.cget("bg")  # classic tk widgets have bg
        except tk.TclError:
            parent_bg = PALETTE["bg"]      # ttk widgets don't -- fallback

    if primary:
        # Call-to-action: electric-blue gradient, white text.
        normal = _rounded_gradient_photo(width, height, radius,
                                         PALETTE["blue_light"],
                                         PALETTE["blue"], parent_bg)
        hover = _rounded_gradient_photo(width, height, radius,
                                        "#6d84ff", PALETTE["blue_light"],
                                        parent_bg)
        fg = "white"
    else:
        # Quiet ghost pill: theme-colored gradient; hover glows blue-ish.
        # (Colors come from the palette so ghost buttons adapt to every
        # theme -- dark, light and high-contrast alike.)
        normal = _rounded_gradient_photo(width, height, radius,
                                         PALETTE["ghost_top"],
                                         PALETTE["ghost_bottom"], parent_bg)
        hover = _rounded_gradient_photo(width, height, radius,
                                        PALETTE["ghost_hover_top"],
                                        PALETTE["ghost_hover_bottom"],
                                        parent_bg)
        fg = PALETTE["text"]
    return normal, hover, fg, parent_bg


# ---------------------------------------------------------------------------
# 5. RoundedFrame -- group "cards" with genuinely rounded corners.
# ---------------------------------------------------------------------------
class RoundedFrame(tk.Frame):
    """
    A card panel with SOFT ROUNDED corners and a hairline border.

    THE TRICK (because tkinter Frames are always sharp rectangles):
      * The Frame itself stays ordinary and rectangular -- so children
        pack() into it EXACTLY like they did with LabelFrame. Zero
        changes needed at call sites beyond the class name.
      * A Canvas is place()d to fill the frame BEHIND the children.
      * On every resize (<Configure> event), we redraw on that canvas:
        layer 1 = a border-colored rounded rect (the hairline outline),
        layer 2 = a surface-colored rounded rect inset 1px (the card face).
        The canvas background matches the window, so the rounded corners
        melt invisibly into the page.
      * The group title is a real Label packed at the top -- simple,
        themeable, and it can never overlap the buttons below it.

    Usage (drop-in replacement for LabelFrame):
        card = RoundedFrame(tab, title="Missing values")
        card.pack(fill="x", padx=8, pady=4)
        tk.Button(card, text="Apply", ...).pack(side="left")
    """

    def __init__(self, master, title="", radius=16, **kw):
        # The outer frame itself blends into the window (the canvas paints
        # the visible card on top of it).
        kw["bg"] = PALETTE["bg"]
        super().__init__(master, **kw)
        self._radius = radius
        # The background canvas: place() layers it UNDER later-packed
        # children (place + pack can mix: place is just the painter here).
        self._canvas = tk.Canvas(self, bg=PALETTE["bg"],
                                 highlightthickness=0, bd=0)
        self._canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        # Title: quiet grey, small -- the poster's restrained typography.
        # theme_keep_font = custom flag: the theme walk normally resets
        # every Label to the body font, but this one keeps its small size.
        self._title_label = tk.Label(self, text=title, bg=PALETTE["surface"],
                                     fg=PALETTE["muted"], font=FONTS["small"],
                                     anchor="w")
        self._title_label.theme_keep_font = True
        # padx=16 keeps the title clear of the rounded edge; pady=(10,2)
        # gives it air above and a small gap before the buttons.
        self._title_label.pack(side="top", anchor="w", padx=16, pady=(10, 2))
        # Redraw the rounded card every time the card changes size.
        self.bind("<Configure>", self._redraw_card)

    def _redraw_card(self, event=None):
        """Repaint the two rounded-rectangle layers at the current size."""
        w, h, r = (self.winfo_width(), self.winfo_height(), self._radius)
        if w < 10 or h < 10:
            return  # window still opening -- nothing sensible to draw yet
        c = self._canvas
        c.delete("all")  # wipe the previous drawing before repainting
        # Layer 1: border color, full-bleed -> becomes the 1px hairline.
        _canvas_rounded_rect(c, 0, 0, w, h, r, PALETTE["border"])
        # Layer 2: surface color, inset 1px -> the card face itself.
        _canvas_rounded_rect(c, 1, 1, w - 1, h - 1, max(r - 1, 1),
                             PALETTE["surface"])


def _canvas_rounded_rect(canvas, x0, y0, x1, y1, radius, fill):
    """
    Draw ONE filled rounded rectangle on a tkinter Canvas.

    tkinter's Canvas has NO rounded-rectangle primitive, so we compose one
    from pieces it DOES have: four circles (the corners) + two rectangles
    (the straight bands between them). Together they form a perfect
    rounded rectangle.
    """
    # Clamp: the radius can never exceed half the width/height, or the
    # corner circles would overlap and the geometry breaks.
    radius = min(radius, (x1 - x0) / 2, (y1 - y0) / 2)
    # Four corner circles, centered radius-away from each corner.
    for cx, cy in ((x0 + radius, y0 + radius),   # top-left
                   (x1 - radius, y0 + radius),   # top-right
                   (x0 + radius, y1 - radius),   # bottom-left
                   (x1 - radius, y1 - radius)):  # bottom-right
        # outline="" is vital: the default outline is black and would draw
        # dark rings around every corner.
        canvas.create_oval(cx - radius, cy - radius,
                           cx + radius, cy + radius,
                           fill=fill, outline="")
    # The straight bands connecting the corners (horizontal + vertical).
    canvas.create_rectangle(x0 + radius, y0, x1 - radius, y1,
                            fill=fill, outline="")
    canvas.create_rectangle(x0, y0 + radius, x1, y1 - radius,
                            fill=fill, outline="")


# ---------------------------------------------------------------------------
# 6. TTK STYLING -- for the "themed" widgets (unchanged from before:
#    Comboboxes, Notebook tabs, Checkbuttons have no rounded-image
#    equivalent, so they keep the flat dark treatment).
# ---------------------------------------------------------------------------
def _configure_ttk_style(root):
    """
    Paint every ttk widget class dark, based on the flexible "clam" theme.
    (ttk widgets ignore bg=/fg= options -- only this Style object paints them.)
    """
    style = ttk.Style(root)
    style.theme_use("clam")

    # "." = root style: defaults inherited by every ttk widget.
    style.configure(".", background=PALETTE["bg"],
                    foreground=PALETTE["text"], font=FONTS["body"])
    style.configure("TFrame", background=PALETTE["bg"])

    # Notebook tabs: quiet grey, selected tab = lighter surface + white.
    style.configure("TNotebook", background=PALETTE["bg"], borderwidth=0)
    style.configure("TNotebook.Tab", background=PALETTE["bg"],
                    foreground=PALETTE["muted"], padding=(18, 10),
                    borderwidth=0, font=FONTS["body"])
    style.map("TNotebook.Tab",
              background=[("selected", PALETTE["surface"])],
              foreground=[("selected", PALETTE["text"])])

    # Combobox drop-downs.
    style.configure("TCombobox", fieldbackground=PALETTE["surface2"],
                    background=PALETTE["surface2"],
                    foreground=PALETTE["text"],
                    arrowcolor=PALETTE["muted"], borderwidth=0,
                    font=FONTS["body"])
    # READONLY quirk (classic ttk gotcha): a readonly Combobox paints its
    # visible text with the SELECTION colors, ignoring `foreground` above.
    # Without this map, the text turns white-on-white (invisible) on the
    # light theme. So we pin the readonly states to the palette explicitly.
    style.map("TCombobox",
              foreground=[("readonly", PALETTE["text"])],
              fieldbackground=[("readonly", PALETTE["surface2"])],
              selectforeground=[("readonly", PALETTE["text"])],
              selectbackground=[("readonly", PALETTE["surface2"])])
    # The popup list is a Listbox behind the scenes -- recolor it too.
    root.option_add("*TCombobox*Listbox.background", PALETTE["surface2"])
    root.option_add("*TCombobox*Listbox.foreground", PALETTE["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", PALETTE["blue"])
    root.option_add("*TCombobox*Listbox.selectForeground", "white")

    # Tick boxes.
    style.configure("TCheckbutton", background=PALETTE["bg"],
                    foreground=PALETTE["text"], font=FONTS["body"])
    style.map("TCheckbutton", background=[("active", PALETTE["bg"])])


# ---------------------------------------------------------------------------
# 7. CLASSIC TK STYLING -- walk the widget tree and repaint by class.
# ---------------------------------------------------------------------------
def _style_one_widget(widget):
    """
    Restyle ONE classic-tk widget according to its class.
    (ttk widgets were handled by _configure_ttk_style above.)
    """
    cls = widget.winfo_class()  # e.g. "Frame", "Button", "Entry", ...

    if cls == "Frame":
        # Plain containers melt into the window background.
        # (RoundedFrame IS a Frame subclass -- isinstance check first so
        # its card styling is never clobbered by this generic rule.)
        if not isinstance(widget, RoundedFrame):
            widget.configure(bg=PALETTE["bg"])

    elif cls == "Label":
        # Label background follows its parent: cards -> surface (so the
        # label sits ON the card), everywhere else -> the window bg.
        # try/except: ttk parents have no "bg" option (they use "background").
        try:
            parent_bg = (PALETTE["surface"]
                         if isinstance(widget.master, RoundedFrame)
                         else widget.master.cget("bg"))
        except tk.TclError:
            parent_bg = PALETTE["bg"]
        widget.configure(bg=parent_bg, fg=PALETTE["text"])
        # Labels that opted out (card titles) keep their custom small font;
        # everyone else gets the standard body font.
        if not getattr(widget, "theme_keep_font", False):
            widget.configure(font=FONTS["body"])

    elif cls == "Button":
        # THE pill buttons: auto-sized rounded gradient images, with a
        # brighter hover variant. theme_primary flag -> blue, else ghost.
        primary = getattr(widget, "theme_primary", False)
        normal, hover, fg, parent_bg = _pill_images_for(widget, primary)
        # Keep our own references too (the module cache also holds them).
        widget._theme_images = (normal, hover)
        widget.configure(image=normal, compound="center", fg=fg,
                         bg=parent_bg, activebackground=parent_bg,
                         relief="flat", bd=0, padx=0, pady=0,
                         highlightthickness=0, font=FONTS["body"],
                         cursor="hand2")  # pointing hand on hover
        # Swap normal <-> hover images on mouse enter/leave.
        # The default args (w=widget, img=...) freeze the CURRENT values
        # into each closure -- without them, every button would control
        # the LAST button (the classic late-binding gotcha).
        widget.bind("<Enter>",
                    lambda e, w=widget, img=hover: w.configure(image=img))
        widget.bind("<Leave>",
                    lambda e, w=widget, img=normal: w.configure(image=img))

    elif cls == "Entry":
        widget.configure(bg=PALETTE["surface2"], fg=PALETTE["text"],
                         insertbackground=PALETTE["text"],
                         relief="flat", bd=0,
                         highlightthickness=1,
                         highlightbackground=PALETTE["border"],
                         highlightcolor=PALETTE["blue"],
                         font=FONTS["body"])

    elif cls == "Listbox":
        widget.configure(bg=PALETTE["surface"], fg=PALETTE["text"],
                         selectbackground=PALETTE["blue"],
                         selectforeground="white", relief="flat", bd=0,
                         highlightthickness=1,
                         highlightbackground=PALETTE["border"],
                         highlightcolor=PALETTE["blue"],
                         font=FONTS["body"])

    elif cls == "Text":
        widget.configure(bg=PALETTE["surface"], fg=PALETTE["text"],
                         insertbackground=PALETTE["text"],
                         selectbackground=PALETTE["blue"],
                         selectforeground="white", relief="flat", bd=0,
                         highlightthickness=1,
                         highlightbackground=PALETTE["border"],
                         highlightcolor=PALETTE["blue"],
                         font=FONTS["mono"])

    elif cls == "Canvas":
        # Plain canvases (e.g. the glow header) blend into the window.
        # (RoundedFrame's own canvas is drawn by RoundedFrame itself and
        # is already correct -- repainting its bg is harmless.)
        widget.configure(bg=PALETTE["bg"], highlightthickness=0, bd=0)

    elif cls == "PanedWindow":
        widget.configure(bg=PALETTE["bg"])
    # Anything else (Scrollbar, Menu, ...) keeps its native look.


def _style_tree(widget):
    """
    Recursively visit EVERY widget inside `widget` and style each one.
    winfo_children() returns only DIRECT children, so we recurse to
    descend the whole tree.
    """
    for child in widget.winfo_children():
        _style_one_widget(child)  # style this widget...
        _style_tree(child)        # ...then descend into ITS children.


# ---------------------------------------------------------------------------
# 8. PUBLIC API -- what app.py actually calls.
# ---------------------------------------------------------------------------
def make_primary(button):
    """
    Flag ONE button as a call-to-action (blue gradient pill).

    This only SETS a flag -- the actual painting happens inside
    apply_theme()'s widget walk, which runs once after the whole window
    is built. Styling earlier would be overwritten by that walk, so the
    flag is the reliable handoff.
    """
    button.theme_primary = True  # plain Python attribute on the widget


def apply_theme(root):
    """
    THE one call that themes the entire application. Call once, after the
    whole window is built (end of __init__):
        theme.apply_theme(self)

    1. paints the root window near-black,
    2. configures the ttk Style engine (themed widgets),
    3. walks and repaints every classic tk widget (pill buttons, cards...).
    """
    root.configure(bg=PALETTE["bg"])
    _configure_ttk_style(root)
    _style_tree(root)
