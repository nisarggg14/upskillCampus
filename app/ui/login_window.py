"""
ui/login_window.py - Login and Registration windows.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from app.core import auth
from app.database import database as db
from app.utils.encryption import EncryptionManager
from app.ui.components import (
    COLORS, FONTS, apply_theme,
    PlaceholderEntry, IconButton, Divider, ToastNotification,
)


# ------------------------------------------------------------------ #
#  Login / Register window                                             #
# ------------------------------------------------------------------ #

class LoginWindow:
    """
    Dual-mode window: shows Login or Register panel
    depending on user's choice.
    """

    def __init__(self, on_login_success):
        """
        on_login_success(session) is called after a successful login
        so the main application can open the dashboard.
        """
        self._on_success = on_login_success

        self.root = tk.Tk()
        self.root.title("PassVault – Secure Password Manager")
        self.root.geometry("460x600")
        self.root.resizable(False, False)
        apply_theme(self.root)

        db.init_db()
        self._build_ui()

    # ---------------------------------------------------------------- #
    #  UI construction                                                   #
    # ---------------------------------------------------------------- #

    def _build_ui(self) -> None:
        root = self.root
        bg = COLORS["bg"]

        # ── Top decoration bar ──────────────────────────────────────
        accent_bar = tk.Frame(root, bg=COLORS["accent"], height=4)
        accent_bar.pack(fill="x")

        # ── Outer padding container ──────────────────────────────────
        container = tk.Frame(root, bg=bg)
        container.pack(fill="both", expand=True, padx=40, pady=30)

        # ── Logo / title ─────────────────────────────────────────────
        tk.Label(container, text="🔐", bg=bg, fg=COLORS["accent"],
                 font=("Segoe UI Emoji", 36)).pack(pady=(10, 4))

        tk.Label(container, text="PassVault",
                 bg=bg, fg=COLORS["text"],
                 font=("Segoe UI", 26, "bold")).pack()

        tk.Label(container, text="Your credentials, encrypted & safe.",
                 bg=bg, fg=COLORS["text_muted"],
                 font=FONTS["small"]).pack(pady=(2, 24))

        # ── Tab switcher ──────────────────────────────────────────────
        tab_frame = tk.Frame(container, bg=COLORS["surface"], bd=0)
        tab_frame.pack(fill="x", ipady=4)

        self._mode = tk.StringVar(value="login")

        self._tab_login = tk.Label(tab_frame, text="Login",
                                   bg=COLORS["accent"], fg="#ffffff",
                                   font=FONTS["subhead"],
                                   padx=24, pady=8, cursor="hand2")
        self._tab_login.pack(side="left", fill="x", expand=True)

        self._tab_reg = tk.Label(tab_frame, text="Register",
                                 bg=COLORS["surface"], fg=COLORS["text_muted"],
                                 font=FONTS["subhead"],
                                 padx=24, pady=8, cursor="hand2")
        self._tab_reg.pack(side="left", fill="x", expand=True)

        self._tab_login.bind("<Button-1>", lambda _: self._switch_mode("login"))
        self._tab_reg.bind("<Button-1>",   lambda _: self._switch_mode("register"))

        Divider(container).pack(fill="x", pady=(16, 0))

        # ── Form area ─────────────────────────────────────────────────
        self._form = tk.Frame(container, bg=bg)
        self._form.pack(fill="x", pady=16)

        self._build_login_form()

        # ── Submit button ─────────────────────────────────────────────
        self._submit_btn = ttk.Button(container, text="Login",
                                      style="Accent.TButton",
                                      command=self._on_submit)
        self._submit_btn.pack(fill="x", ipady=4)

        # ── Error label ───────────────────────────────────────────────
        self._error_var = tk.StringVar()
        self._error_lbl = tk.Label(container,
                                   textvariable=self._error_var,
                                   bg=bg, fg=COLORS["danger"],
                                   font=FONTS["small"],
                                   wraplength=360)
        self._error_lbl.pack(pady=(8, 0))

        # Bind Enter key
        root.bind("<Return>", lambda _: self._on_submit())

    # ---------------------------------------------------------------- #
    #  Form builders                                                     #
    # ---------------------------------------------------------------- #

    def _clear_form(self) -> None:
        for w in self._form.winfo_children():
            w.destroy()

    def _field(self, parent, label: str, placeholder: str,
               show_char: str = "") -> PlaceholderEntry:
        """Helper: build a labelled entry and return the entry widget."""
        tk.Label(parent, text=label,
                 bg=COLORS["bg"], fg=COLORS["text_muted"],
                 font=FONTS["small"]).pack(anchor="w", pady=(8, 2))

        row = tk.Frame(parent, bg=COLORS["surface2"],
                       highlightthickness=1,
                       highlightbackground=COLORS["border"],
                       highlightcolor=COLORS["accent"])
        row.pack(fill="x")

        entry = PlaceholderEntry(row, placeholder=placeholder,
                                 show_char=show_char,
                                 style="TEntry")
        entry.pack(side="left", fill="x", expand=True, padx=8, pady=6)

        if show_char:
            eye = IconButton(row, text="👁", command=entry.toggle_show,
                             bg=COLORS["surface2"])
            eye.pack(side="right", padx=6)

        return entry

    def _build_login_form(self) -> None:
        self._username_entry = self._field(self._form, "Username", "Enter username")
        self._password_entry = self._field(self._form, "Master Password",
                                           "Enter master password", show_char="•")

    def _build_register_form(self) -> None:
        self._username_entry  = self._field(self._form, "Username", "Choose a username")
        self._password_entry  = self._field(self._form, "Master Password",
                                            "Choose a strong password", show_char="•")
        self._password2_entry = self._field(self._form, "Confirm Password",
                                            "Repeat master password", show_char="•")

    # ---------------------------------------------------------------- #
    #  Mode switching                                                    #
    # ---------------------------------------------------------------- #

    def _switch_mode(self, mode: str) -> None:
        self._mode.set(mode)
        self._error_var.set("")
        self._clear_form()

        if mode == "login":
            self._tab_login.configure(bg=COLORS["accent"], fg="#ffffff")
            self._tab_reg.configure(bg=COLORS["surface"], fg=COLORS["text_muted"])
            self._submit_btn.configure(text="Login")
            self._build_login_form()
        else:
            self._tab_reg.configure(bg=COLORS["accent"], fg="#ffffff")
            self._tab_login.configure(bg=COLORS["surface"], fg=COLORS["text_muted"])
            self._submit_btn.configure(text="Create Account")
            self._build_register_form()

    # ---------------------------------------------------------------- #
    #  Submit handler                                                    #
    # ---------------------------------------------------------------- #

    def _on_submit(self) -> None:
        self._error_var.set("")
        username = self._username_entry.real_get().strip()
        password = self._password_entry.real_get()

        if not username or not password:
            self._error_var.set("Please fill in all fields.")
            return

        if self._mode.get() == "login":
            self._do_login(username, password)
        else:
            self._do_register(username, password)

    def _do_login(self, username: str, password: str) -> None:
        result = auth.login_user(username, password)
        if result["success"]:
            enc_mgr = EncryptionManager()
            enc_mgr.init_cipher(password, result["enc_salt"])
            session = auth.Session(
                user_id     = result["user"]["id"],
                username    = result["user"]["username"],
                enc_manager = enc_mgr,
            )
            self.root.destroy()
            self._on_success(session)
        else:
            self._error_var.set(result["error"])

    def _do_register(self, username: str, password: str) -> None:
        password2 = self._password2_entry.real_get()
        if password != password2:
            self._error_var.set("Passwords do not match.")
            return

        result = auth.register_user(username, password)
        if result["success"]:
            self._switch_mode("login")
            self._error_var.set("")   # clear any old error
            ToastNotification(self.root, "Account created! Please log in.", "success")
        else:
            self._error_var.set(result["error"])

    # ---------------------------------------------------------------- #
    #  Run                                                               #
    # ---------------------------------------------------------------- #

    def run(self) -> None:
        self.root.mainloop()
