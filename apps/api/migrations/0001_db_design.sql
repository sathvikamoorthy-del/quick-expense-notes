-- knm-generated: db-design dialect=sqlite; from docs/project/db_design.md
-- Hand-added (user approved 2026-11-13), from constraints the generator lists as "not mapped":
--   the code CHECKs (design: length 1 / length 3, upper case) and UQ (code, category_code) on merchants.
-- NOT NULL on the code keys is also hand-added: SQLite lets a non-INTEGER PRIMARY KEY hold NULL otherwise
-- (the design says Null: no; the generator left it out).
CREATE TABLE "categories" (
  "code" TEXT NOT NULL PRIMARY KEY CHECK (length("code") = 1 AND "code" = upper("code")),
  "name" TEXT NOT NULL UNIQUE
);

CREATE TABLE "merchants" (
  "code" TEXT NOT NULL PRIMARY KEY CHECK (length("code") = 3 AND "code" = upper("code")),
  "name" TEXT NOT NULL UNIQUE,
  "category_code" TEXT NOT NULL REFERENCES "categories"("code") ON DELETE RESTRICT
);
CREATE INDEX "idx_merchants_category_code" ON "merchants" ("category_code");
CREATE UNIQUE INDEX "uq_merchants_code_category_code" ON "merchants" ("code", "category_code");
