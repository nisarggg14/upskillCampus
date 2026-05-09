
# 🔐 PassVault — Secure Password Manager (NeonDB Edition)

A Python desktop password manager that encrypts credentials locally and stores them securely in a **NeonDB (PostgreSQL)** database.

---

## Features

- Secure credential vault with AES-based Fernet encryption
- Master password hashing using PBKDF2-HMAC-SHA256
- NeonDB / PostgreSQL cloud storage with parameterized queries
- Login lockout after repeated failed attempts
- Idle session timeout and auto-logout
- Password generator with strength feedback
- Clipboard copy with auto-clear
- Export / import encrypted vault backups
- Dark-themed Tkinter desktop UI

---

## Project Structure

```
.
├── app/
│   ├── assets/                # Static application assets
│   ├── core/                  # Business and authentication logic
│   │   └── auth.py
│   ├── database/              # Neon/PostgreSQL persistence layer
│   │   └── database.py
│   ├── ui/                    # Tkinter desktop interface
│   │   ├── components.py
│   │   ├── dashboard.py
│   │   └── login_window.py
│   └── utils/                 # Shared helpers and utilities
│       ├── encryption.py
│       └── password_generator.py
├── docs/                      # Project documentation
├── screenshots/               # UI screenshots
├── tests/                     # Unit tests and integration checks
├── .env.example
├── .gitignore
├── main.py                    # Application launcher
├── README.md
└── requirements.txt
```

---

## Getting Started

### 1 — Create a NeonDB database

1. Go to **https://console.neon.tech** and sign up.
2. Create a new project and open **Connection Details**.
3. Choose the `psycopg2` connection string format.
4. Copy the database URL.

### 2 — Configure your environment

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Then open `.env` and set:

```bash
DATABASE_URL=YOUR_NEON_DATABASE_URL
```

### 3 — Install dependencies

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4 — Run the app

```bash
# Activate your virtual environment first
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS / Linux

python main.py
```

---

## Technologies

- Python 3.10+
- Tkinter for desktop UI
- psycopg2-binary for PostgreSQL compatibility
- python-dotenv for environment configuration
- cryptography for secure encryption

---

## Database Integration

The app loads `DATABASE_URL` from `.env` and initializes the following tables automatically:

- `users`
- `credentials`

This ensures NeonDB connectivity works before the UI starts.

---

## Testing

Run the import validation test:

```bash
pytest tests/test_imports.py
```

---

## Notes for Recruiters

This project is built with a clean package layout for scalability, separation of concerns, and maintainability. The `app/` package keeps UI, database, business logic, and utilities isolated for future expansion.

---

## Security

- Secrets and database URLs are loaded from `.env` only.
- `.env` is ignored by Git.
- Passwords are encrypted before being stored in NeonDB.

---

## License

MIT
=======
# upskillCampus
>>>>>>> 2d40faf97eb2aff14f40756de6961d6eb7396e28
