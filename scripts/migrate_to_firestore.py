"""
migrate_to_firestore.py
=======================
Safely migrates all SQLite data to Firebase Firestore.

Rules:
  - NEVER modifies or deletes the original SQLite database.
  - Creates a timestamped backup of database.db before anything.
  - Exports each table to separate JSON files in scripts/exports/.
  - Uploads each JSON export as a Firestore collection (one doc per row).
  - Full logging throughout, with error capture.
  - Does NOT connect Firebase to the live frontend.
  - Does NOT replace any SQLite queries in app.py.

Prerequisites:
  pip install firebase-admin
  Place your Firebase service account key JSON at:
    scripts/serviceAccountKey.json
"""

import sqlite3
import json
import os
import sys
import shutil
import logging
from datetime import datetime

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE        = os.path.join(BASE_DIR, 'database.db')
SCRIPTS_DIR     = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR      = os.path.join(SCRIPTS_DIR, 'exports')
BACKUP_DIR      = os.path.join(SCRIPTS_DIR, 'backups')
SERVICE_KEY     = os.path.join(SCRIPTS_DIR, 'serviceAccountKey.json')
LOG_FILE        = os.path.join(SCRIPTS_DIR, 'migration.log')

# Tables to SKIP (SQLite internals)
SKIP_TABLES = {'sqlite_sequence'}

# ──────────────────────────────────────────────
# LOGGING SETUP
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  [%(levelname)s]  %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# STEP 1 — BACKUP DATABASE
# ──────────────────────────────────────────────
def backup_database():
    """Creates a timestamped copy of database.db. NEVER touches the original."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'database_backup_{timestamp}.db')

    log.info("=" * 60)
    log.info("STEP 1 — Creating database backup")
    log.info(f"  Source : {DATABASE}")
    log.info(f"  Backup : {backup_path}")

    if not os.path.exists(DATABASE):
        log.error("  [FAIL] database.db not found. Aborting.")
        sys.exit(1)

    shutil.copy2(DATABASE, backup_path)
    backup_size = os.path.getsize(backup_path)
    log.info(f"  [OK] Backup created ({backup_size} bytes)")
    return backup_path

# ──────────────────────────────────────────────
# STEP 2 — EXPORT TABLES TO JSON
# ──────────────────────────────────────────────
def serialize_value(val):
    """Converts SQLite values to JSON-safe Python types."""
    if val is None:
        return None
    if isinstance(val, (int, float, bool)):
        return val
    if isinstance(val, str):
        # Try to detect JSON-encoded strings (progress_json, passed_sections, etc.)
        if val.strip().startswith(('{', '[', '"')):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, ValueError):
                pass
        return val
    return str(val)


def export_tables():
    """Exports every non-system table from SQLite to individual JSON files."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    log.info("=" * 60)
    log.info("STEP 2 — Exporting tables to JSON")

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    export_summary = {}  # {table_name: row_count}

    for table in tables:
        if table in SKIP_TABLES:
            log.info(f"  Skipping system table: {table}")
            continue

        cursor.execute(f"SELECT * FROM [{table}]")
        rows = cursor.fetchall()

        # Convert rows → list of dicts with proper types
        records = []
        null_count = 0
        error_count = 0

        for row in rows:
            record = {}
            valid = True
            for key in row.keys():
                try:
                    record[key] = serialize_value(row[key])
                    if row[key] is None:
                        null_count += 1
                except Exception as e:
                    log.warning(f"  [WARN] Could not convert field '{key}' in table '{table}': {e}")
                    record[key] = None
                    error_count += 1
                    valid = False
            records.append(record)

        # Write JSON export
        export_path = os.path.join(EXPORT_DIR, f'{table}.json')
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2, default=str)

        export_summary[table] = len(records)
        log.info(f"  [{table}]")
        log.info(f"    → Rows exported : {len(records)}")
        log.info(f"    → Null values   : {null_count}")
        log.info(f"    → Convert errors: {error_count}")
        log.info(f"    → File          : {export_path}")

    conn.close()
    log.info("  [OK] JSON export complete")
    return export_summary

