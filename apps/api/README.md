# api

Python API (FastAPI). The virtual environment is not created for you.

```
python3 -m venv .venv && source .venv/bin/activate
pip install pip-tools
pip-compile requirements.in -o requirements.txt   # after requirements.in changes
pip install -r requirements.txt
```

Run, test and lint commands are added by the modules (python-build, pytest-testing, python-quality).

## Accounts (REQ-275)

There is no sign-up yet. Create the users table, then the demo user `asha@example.com`:

```
python -c "import sqlite3, pathlib; c = sqlite3.connect('data/app.db'); c.executescript(pathlib.Path('migrations/0003_users.sql').read_text()); c.close()"
python -m scripts.seed_users   # password from DEMO_USER_PASSWORD; stored only as a bcrypt hash
```

`POST /auth/sign-in` with `{email, password}` returns a token valid for 60 minutes; send it as `Authorization: Bearer <token>`.
Set `JWT_SECRET` (at least 32 characters) in `.env`.
