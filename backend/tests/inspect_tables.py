import os
import sqlite3

db_path = os.path.expandvars(r"%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3")
conn = sqlite3.connect(db_path)
cur = conn.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in active database:")
for t in sorted(tables):
    print(f" - {t}")
conn.close()

