"""
Quick inspection script for the menu_items table.

Usage:
  python tools/inspect_menu_items_table.py
"""

from pathlib import Path
import sys

# Ensure repo root is on sys.path when running as a script from /tools.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.db_tool import DataBaseConnection


def main() -> None:
    with DataBaseConnection() as db:
        db.cursor.execute("SELECT COUNT(*) AS c FROM menu_items")
        total = db.cursor.fetchone()["c"]
        print(f"TOTAL_ROWS: {total}")

        db.cursor.execute(
            """
            SELECT category, COUNT(*) AS c
            FROM menu_items
            GROUP BY category
            ORDER BY c DESC, category
            """
        )
        print("\nCATEGORIES:")
        for r in db.cursor.fetchall():
            print(f"- {r['category']}: {r['c']}")

        db.cursor.execute(
            """
            SELECT spice_level, COUNT(*) AS c
            FROM menu_items
            GROUP BY spice_level
            ORDER BY spice_level
            """
        )
        print("\nSPICE_LEVELS:")
        for r in db.cursor.fetchall():
            print(f"- {r['spice_level']}: {r['c']}")

        db.cursor.execute(
            """
            SELECT is_vegetarian, COUNT(*) AS c
            FROM menu_items
            GROUP BY is_vegetarian
            ORDER BY is_vegetarian
            """
        )
        print("\nIS_VEGETARIAN:")
        for r in db.cursor.fetchall():
            print(f"- {r['is_vegetarian']}: {r['c']}")


if __name__ == "__main__":
    main()

