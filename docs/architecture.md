# Application Architecture

PassVault is organized as a modular Python package under the `app/` folder.

- `app/core/` contains business logic and authentication.
- `app/database/` contains Neon/PostgreSQL persistence and schema initialization.
- `app/ui/` contains the desktop Tkinter interface.
- `app/utils/` contains reusable utility code such as encryption and password generation.
- `app/assets/` contains static UI assets.
