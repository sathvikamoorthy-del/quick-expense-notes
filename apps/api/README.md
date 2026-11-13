# api

Python API (FastAPI). The virtual environment is not created for you.

```
python3 -m venv .venv && source .venv/bin/activate
pip install pip-tools
pip-compile requirements.in -o requirements.txt   # after requirements.in changes
pip install -r requirements.txt
```

Run, test and lint commands are added by the modules (python-build, pytest-testing, python-quality).
