-- users (REQ-275, WI-039), from docs/project/db_design.md.
-- NOT NULL on the TEXT primary key is explicit: SQLite lets a non-INTEGER PRIMARY KEY hold NULL otherwise.
-- The email is stored lower-cased by the app (sign-in is not case-sensitive); the CHECK keeps the unique index honest.
CREATE TABLE "users" (
  "id" TEXT NOT NULL PRIMARY KEY CHECK (length("id") = 36),
  "email" TEXT NOT NULL UNIQUE CHECK (length("email") > 0 AND "email" = lower("email")),
  "password_hash" TEXT NOT NULL,
  "display_name" TEXT NOT NULL CHECK (length("display_name") > 0),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
