"""
main.py - Entry point for PassVault Password Manager.

Usage:
    python main.py
"""

from app.ui.login_window import LoginWindow
from app.ui.dashboard import Dashboard
import app.core.auth as auth_module


def start_dashboard(session: auth_module.Session) -> None:
    """Called by LoginWindow after a successful login."""
    dash = Dashboard(session, on_logout=restart_login)
    dash.run()


def restart_login() -> None:
    """Re-open the login window after logout or timeout."""
    win = LoginWindow(on_login_success=start_dashboard)
    win.run()


def main() -> None:
    restart_login()


if __name__ == "__main__":
    main()
