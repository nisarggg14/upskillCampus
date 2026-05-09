"""
ui/dashboard.py - Main dashboard window after login.
Handles the vault list, add/edit/delete dialogs, search,
password generator dialog, export/import, and session timeout.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time, json

from app.database import database as db
import app.core.auth as auth_module
from app.utils.encryption import EncryptionManager
from app.utils.password_generator import generate_password, check_strength
from app.ui.components import (
    COLORS, FONTS, apply_theme,
    PlaceholderEntry, IconButton, Divider, ToastNotification,
)


# ------------------------------------------------------------------ #
#  Credential dialog (Add / Edit)                                      #
# ------------------------------------------------------------------ #

class CredentialDialog(tk.Toplevel):
    """
    Modal dialog for creating or editing a credential entry.
    result is set to the form data dict on OK, or None on cancel.
    """

    def __init__(self, parent, enc_manager: EncryptionManager,
                 title: str = "Add Credential",
                 initial: dict | None = None):
        super().__init__(parent)
        self.title(title)
        self.geometry("460x520")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()                     # modal
        self.transient(parent)

        self._enc   = enc_manager
        self.result = None

        apply_theme(self)
        self._build(initial or {})

    # ---------------------------------------------------------------- #

    def _build(self, data: dict) -> None:
        pad = tk.Frame(self, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=28, pady=20)

        tk.Frame(self, bg=COLORS["accent"], height=3).place(x=0, y=0, relwidth=1)

        def field(label, placeholder, show="", val=""):
            tk.Label(pad, text=label, bg=COLORS["bg"],
                     fg=COLORS["text_muted"], font=FONTS["small"]).pack(anchor="w", pady=(10,2))
            row = tk.Frame(pad, bg=COLORS["surface2"],
                           highlightthickness=1,
                           highlightbackground=COLORS["border"],
                           highlightcolor=COLORS["accent"])
            row.pack(fill="x")
            e = PlaceholderEntry(row, placeholder=placeholder,
                                 show_char=show, style="TEntry")
            e.pack(side="left", fill="x", expand=True, padx=8, pady=6)
            if show:
                eye = IconButton(row, text="👁", command=e.toggle_show,
                                 bg=COLORS["surface2"])
                eye.pack(side="right", padx=6)
            if val:
                e._on_focus_in(None)
                e.delete(0, tk.END)
                e.insert(0, val)
                e._showing_ph = False
            return e

        self._website  = field("Website / App", "e.g. GitHub",       val=data.get("website",""))
        self._username = field("Username / Email","you@example.com",  val=data.get("username",""))
        self._password = field("Password",       "Enter password",    show="•", val=data.get("password",""))

        # Password row with generator button
        gen_btn = ttk.Button(pad, text="⚡ Generate",
                             style="Ghost.TButton",
                             command=self._generate)
        gen_btn.pack(anchor="e", pady=(4, 0))

        # Strength bar
        self._strength_frame = tk.Frame(pad, bg=COLORS["bg"])
        self._strength_frame.pack(fill="x", pady=(2,0))
        self._strength_var  = tk.DoubleVar(value=0)
        self._strength_lbl  = tk.Label(self._strength_frame, text="",
                                        bg=COLORS["bg"], fg=COLORS["text_muted"],
                                        font=FONTS["small"])
        self._strength_lbl.pack(anchor="w")
        pb = ttk.Progressbar(self._strength_frame, variable=self._strength_var,
                             maximum=100, style="Strength.Horizontal.TProgressbar")
        pb.pack(fill="x")
        self._pb = pb

        self._password.bind("<KeyRelease>", self._update_strength)

        # Notes
        tk.Label(pad, text="Notes (optional)", bg=COLORS["bg"],
                 fg=COLORS["text_muted"], font=FONTS["small"]).pack(anchor="w", pady=(10,2))
        notes_frame = tk.Frame(pad, bg=COLORS["surface2"],
                               highlightthickness=1,
                               highlightbackground=COLORS["border"])
        notes_frame.pack(fill="x")
        self._notes = tk.Text(notes_frame, height=3,
                              bg=COLORS["surface2"], fg=COLORS["text"],
                              insertbackground=COLORS["text"],
                              relief="flat", font=FONTS["body"],
                              padx=8, pady=6)
        self._notes.pack(fill="x")
        if data.get("notes"):
            self._notes.insert("1.0", data["notes"])

        Divider(pad).pack(fill="x", pady=14)

        btn_row = tk.Frame(pad, bg=COLORS["bg"])
        btn_row.pack(fill="x")
        ttk.Button(btn_row, text="Cancel", style="Ghost.TButton",
                   command=self.destroy).pack(side="right", padx=(8,0))
        ttk.Button(btn_row, text="Save", style="Accent.TButton",
                   command=self._save).pack(side="right")

    def _update_strength(self, _event=None) -> None:
        pw = self._password.real_get()
        if not pw:
            self._strength_var.set(0)
            self._strength_lbl.configure(text="")
            return
        info = check_strength(pw)
        self._strength_var.set(info["score"])
        self._strength_lbl.configure(text=info["label"], fg=info["color"])
        style = ttk.Style(self)
        style.configure("Strength.Horizontal.TProgressbar",
                        background=info["color"])

    def _generate(self) -> None:
        """Open mini generator dialog."""
        GenMiniDialog(self, callback=self._apply_generated)

    def _apply_generated(self, pw: str) -> None:
        self._password._on_focus_in(None)
        self._password.delete(0, tk.END)
        self._password.insert(0, pw)
        self._password._showing_ph = False
        self._update_strength()

    def _save(self) -> None:
        website  = self._website.real_get().strip()
        username = self._username.real_get().strip()
        password = self._password.real_get()
        notes    = self._notes.get("1.0", tk.END).strip()

        if not website or not username or not password:
            messagebox.showwarning("Missing fields",
                                   "Website, username and password are required.",
                                   parent=self)
            return

        self.result = {
            "website":  website,
            "username": username,
            "password": password,
            "notes":    notes,
        }
        self.destroy()


# ------------------------------------------------------------------ #
#  Mini generator dialog                                               #
# ------------------------------------------------------------------ #

class GenMiniDialog(tk.Toplevel):
    """Small popup for customising and generating a password."""

    def __init__(self, parent, callback=None):
        super().__init__(parent)
        self.title("Password Generator")
        self.geometry("380x400")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        self.transient(parent)
        self._callback = callback
        apply_theme(self)
        self._build()

    def _build(self) -> None:
        pad = tk.Frame(self, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(pad, text="⚡ Password Generator",
                 bg=COLORS["bg"], fg=COLORS["text"],
                 font=FONTS["heading"]).pack(anchor="w")
        Divider(pad).pack(fill="x", pady=10)

        # Length slider
        tk.Label(pad, text="Length", bg=COLORS["bg"],
                 fg=COLORS["text_muted"], font=FONTS["small"]).pack(anchor="w")
        len_row = tk.Frame(pad, bg=COLORS["bg"])
        len_row.pack(fill="x")
        self._len_var = tk.IntVar(value=16)
        self._len_lbl = tk.Label(len_row, textvariable=self._len_var,
                                  bg=COLORS["bg"], fg=COLORS["accent"],
                                  font=FONTS["subhead"], width=3)
        self._len_lbl.pack(side="right")
        ttk.Scale(len_row, from_=8, to=64,
                  variable=self._len_var, orient="horizontal",
                  command=lambda _: self._preview()).pack(side="left", fill="x", expand=True)

        # Options checkboxes
        self._upper   = self._check(pad, "Uppercase (A–Z)",   True)
        self._lower   = self._check(pad, "Lowercase (a–z)",   True)
        self._digits  = self._check(pad, "Numbers (0–9)",     True)
        self._symbols = self._check(pad, "Symbols (!@#…)",    True)

        Divider(pad).pack(fill="x", pady=10)

        # Preview
        tk.Label(pad, text="Generated password", bg=COLORS["bg"],
                 fg=COLORS["text_muted"], font=FONTS["small"]).pack(anchor="w")
        self._preview_var = tk.StringVar()
        preview_lbl = tk.Label(pad, textvariable=self._preview_var,
                                bg=COLORS["surface2"], fg=COLORS["text"],
                                font=FONTS["mono"], anchor="w",
                                padx=10, pady=8)
        preview_lbl.pack(fill="x")

        self._preview()

        btn_row = tk.Frame(pad, bg=COLORS["bg"])
        btn_row.pack(fill="x", pady=(12,0))
        ttk.Button(btn_row, text="🔄 Regenerate",
                   style="Ghost.TButton",
                   command=self._preview).pack(side="left")
        ttk.Button(btn_row, text="Use this password",
                   style="Accent.TButton",
                   command=self._use).pack(side="right")

    def _check(self, parent, text, default=True) -> tk.BooleanVar:
        var = tk.BooleanVar(value=default)
        tk.Checkbutton(parent, text=text, variable=var,
                       bg=COLORS["bg"], fg=COLORS["text"],
                       selectcolor=COLORS["surface2"],
                       activebackground=COLORS["bg"],
                       activeforeground=COLORS["accent"],
                       font=FONTS["body"],
                       command=self._preview).pack(anchor="w", pady=2)
        return var

    def _preview(self, *_) -> None:
        try:
            pw = generate_password(
                length      = self._len_var.get(),
                use_upper   = self._upper.get(),
                use_lower   = self._lower.get(),
                use_digits  = self._digits.get(),
                use_symbols = self._symbols.get(),
            )
            self._preview_var.set(pw)
        except ValueError:
            self._preview_var.set("(select at least one option)")

    def _use(self) -> None:
        pw = self._preview_var.get()
        if self._callback and not pw.startswith("("):
            self._callback(pw)
        self.destroy()


# ------------------------------------------------------------------ #
#  Main Dashboard window                                               #
# ------------------------------------------------------------------ #

class Dashboard:
    """
    Primary application window shown after a successful login.
    Contains the credentials vault table plus all action buttons.
    """

    SESSION_CHECK_INTERVAL = 5_000   # ms between idle-timeout checks

    def __init__(self, session: auth_module.Session, on_logout):
        self._session    = session
        self._on_logout  = on_logout
        self._enc        = session.enc_manager

        self.root = tk.Tk()
        self.root.title("PassVault – Dashboard")
        self.root.geometry("900x640")
        self.root.minsize(780, 520)
        apply_theme(self.root)

        self._build_ui()
        self._load_credentials()
        self._schedule_timeout_check()

    # ---------------------------------------------------------------- #
    #  UI layout                                                         #
    # ---------------------------------------------------------------- #

    def _build_ui(self) -> None:
        root = self.root

        # ── Sidebar ──────────────────────────────────────────────────
        sidebar = tk.Frame(root, bg=COLORS["surface"], width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Frame(sidebar, bg=COLORS["accent"], width=3).pack(side="left", fill="y")

        inner = tk.Frame(sidebar, bg=COLORS["surface"])
        inner.pack(fill="both", expand=True, padx=16, pady=24)

        tk.Label(inner, text="🔐 PassVault",
                 bg=COLORS["surface"], fg=COLORS["text"],
                 font=("Segoe UI", 15, "bold")).pack(anchor="w")

        tk.Label(inner, text=f"@{self._session.username}",
                 bg=COLORS["surface"], fg=COLORS["text_muted"],
                 font=FONTS["small"]).pack(anchor="w", pady=(2,20))

        Divider(inner).pack(fill="x", pady=(0,16))

        def nav_btn(label, cmd):
            b = ttk.Button(inner, text=label, style="Ghost.TButton", command=cmd)
            b.pack(fill="x", pady=3)
            return b

        nav_btn("➕  Add Credential",    self._cmd_add)
        nav_btn("⚡  Generate Password", self._cmd_gen)
        nav_btn("📤  Export Vault",      self._cmd_export)
        nav_btn("📥  Import Vault",      self._cmd_import)

        # Spacer
        tk.Frame(inner, bg=COLORS["surface"]).pack(fill="both", expand=True)

        Divider(inner).pack(fill="x", pady=8)
        nav_btn("🚪  Logout",            self._cmd_logout)

        # Session timer label
        self._timer_var = tk.StringVar(value="")
        tk.Label(inner, textvariable=self._timer_var,
                 bg=COLORS["surface"], fg=COLORS["text_dim"],
                 font=FONTS["small"]).pack(anchor="w", pady=(4,0))

        # ── Main content area ────────────────────────────────────────
        main = tk.Frame(root, bg=COLORS["bg"])
        main.pack(side="right", fill="both", expand=True)

        # Top bar
        topbar = tk.Frame(main, bg=COLORS["surface"], height=56)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        # Stats label
        self._stats_var = tk.StringVar(value="")
        tk.Label(topbar, textvariable=self._stats_var,
                 bg=COLORS["surface"], fg=COLORS["text_muted"],
                 font=FONTS["small"]).pack(side="left", padx=20)

        # Search
        search_frame = tk.Frame(topbar, bg=COLORS["surface2"],
                                highlightthickness=1,
                                highlightbackground=COLORS["border"],
                                highlightcolor=COLORS["accent"])
        search_frame.pack(side="right", padx=16, pady=10)

        self._search_entry = PlaceholderEntry(search_frame,
                                              placeholder="🔍  Search...",
                                              style="TEntry")
        self._search_entry.pack(padx=10, pady=4, ipadx=80)
        self._search_entry.bind("<KeyRelease>", self._on_search)

        Divider(main).pack(fill="x")

        # Treeview (vault table)
        tree_frame = tk.Frame(main, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, padx=16, pady=12)

        cols = ("website", "username", "password", "notes", "updated")
        self._tree = ttk.Treeview(tree_frame, columns=cols,
                                  show="headings", selectmode="browse")

        headers = {
            "website":  ("Website / App", 180),
            "username": ("Username / Email", 200),
            "password": ("Password", 140),
            "notes":    ("Notes", 160),
            "updated":  ("Last Updated", 130),
        }
        for col, (head, w) in headers.items():
            self._tree.heading(col, text=head,
                               command=lambda c=col: self._sort_by(c))
            self._tree.column(col, width=w, minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Row action bar
        action_bar = tk.Frame(main, bg=COLORS["surface"], height=44)
        action_bar.pack(fill="x", side="bottom")
        action_bar.pack_propagate(False)

        ab_inner = tk.Frame(action_bar, bg=COLORS["surface"])
        ab_inner.pack(side="right", padx=16, pady=6)

        ttk.Button(ab_inner, text="📋 Copy Password",
                   style="Ghost.TButton",
                   command=self._cmd_copy).pack(side="left", padx=4)
        ttk.Button(ab_inner, text="✏️ Edit",
                   style="Ghost.TButton",
                   command=self._cmd_edit).pack(side="left", padx=4)
        ttk.Button(ab_inner, text="🗑 Delete",
                   style="Danger.TButton",
                   command=self._cmd_delete).pack(side="left", padx=4)

        # Bind double-click → edit
        self._tree.bind("<Double-Button-1>", lambda _: self._cmd_edit())

        # Activity tracking
        for event in ("<Motion>", "<KeyPress>", "<Button-1>"):
            root.bind(event, self._on_activity, add="+")

        # Internal cache: maps tree iid → db credential id
        self._iid_to_id: dict[str, int] = {}

    # ---------------------------------------------------------------- #
    #  Data loading                                                      #
    # ---------------------------------------------------------------- #

    def _load_credentials(self, query: str = "") -> None:
        self._tree.delete(*self._tree.get_children())
        self._iid_to_id.clear()

        if query:
            rows = db.search_credentials(self._session.user_id, query)
        else:
            rows = db.get_credentials(self._session.user_id)

        for row in rows:
            try:
                plain_pw = self._enc.decrypt(row["password"])
            except Exception:
                plain_pw = "⚠ decrypt error"

            masked  = "•" * min(len(plain_pw), 12)
            updated_raw = row["updated_at"]
            if updated_raw is None:
                updated = ""
            elif hasattr(updated_raw, "strftime"):
                updated = updated_raw.strftime("%Y-%m-%d")
            else:
                updated = str(updated_raw)[:10]

            iid = self._tree.insert("", tk.END, values=(
                row["website"],
                row["username"],
                masked,
                row["notes"] or "",
                updated,
            ))
            self._iid_to_id[iid] = row["id"]

        count = db.count_credentials(self._session.user_id)
        self._stats_var.set(f"{count} credential(s) stored")

    def _on_search(self, _event=None) -> None:
        self._session.touch()
        self._load_credentials(self._search_entry.real_get().strip())

    # ---------------------------------------------------------------- #
    #  Commands                                                          #
    # ---------------------------------------------------------------- #

    def _cmd_add(self) -> None:
        self._session.touch()
        dlg = CredentialDialog(self.root, self._enc, title="Add Credential")
        self.root.wait_window(dlg)
        if dlg.result:
            enc_pw = self._enc.encrypt(dlg.result["password"])
            db.add_credential(
                user_id  = self._session.user_id,
                website  = dlg.result["website"],
                username = dlg.result["username"],
                password = enc_pw,
                notes    = dlg.result["notes"],
            )
            self._load_credentials()
            ToastNotification(self.root, "Credential added ✓", "success")

    def _get_selected_row(self) -> tuple[str | None, int | None]:
        """Return (iid, db_id) of the selected tree row, or (None, None)."""
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("No selection", "Please select a credential first.",
                                parent=self.root)
            return None, None
        iid = sel[0]
        return iid, self._iid_to_id.get(iid)

    def _cmd_copy(self) -> None:
        self._session.touch()
        iid, cred_id = self._get_selected_row()
        if cred_id is None:
            return
        row = db.get_credential_by_id(cred_id, self._session.user_id)
        if row:
            try:
                plain_pw = self._enc.decrypt(row["password"])
                self.root.clipboard_clear()
                self.root.clipboard_append(plain_pw)
                ToastNotification(self.root, "Password copied to clipboard ✓", "success")
                # Schedule clipboard clear after 30 seconds
                self.root.after(30_000, lambda: self.root.clipboard_clear())
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)

    def _cmd_edit(self) -> None:
        self._session.touch()
        iid, cred_id = self._get_selected_row()
        if cred_id is None:
            return
        row = db.get_credential_by_id(cred_id, self._session.user_id)
        if not row:
            return
        try:
            plain_pw = self._enc.decrypt(row["password"])
        except Exception:
            plain_pw = ""

        initial = {
            "website":  row["website"],
            "username": row["username"],
            "password": plain_pw,
            "notes":    row["notes"] or "",
        }
        dlg = CredentialDialog(self.root, self._enc,
                               title="Edit Credential", initial=initial)
        self.root.wait_window(dlg)
        if dlg.result:
            enc_pw = self._enc.encrypt(dlg.result["password"])
            db.update_credential(
                cred_id  = cred_id,
                user_id  = self._session.user_id,
                website  = dlg.result["website"],
                username = dlg.result["username"],
                password = enc_pw,
                notes    = dlg.result["notes"],
            )
            self._load_credentials()
            ToastNotification(self.root, "Credential updated ✓", "success")

    def _cmd_delete(self) -> None:
        self._session.touch()
        iid, cred_id = self._get_selected_row()
        if cred_id is None:
            return
        row = db.get_credential_by_id(cred_id, self._session.user_id)
        if not row:
            return
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete credentials for '{row['website']}'?\nThis cannot be undone.",
            icon="warning",
            parent=self.root,
        )
        if confirm:
            db.delete_credential(cred_id, self._session.user_id)
            self._load_credentials()
            ToastNotification(self.root, "Credential deleted", "success")

    def _cmd_gen(self) -> None:
        self._session.touch()
        GenMiniDialog(self.root)

    # ---------------------------------------------------------------- #
    #  Export / Import                                                   #
    # ---------------------------------------------------------------- #

    def _cmd_export(self) -> None:
        self._session.touch()
        path = filedialog.asksaveasfilename(
            parent=self.root,
            defaultextension=".pvault",
            filetypes=[("PassVault encrypted export", "*.pvault"), ("All files", "*")],
            title="Export Vault",
        )
        if not path:
            return

        # Ask for export passphrase
        PassphraseDialog(self.root, "Export passphrase",
                         callback=lambda pp: self._do_export(path, pp))

    def _do_export(self, path: str, passphrase: str) -> None:
        rows = db.get_credentials(self._session.user_id)
        data = []
        for row in rows:
            try:
                pw = self._enc.decrypt(row["password"])
            except Exception:
                pw = ""
            data.append({
                "website":  row["website"],
                "username": row["username"],
                "password": pw,
                "notes":    row["notes"] or "",
            })
        blob = EncryptionManager.encrypt_export(json.dumps(data), passphrase)
        with open(path, "wb") as f:
            f.write(blob)
        ToastNotification(self.root, f"Exported {len(data)} credential(s) ✓", "success")

    def _cmd_import(self) -> None:
        self._session.touch()
        path = filedialog.askopenfilename(
            parent=self.root,
            filetypes=[("PassVault encrypted export", "*.pvault"), ("All files", "*")],
            title="Import Vault",
        )
        if not path:
            return
        PassphraseDialog(self.root, "Import passphrase",
                         callback=lambda pp: self._do_import(path, pp))

    def _do_import(self, path: str, passphrase: str) -> None:
        try:
            with open(path, "rb") as f:
                blob = f.read()
            json_str = EncryptionManager.decrypt_export(blob, passphrase)
            items = json.loads(json_str)
        except Exception as e:
            messagebox.showerror("Import failed",
                                 f"Could not decrypt file.\n{e}", parent=self.root)
            return

        count = 0
        for item in items:
            enc_pw = self._enc.encrypt(item["password"])
            db.add_credential(
                user_id  = self._session.user_id,
                website  = item["website"],
                username = item["username"],
                password = enc_pw,
                notes    = item.get("notes", ""),
            )
            count += 1
        self._load_credentials()
        ToastNotification(self.root, f"Imported {count} credential(s) ✓", "success")

    # ---------------------------------------------------------------- #
    #  Sorting                                                           #
    # ---------------------------------------------------------------- #

    def _sort_by(self, col: str) -> None:
        data = [(self._tree.set(iid, col), iid)
                for iid in self._tree.get_children()]
        data.sort(key=lambda x: x[0].lower())
        for idx, (_, iid) in enumerate(data):
            self._tree.move(iid, "", idx)

    # ---------------------------------------------------------------- #
    #  Session timeout                                                   #
    # ---------------------------------------------------------------- #

    def _on_activity(self, _event=None) -> None:
        self._session.touch()

    def _schedule_timeout_check(self) -> None:
        self.root.after(self.SESSION_CHECK_INTERVAL, self._check_timeout)

    def _check_timeout(self) -> None:
        if self._session.is_expired():
            messagebox.showinfo(
                "Session expired",
                "Your session has timed out due to inactivity.\nPlease log in again.",
                parent=self.root,
            )
            self._cmd_logout()
            return

        remaining = self._session.seconds_remaining()
        self._timer_var.set(f"⏱ {remaining}s idle")
        self._schedule_timeout_check()

    # ---------------------------------------------------------------- #
    #  Logout                                                            #
    # ---------------------------------------------------------------- #

    def _cmd_logout(self) -> None:
        self.root.destroy()
        self._on_logout()

    # ---------------------------------------------------------------- #
    #  Run                                                               #
    # ---------------------------------------------------------------- #

    def run(self) -> None:
        self.root.mainloop()


# ------------------------------------------------------------------ #
#  Passphrase dialog (helper for export/import)                       #
# ------------------------------------------------------------------ #

class PassphraseDialog(tk.Toplevel):
    def __init__(self, parent, label: str, callback):
        super().__init__(parent)
        self.title(label)
        self.geometry("360x180")
        self.resizable(False, False)
        self.configure(bg=COLORS["bg"])
        self.grab_set()
        self.transient(parent)
        apply_theme(self)
        self._callback = callback

        pad = tk.Frame(self, bg=COLORS["bg"])
        pad.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(pad, text=label, bg=COLORS["bg"], fg=COLORS["text"],
                 font=FONTS["heading"]).pack(anchor="w")
        tk.Label(pad, text="Enter a passphrase to encrypt / decrypt the export file.",
                 bg=COLORS["bg"], fg=COLORS["text_muted"],
                 font=FONTS["small"], wraplength=300).pack(anchor="w", pady=(2,10))

        row = tk.Frame(pad, bg=COLORS["surface2"],
                       highlightthickness=1, highlightbackground=COLORS["border"])
        row.pack(fill="x")
        self._entry = PlaceholderEntry(row, placeholder="Passphrase",
                                       show_char="•", style="TEntry")
        self._entry.pack(fill="x", padx=8, pady=6)

        btn_row = tk.Frame(pad, bg=COLORS["bg"])
        btn_row.pack(fill="x", pady=(12,0))
        ttk.Button(btn_row, text="Cancel", style="Ghost.TButton",
                   command=self.destroy).pack(side="right", padx=(8,0))
        ttk.Button(btn_row, text="OK", style="Accent.TButton",
                   command=self._ok).pack(side="right")

        self.bind("<Return>", lambda _: self._ok())

    def _ok(self) -> None:
        pp = self._entry.real_get()
        if not pp:
            return
        self.destroy()
        self._callback(pp)
