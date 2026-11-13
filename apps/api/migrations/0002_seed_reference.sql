-- Seed of the reference tables (user approved 2026-11-13).
-- Source: docs/project/db_design_tables.csv descriptions and docs/project/source/02-abbreviation-rules.md.
INSERT INTO "categories" ("code", "name") VALUES
  ('F', 'Food'),
  ('T', 'Travel'),
  ('R', 'Rent'),
  ('U', 'Utilities'),
  ('S', 'Shopping'),
  ('H', 'Health'),
  ('E', 'Entertainment'),
  ('O', 'Other');

INSERT INTO "merchants" ("code", "name", "category_code") VALUES
  ('SWG', 'Swiggy', 'F'),
  ('ZMT', 'Zomato', 'F'),
  ('UBR', 'Uber', 'T'),
  ('OLA', 'Ola', 'T'),
  ('AMZ', 'Amazon', 'S'),
  ('NFX', 'Netflix', 'E'),
  ('APL', 'Apollo Pharmacy', 'H'),
  ('BSN', 'BSNL', 'U');
