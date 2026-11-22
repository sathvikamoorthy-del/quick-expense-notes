-- expenses (REQ-278, WI-048), from docs/project/db_design.md (design accepted by the product owner on 22 Nov 2026).
-- NOT NULL on the TEXT primary key is explicit: SQLite lets a non-INTEGER PRIMARY KEY hold NULL otherwise.
-- The composite FK (merchant_code, category_code) -> merchants (code, category_code) makes a merchant with another
-- category impossible; it uses uq_merchants_code_category_code from 0001. With merchant_code NULL it does not apply.
-- spent_on IS date(spent_on): date() gives NULL for anything that is not a real YYYY-MM-DD date ("not in the future"
-- depends on today and is checked by the app). Every connection must run PRAGMA foreign_keys = ON.
CREATE TABLE "expenses" (
  "id" TEXT NOT NULL PRIMARY KEY CHECK (length("id") = 36),
  "user_id" TEXT NOT NULL REFERENCES "users"("id") ON DELETE CASCADE,
  "typed_text" TEXT NOT NULL CHECK (length("typed_text") > 0),
  "category_code" TEXT NOT NULL REFERENCES "categories"("code") ON DELETE RESTRICT,
  "merchant_code" TEXT REFERENCES "merchants"("code") ON DELETE RESTRICT,
  "amount_paise" INTEGER NOT NULL CHECK (typeof("amount_paise") = 'integer' AND "amount_paise" > 0),
  "spent_on" TEXT NOT NULL CHECK ("spent_on" IS date("spent_on")),
  "note" TEXT,
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY ("merchant_code", "category_code") REFERENCES "merchants"("code", "category_code") ON DELETE RESTRICT
);
CREATE INDEX "idx_expenses_user_id_spent_on" ON "expenses" ("user_id", "spent_on");
CREATE INDEX "idx_expenses_category_code" ON "expenses" ("category_code");
CREATE INDEX "idx_expenses_merchant_code" ON "expenses" ("merchant_code");