# ──────────────────────────────────────────────
# STEP 3 — VERIFY JSON STRUCTURE
# ──────────────────────────────────────────────
def verify_json_exports(export_summary):
    """Re-reads each JSON file and verifies structure integrity."""
    log.info("=" * 60)
    log.info("STEP 3 — Verifying JSON structure")

    all_ok = True
    for table, expected_count in export_summary.items():
        export_path = os.path.join(EXPORT_DIR, f'{table}.json')
        if not os.path.exists(export_path):
            log.error(f"  [FAIL] Missing file: {export_path}")
            all_ok = False
            continue

        with open(export_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        actual_count = len(data)
        if actual_count != expected_count:
            log.error(f"  [FAIL] {table}: expected {expected_count}, got {actual_count} records")
            all_ok = False
        else:
            # Check first record has keys
            if data and not isinstance(data[0], dict):
                log.error(f"  [FAIL] {table}: first record is not a dict")
                all_ok = False
            else:
                log.info(f"  [OK] {table}: {actual_count} records, structure valid")

    if all_ok:
        log.info("  [OK] All JSON files verified successfully")
    else:
        log.error("  [FAIL] Some JSON files have issues. Review logs before uploading.")
    return all_ok

# ──────────────────────────────────────────────
# STEP 4 — UPLOAD TO FIRESTORE (REST API)
# ──────────────────────────────────────────────
def upload_to_firestore_rest(export_summary):
    """
    Uploads each JSON export to Firestore using the REST API.
    Does NOT require a service account key if rules allow API key access.
    """
    log.info("=" * 60)
    log.info("STEP 4 — Uploading to Firebase Firestore (REST API)")

    import requests

    API_KEY    = "AIzaSyBU91sJqU8NTwalzr--BxzpJukpyWVLq-E"
    PROJECT_ID = "ai-carrier-consulting-system"
    BASE_URL   = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"

    def to_firestore_value(val):
        """Converts a Python value to Firestore REST API format."""
        if val is None:
            return {"nullValue": None}
        if isinstance(val, bool):
            return {"booleanValue": val}
        if isinstance(val, int):
            return {"integerValue": str(val)}
        if isinstance(val, float):
            return {"doubleValue": val}
        if isinstance(val, str):
            return {"stringValue": val}
        if isinstance(val, list):
            return {"arrayValue": {"values": [to_firestore_value(x) for x in val]}}
        if isinstance(val, dict):
            return {"mapValue": {"fields": {k: to_firestore_value(v) for k, v in val.items()}}}
        return {"stringValue": str(val)}

    upload_summary = {} 
    total_uploaded = 0
    total_errors   = 0

    for table in export_summary:
        export_path = os.path.join(EXPORT_DIR, f'{table}.json')
        if not os.path.exists(export_path):
            continue

        with open(export_path, 'r', encoding='utf-8') as f:
            records = json.load(f)

        uploaded = 0
        errors   = 0
        log.info(f"  Uploading [{table}] -> Firestore collection '{table}' ({len(records)} documents)...")

        for record in records:
            # Use SQLite 'id' if available
            doc_id = str(record.get('id', '')) if record.get('id') is not None else ""
            
            # Prepare fields
            fields = {k: to_firestore_value(v) for k, v in record.items()}
            payload = {"fields": fields}

            # If doc_id exists, use it in the path
            if doc_id:
                url = f"{BASE_URL}/{table}/{doc_id}?key={API_KEY}"
                method = requests.patch  # Use patch (upsert) for doc_id
            else:
                url = f"{BASE_URL}/{table}?key={API_KEY}"
                method = requests.post  # Use post for auto-generated ID

            try:
                # Patch requires updateMask for fields if updating existing docs
                if method == requests.patch:
                    # Simplify: just overwrite everything for migration
                    params = {"key": API_KEY}
                    # For patch, the fields are top level in the document
                    response = method(url, json=payload, timeout=10)
                else:
                    response = method(url, json=payload, timeout=10)

                if response.status_code in [200, 201]:
                    uploaded += 1
                else:
                    log.warning(f"    [WARN] Failed record {doc_id}: {response.text}")
                    errors += 1
            except Exception as e:
                log.error(f"    [ERROR] Request failed: {e}")
                errors += 1

        upload_summary[table] = {"uploaded": uploaded, "errors": errors}
        total_uploaded += uploaded
        total_errors   += errors
        log.info(f"  [{table}] Done — Uploaded: {uploaded}, Errors: {errors}")

    return upload_summary, total_uploaded, total_errors

# ──────────────────────────────────────────────
# STEP 5 — VERIFY & COMPARE COUNTS
# ──────────────────────────────────────────────
def verify_migration(export_summary, upload_summary):
    """Compares SQLite row counts vs Firestore upload counts."""
    log.info("=" * 60)
    log.info("STEP 5 — Verification: SQLite vs Firestore record counts")
    log.info(f"  {'Table':<20} {'SQLite Rows':<15} {'Uploaded':<12} {'Errors':<10} {'Match?'}")
    log.info(f"  {'-'*70}")

    all_match = True
    for table, sqlite_count in export_summary.items():
        info = upload_summary.get(table, {"uploaded": 0, "errors": 0})
        uploaded = info["uploaded"]
        errors   = info["errors"]
        match    = "[OK] YES" if uploaded == sqlite_count and errors == 0 else "[FAIL] NO"
        if match != "[OK] YES":
            all_match = False
        log.info(f"  {table:<20} {sqlite_count:<15} {uploaded:<12} {errors:<10} {match}")

    log.info(f"  {'-'*70}")
    return all_match

# ──────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────
def main():
    log.info("\n" + "=" * 60)
    log.info("  SQLITE → FIRESTORE MIGRATION (REST API)")
    log.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 60)

    # STEP 1
    backup_path = backup_database()

    # STEP 2
    export_summary = export_tables()

    # STEP 3
    json_ok = verify_json_exports(export_summary)
    if not json_ok:
        log.error("\n[ABORT] JSON verification failed. Fix issues before uploading.")
        sys.exit(1)

    # STEP 4 (REST API VERSION)
    upload_summary, total_up, total_err = upload_to_firestore_rest(export_summary)

    # STEP 5
    all_match = verify_migration(export_summary, upload_summary)

    log.info("=" * 60)
    if all_match:
        log.info("  MIGRATION STATUS : [OK] SUCCESS")
        log.info("  All SQLite records are now in Firestore.")
        log.info("  Original SQLite database is UNTOUCHED.")
        log.info("  Backup saved at: " + backup_path)
    else:
        log.warning("  MIGRATION STATUS : [WARN] PARTIAL")
        log.warning("  Review migration.log for mismatches.")
    log.info("=" * 60 + "\n")


if __name__ == '__main__':
    main()
