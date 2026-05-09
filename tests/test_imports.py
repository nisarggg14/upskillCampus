import app.core.auth as auth
from app.database import database as db
import app.utils.encryption as encryption
import app.utils.password_generator as password_generator
import app.ui.login_window as login_window
import app.ui.dashboard as dashboard


def test_package_imports():
    assert auth is not None
    assert db is not None
    assert encryption is not None
    assert password_generator is not None
    assert login_window is not None
    assert dashboard is not None
