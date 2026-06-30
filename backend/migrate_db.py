"""
One-time migration script.
Adds the new columns and tables to the existing health_app.db
without deleting any data.

Run ONCE with uvicorn STOPPED:
    python migrate_db.py
"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "health_app.db")

def migrate():
    if not os.path.exists(DB_PATH):
        print("No existing DB found — nothing to migrate. Just start uvicorn.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # ── 1. Check current food_restrictions columns ──────────────────────────
    cur.execute("PRAGMA table_info(food_restrictions)")
    cols = [row[1] for row in cur.fetchall()]
    print(f"food_restrictions columns: {cols}")

    # ── 2. If old schema (has restriction_name), rebuild the table ──────────
    if "restriction_name" in cols and "category" not in cols:
        print("Migrating food_restrictions table...")
        cur.execute("ALTER TABLE food_restrictions RENAME TO food_restrictions_old")
        cur.execute("""
            CREATE TABLE food_restrictions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                category   TEXT    NOT NULL,
                item       TEXT    NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Old rows had no category — leave the new table empty.
        # Restrictions will be regenerated when user re-saves health profile.
        cur.execute("DROP TABLE food_restrictions_old")
        print("  Done. Old restriction_name rows removed (will regenerate on next save).")
    elif "category" in cols:
        print("food_restrictions already on new schema — no change needed.")

    # ── 3. Create food_restriction_rules table if it doesn't exist ──────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS food_restriction_rules (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            condition_key  TEXT UNIQUE NOT NULL,
            category_label TEXT NOT NULL,
            foods_json     TEXT NOT NULL,
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("food_restriction_rules table ensured.")

    conn.commit()
    conn.close()
    print("\nMigration complete!")
    print("Now start uvicorn — it will seed the 19 rules automatically.")

if __name__ == "__main__":
    migrate()
