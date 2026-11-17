# Rules
- Docs live in docs/. Requirements are in docs/requirements.
- Run `pytest -q` in apps/api before every commit. All tests must pass.
- Routes stay thin. Business rules live in the service. No database code in the React UI.
- Amounts are stored as integer paise.