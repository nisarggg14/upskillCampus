"""
ui/components.py - Reusable UI widgets and theme constants.
"""

import tkinter as tk
from tkinter import ttk


# ------------------------------------------------------------------ #
#  Colour palette  (dark theme)                                        #
# ------------------------------------------------------------------ #

COLORS = {
    "bg":           "#0f1117",   # deepest background
    "surface":      "#1a1d27",   # cards / panels
    "surface2":     "#252836",   # input backgrounds / hover
    "border":       "#2e3149",
    "accent":       "#6c63ff",   # purple accent
    "accent_hover": "#7c74ff",
    "success":      "#22c55e",
    "warning":      "#f59e0b",
    "danger":       "#ef4444",
    "text":         "#e2e8f0",
    "text_muted":   "#7c829a",
    "text_dim":     "#4a5070",
}

FONTS = {
    "title":    ("Segoe UI", 22, "bold"),
    "heading":  ("Segoe UI", 14, "bold"),
    "subhead":  ("Segoe UI", 11, "bold"),
    "body":     ("Segoe UI", 10),
    "small":    ("Segoe UI",  9),
    "mono":     ("Consolas",  10),
}


# ------------------------------------------------------------------ #
#  Style initialiser                                                   #
# ------------------------------------------------------------------ #

def apply_theme(root: tk.Tk | tk.Toplevel) -> None:
    """Apply global ttk styles to *root*."""
    root.configure(bg=COLORS["bg"])

    style = ttk.Style(root)
    style.theme_use("clam")

    # Frame
    style.configure("TFrame",      background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["surface"])

    # Label
    style.configure("TLabel",
                    background=COLORS["bg"],
                    foreground=COLORS["text"],
                    font=FONTS["body"])
    style.configure("Title.TLabel",
                    background=COLORS["bg"],
                    foreground=COLORS["text"],
                    font=FONTS["title"])
    style.configure("Heading.TLabel",
                    background=COLORS["bg"],
                    foreground=COLORS["text"],
                    font=FONTS["heading"])
    style.configure("Muted.TLabel",
                    background=COLORS["bg"],
                    foreground=COLORS["text_muted"],
                    font=FONTS["small"])
    style.configure("Card.TLabel",
                    background=COLORS["surface"],
                    foreground=COLORS["text"],
                    font=FONTS["body"])

    # Entry
    style.configure("TEntry",
                    fieldbackground=COLORS["surface2"],
                    foreground=COLORS["text"],
                    insertcolor=COLORS["text"],
                    bordercolor=COLORS["border"],
                    lightcolor=COLORS["border"],
                    darkcolor=COLORS["border"],
                    font=FONTS["body"])
    style.map("TEntry",
              bordercolor=[("focus", COLORS["accent"])],
              lightcolor=[("focus", COLORS["accent"])],
              darkcolor=[("focus", COLORS["accent"])])

    # Button – primary
    style.configure("Accent.TButton",
                    background=COLORS["accent"],
                    foreground="#ffffff",
                    font=FONTS["subhead"],
                    relief="flat",
                    borderwidth=0,
                    padding=(16, 8))
    style.map("Accent.TButton",
              background=[("active", COLORS["accent_hover"]),
                          ("pressed", COLORS["accent"])])

    # Button – secondary / ghost
    style.configure("Ghost.TButton",
                    background=COLORS["surface2"],
                    foreground=COLORS["text"],
                    font=FONTS["body"],
                    relief="flat",
                    borderwidth=0,
                    padding=(12, 6))
    style.map("Ghost.TButton",
              background=[("active", COLORS["border"])])

    # Button – danger
    style.configure("Danger.TButton",
                    background=COLORS["danger"],
                    foreground="#ffffff",
                    font=FONTS["body"],
                    relief="flat",
                    borderwidth=0,
                    padding=(12, 6))
    style.map("Danger.TButton",
              background=[("active", "#dc2626")])

    # Treeview
    style.configure("Treeview",
                    background=COLORS["surface"],
                    fieldbackground=COLORS["surface"],
                    foreground=COLORS["text"],
                    rowheight=36,
                    font=FONTS["body"],
                    borderwidth=0)
    style.configure("Treeview.Heading",
                    background=COLORS["surface2"],
                    foreground=COLORS["text_muted"],
                    font=FONTS["small"],
                    relief="flat")
    style.map("Treeview",
              background=[("selected", COLORS["accent"])],
              foreground=[("selected", "#ffffff")])

    # Scrollbar
    style.configure("Vertical.TScrollbar",
                    troughcolor=COLORS["surface"],
                    background=COLORS["border"],
                    arrowcolor=COLORS["text_muted"],
                    borderwidth=0)

    # Progressbar (strength meter)
    style.configure("Strength.Horizontal.TProgressbar",
                    troughcolor=COLORS["surface2"],
                    borderwidth=0,
                    thickness=6)


