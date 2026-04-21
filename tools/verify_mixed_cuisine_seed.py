"""
Verify the seeded '混合菜系' dishes in table `menu_items`.

Usage:
  python tools/verify_mixed_cuisine_seed.py
"""

from pathlib import Path
import sys
import json

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.db_tool import DataBaseConnection


def main() -> None:
    with DataBaseConnection() as db:
        db.cursor.execute("SELECT COUNT(*) AS c FROM menu_items WHERE category=%s", ("混合菜系",))
        c = db.cursor.fetchone()["c"]
        print(f"MIXED_COUNT: {c}")

        db.cursor.execute(
            """
            SELECT
              id, dish_name, price, description, category,
              spice_level, flavor, main_ingredients, cooking_method,
              is_vegetarian, allergens, is_available, created_at, updated_at
            FROM menu_items
            WHERE category=%s
            ORDER BY id
            LIMIT 3
            """,
            ("混合菜系",),
        )
        rows = db.cursor.fetchall()
        print(json.dumps(rows, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()

