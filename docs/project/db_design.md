# DB design
Target DB: SQLite 3
Constraints:
- Naming: snake_case, plural table names, FK columns `<singular>_id` / `<table>_code`.
- Ids: text UUIDs (36 chars, lower case, made by the app) on user data; reference tables keyed by their code.
- Dates: ISO 8601 text. A calendar date is `YYYY-MM-DD`; a timestamp is UTC `YYYY-MM-DDTHH:MM:SS.SSSZ`.
- Timestamps: `created_at`, `updated_at` on user data only, default `(strftime('%Y-%m-%dT%H:%M:%fZ','now'))`.
- Money: integer paise (`amount_paise`, 340.00 rupees = 34000), > 0. Shown as rupees with 2 decimals by the app.
- Delete: hard delete (REQ-281: the entry is no longer a record). No soft delete.
- Tenancy: none; one user per account, rows owned by `user_id` (intent, REQ-275).
- Audit columns: none.
- Auth: email + password (bcrypt hash in `users.password_hash`), JWT for requests; tokens are not stored, so no session table.
- Normal form: 3NF; deviations noted on the table.
- SQLite: every connection runs `PRAGMA foreign_keys = ON` (otherwise FKs and cascades are ignored). Types are enforced by `typeof` checks, not STRICT.
- The monthly summary is computed (no table): `sum(amount_paise)` grouped by `category_code` where `substr(spent_on, 1, 7)` is the month, so it always matches the entries (G3).
Sources: intent.md (85ac23f0); source/01-project-brief.md, 02-abbreviation-rules.md, 03-sample-entries.md; REQ-275 to REQ-281 (req.md, mock.md); walkthrough docs/mock/apps/expenses (S01 to S05, gaps/note-to-summary.md).
Tables: db_design_tables.csv (Status: New = proposed by Claude · Feedback = open feedback to apply or answer · Final = accepted)

## Columns
### users
| Column | Type | Null | Default | Key / FK | Index | Constraints | Description |
|---|---|---|---|---|---|---|---|
| id | TEXT | no | | PK | PK | length(id) = 36 | Account UUID |
| email | TEXT | no | | UQ | unique | length > 0 | Sign-in email |
| password_hash | TEXT | no | | | | | bcrypt hash; never the password |
| display_name | TEXT | no | | | | length > 0 | Shown name, e.g. Asha |
| created_at | TEXT | no | now (ISO UTC) | | | | Created |
| updated_at | TEXT | no | now (ISO UTC) | | | | Last changed |

### categories
| Column | Type | Null | Default | Key / FK | Index | Constraints | Description |
|---|---|---|---|---|---|---|---|
| code | TEXT | no | | PK | PK | length 1, upper case | Category code, e.g. F |
| name | TEXT | no | | UQ | unique | | Category name, e.g. Food |

### merchants
| Column | Type | Null | Default | Key / FK | Index | Constraints | Description |
|---|---|---|---|---|---|---|---|
| code | TEXT | no | | PK | PK | length 3, upper case | Merchant code, e.g. SWG |
| name | TEXT | no | | UQ | unique | | Merchant name, e.g. Swiggy |
| category_code | TEXT | no | | FK -> categories.code | yes | UQ (code, category_code) for expenses FK; on delete restrict | Category the merchant sets |

### expenses
| Column | Type | Null | Default | Key / FK | Index | Constraints | Description |
|---|---|---|---|---|---|---|---|
| id | TEXT | no | | PK | PK | length(id) = 36 | Expense UUID |
| user_id | TEXT | no | | FK -> users.id | (user_id, spent_on) | on delete cascade | Owner; only they see it |
| typed_text | TEXT | no | | | | length > 0 | Short entry as typed, e.g. `SWG 340 yd` |
| category_code | TEXT | no | | FK -> categories.code | yes | on delete restrict | Category (summary groups by it) |
| merchant_code | TEXT | yes | | FK -> merchants.code | yes | (merchant_code, category_code) FK -> merchants (code, category_code); on delete restrict | Merchant; null for a category code |
| amount_paise | INTEGER | no | | | | typeof = 'integer' and > 0 | Amount in paise (799.50 = 79950) |
| spent_on | TEXT | no | | | (user_id, spent_on) | spent_on IS date(spent_on); not in the future (app check) | Resolved date `YYYY-MM-DD` (td, yd, dd/mm) |
| note | TEXT | yes | | | | | Text after the date or amount |
| created_at | TEXT | no | now (ISO UTC) | | | | Saved |
| updated_at | TEXT | no | now (ISO UTC) | | | | Last edited (REQ-280) |

Notes on expenses:
- `typed_text` is derived from the other fields (3NF deviation, agreed): kept to pre-fill the short-form edit.
- `category_code` is set by `merchant_code` when there is one (3NF deviation): kept so the summary groups on one column; the composite FK makes a mismatch impossible.
- `spent_on IS date(spent_on)` rejects anything that is not a real `YYYY-MM-DD` date (`IS`, not `=`: date() gives NULL for bad input and a NULL check passes). "Not in the future" depends on today, so the app checks it.
- November 2026 sample: grand total 613850 paise = 6138.50.
