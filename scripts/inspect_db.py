"""
inspect_db.py
-------------
Inspects the SQLite database and prints table names, schemas, and row counts.
Safe — READ ONLY, makes no changes.
"""

import sqlite3
import json
import os

DATABASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.db')

def inspect():
    if not os.path.exists(DATABASE):
        print(f"[ERROR] database.db not found at: {DATABASE}")
        return

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"\n{'='*50}")
    print(f"  DATABASE: {DATABASE}")
    print(f"  TABLES FOUND: {len(tables)}")
    print(f"{'='*50}\n")

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
        count = cursor.fetchone()[0]

        cursor.execute(f"PRAGMA table_info([{table}])")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]

        print(f"  TABLE: {table}")
        print(f"  ROWS : {count}")
        print(f"  COLS : {col_names}")
        print()

    conn.close()
    print("Inspection complete. No data was modified.")

if __name__ == '__main__':
    inspect()
