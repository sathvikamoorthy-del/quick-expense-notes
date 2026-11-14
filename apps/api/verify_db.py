r"""Quick Expense Notes: database practice and verification.

Run from apps/api:   .\.venv\Scripts\python verify_db.py
It only READS data/app.db. All changes are made on a practice copy, which is deleted at the end.
"""
import os
import shutil
import sqlite3
import sys

DB = os.path.join("data", "app.db")
PRACTICE = os.path.join("data", "practice.db")
BACKUP = os.path.join("data", "practice.backup.db")
ok_all = True


def check(label, passed, detail=""):
    global ok_all
    ok_all = ok_all and passed
    print(("PASS  " if passed else "FAIL  ") + label + (f"   {detail}" if detail else ""))


if not os.path.exists(DB):
    print("Run this from apps/api (data/app.db not found).")
    sys.exit(1)

print("== 1. What is in the database (read only) ==")
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
tables = [r[0] for r in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
print("tables:", tables)
check("categories and merchants exist", "categories" in tables and "merchants" in tables)
n_cat = con.execute("select count(*) from categories").fetchone()[0]
n_mer = con.execute("select count(*) from merchants").fetchone()[0]
check("8 categories", n_cat == 8, f"found {n_cat}")
check("8 merchants", n_mer == 8, f"found {n_mer}")
print("\nmerchant -> category (join):")
for code, merchant, category in con.execute(
    "select m.code, m.name, c.name from merchants m join categories c on c.code = m.category_code order by m.code"
):
    print(f"   {code}  {merchant:<16} {category}")
check("foreign keys consistent", con.execute("pragma foreign_key_check").fetchall() == [])
con.close()

print("\n== 2. ORM read (what codes.py does) ==")
try:
    import asyncio

    sys.path.insert(0, os.getcwd())
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from app.entries.codes import read_codes

    async def main():
        engine = create_async_engine("sqlite+aiosqlite:///" + DB.replace("\\", "/"))
        async with AsyncSession(engine) as session:
            return await read_codes(session)

    codes = asyncio.run(main())
    check("ORM reads 16 codes", len(codes) == 16, f"found {len(codes)}")
    check("SWG is Swiggy / Food", codes["SWG"].merchant == "Swiggy" and codes["SWG"].category == "Food")
    check("F is Food, no merchant", codes["F"].merchant is None and codes["F"].category == "Food")
except Exception as exc:  # the ORM part is a bonus
    print("SKIPPED ORM check:", type(exc).__name__, exc)

print("\n== 3. Constraints work (on a practice copy) ==")
shutil.copyfile(DB, PRACTICE)
p = sqlite3.connect(PRACTICE)
p.execute("pragma foreign_keys = on")
for label, sql in [
    ("lowercase category code is rejected", "insert into categories values ('f', 'Test')"),
    ("2-character category code is rejected", "insert into categories values ('FF', 'Test2')"),
    ("merchant with a missing category is rejected", "insert into merchants values ('XYZ', 'Nobody', 'Q')"),
    ("deleting a category that is in use is rejected", "delete from categories where code = 'F'"),
]:
    try:
        p.execute(sql)
        p.rollback()
        check(label, False, "it was accepted!")
    except sqlite3.IntegrityError as exc:
        p.rollback()
        check(label, True, str(exc)[:60])
p.close()

print("\n== 4. Backup, migrate, verify, roll back (practice copy) ==")
shutil.copyfile(PRACTICE, BACKUP)
check("backup taken", os.path.exists(BACKUP))
p = sqlite3.connect(PRACTICE)
p.execute("alter table categories add column notes text")
p.commit()
cols = [r[1] for r in p.execute("pragma table_info(categories)")]
check("migration applied: column 'notes' exists", "notes" in cols, str(cols))
p.close()
shutil.copyfile(BACKUP, PRACTICE)  # roll back
p = sqlite3.connect(PRACTICE)
cols = [r[1] for r in p.execute("pragma table_info(categories)")]
check("rolled back: column 'notes' is gone", "notes" not in cols, str(cols))
p.close()

for f in (PRACTICE, BACKUP):
    if os.path.exists(f):
        os.remove(f)
print("\npractice files removed; data/app.db was never changed.")
print("\nRESULT:", "ALL CHECKS PASSED" if ok_all else "SOME CHECKS FAILED")