# ------------------------------------------------------------------ #
#  Reusable widgets                                                    #
# ------------------------------------------------------------------ #

class PlaceholderEntry(ttk.Entry):
    """Entry widget with placeholder text (like HTML placeholder=)."""

    def __init__(self, master, placeholder: str = "", show_char: str = "", **kwargs):
        super().__init__(master, **kwargs)
        self._placeholder   = placeholder
        self._show_char     = show_char          # e.g. "•" for passwords
        self._showing_ph    = False
        self._real_show     = show_char

        self.configure(foreground=COLORS["text"])
        self._put_placeholder()

        self.bind("<FocusIn>",  self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _put_placeholder(self) -> None:
        self._showing_ph = True
        self.configure(show="", foreground=COLORS["text_dim"])
        self.delete(0, tk.END)
        self.insert(0, self._placeholder)

    def _on_focus_in(self, _event) -> None:
        if self._showing_ph:
            self._showing_ph = False
            self.delete(0, tk.END)
            self.configure(show=self._real_show, foreground=COLORS["text"])

    def _on_focus_out(self, _event) -> None:
        if not self.get():
            self._put_placeholder()

    def real_get(self) -> str:
        """Return the real value (empty string if placeholder is showing)."""
        return "" if self._showing_ph else self.get()

    def toggle_show(self) -> None:
        """Toggle password masking on/off."""
        if self._showing_ph:
            return
        if self._real_show:
            self._real_show = ""
        else:
            self._real_show = self._show_char
        self.configure(show=self._real_show)


class IconButton(tk.Label):
    """Clickable label styled as a flat icon button."""

    def __init__(self, master, text: str, command=None,
                 fg: str = COLORS["text_muted"],
                 hover_fg: str = COLORS["accent"],
                 font=FONTS["body"], **kwargs):
        super().__init__(master, text=text, fg=fg,
                         font=font, cursor="hand2", **kwargs)
        self._command  = command
        self._fg       = fg
        self._hover_fg = hover_fg

        self.bind("<Enter>",   lambda _: self.configure(fg=self._hover_fg))
        self.bind("<Leave>",   lambda _: self.configure(fg=self._fg))
        if command:
            self.bind("<Button-1>", lambda _: self._command())


class Divider(tk.Frame):
    """Horizontal rule."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=1,
                         bg=COLORS["border"], **kwargs)


class ToastNotification:
    """Temporary overlay message (success / error)."""

    def __init__(self, parent: tk.Widget, message: str, kind: str = "success"):
        color = COLORS["success"] if kind == "success" else COLORS["danger"]
        self._label = tk.Label(
            parent, text=message,
            bg=color, fg="#ffffff",
            font=FONTS["body"],
            padx=16, pady=8,
            relief="flat",
        )
        # Place at the top-right of parent
        self._label.place(relx=1.0, rely=0.0, anchor="ne", x=-12, y=12)
        parent.after(2500, self._dismiss)

    def _dismiss(self) -> None:
        try:
            self._label.destroy()
        except tk.TclError:
            pass
