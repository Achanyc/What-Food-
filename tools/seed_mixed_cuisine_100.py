"""
Seed 100 "混合菜系" dishes into MySQL table `menu_items`.

It inserts ALL columns explicitly (including id/created_at/updated_at).

Usage:
  python tools/seed_mixed_cuisine_100.py
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Ensure repo root on sys.path when running from /tools.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.db_tool import DataBaseConnection


@dataclass(frozen=True)
class Dish:
    id: int
    dish_name: str
    price: float
    description: str
    category: str
    spice_level: int
    flavor: str
    main_ingredients: str
    cooking_method: str
    is_vegetarian: int
    allergens: str
    is_available: int
    created_at: datetime
    updated_at: datetime


def _pick(rng: random.Random, items: List[str]) -> str:
    return items[rng.randrange(0, len(items))]


def _maybe(rng: random.Random, p: float) -> bool:
    return rng.random() < p


def generate_dishes(start_id: int, n: int, seed: int = 20260421) -> List[Dish]:
    rng = random.Random(seed)
    now = datetime.now()

    proteins = ["鸡胸", "鸡腿", "牛肉", "肥牛", "猪里脊", "五花肉", "虾仁", "鱿鱼", "鱼片", "鸡蛋", "豆腐", "菌菇"]
    vegs = ["青椒", "彩椒", "西兰花", "芦笋", "土豆", "莲藕", "茄子", "番茄", "黄瓜", "娃娃菜", "洋葱", "胡萝卜"]
    carbs = ["米饭", "乌冬面", "意面", "年糕", "粉丝", "馒头片", "手擀面", "藜麦"]
    cuisines = ["川味", "粤式", "鲁味", "湘味", "江浙", "西北", "泰式", "日式", "韩式", "东南亚", "新中式", "Fusion"]
    cooking_methods = ["爆炒", "清炒", "红烧", "炖", "蒸", "煮", "煎", "烤", "焗", "凉拌", "油炸", "干锅"]
    sauces = [
        "黑椒", "蒜蓉", "葱姜", "麻辣", "藤椒", "咖喱", "番茄", "照烧", "泡椒", "酸汤", "蜜汁", "沙茶",
        "芝麻酱", "酸甜", "椒盐", "孜然",
    ]
    flavor_templates = ["{sauce}风味", "{sauce}微辣", "{sauce}麻香", "{sauce}清爽", "{sauce}酸甜", "{sauce}浓香"]
    sides = ["小葱", "香菜", "蒜末", "姜丝", "白芝麻", "花生碎", "小米椒", "青花椒", "酸豆角", "木耳", "玉米粒"]

    allergen_pool = [
        "含花生",
        "含芝麻",
        "含大豆",
        "含蛋",
        "含乳制品",
        "含小麦(麸质)",
        "含鱼类",
        "含贝类",
        "可能含坚果",
    ]

    dishes: List[Dish] = []
    used_names: set[str] = set()

    for i in range(n):
        dish_id = start_id + i
        cuisine = _pick(rng, cuisines)
        method = _pick(rng, cooking_methods)
        sauce = _pick(rng, sauces)

        vegetarian = 1 if _maybe(rng, 0.22) else 0

        if vegetarian:
            main = _pick(rng, ["豆腐", "菌菇", "茄子", "西兰花", "芦笋", "番茄", "土豆", "莲藕"])
            second = _pick(rng, vegs)
        else:
            main = _pick(rng, proteins)
            second = _pick(rng, vegs)

        # Sometimes make it a staple bowl/noodle.
        add_carb = _maybe(rng, 0.26)
        carb = _pick(rng, carbs) if add_carb else ""

        base_name = f"{cuisine}{method}{main}"
        if sauce in ("黑椒", "孜然", "咖喱", "酸汤", "泡椒", "椒盐", "照烧"):
            base_name = f"{sauce}{base_name}"
        if add_carb:
            base_name = f"{base_name}{carb}"

        # Ensure unique name.
        name = base_name
        suffix = 2
        while name in used_names:
            suffix += 1
            name = f"{base_name}{suffix}"
        used_names.add(name)

        spice_level = rng.choices([0, 1, 2, 3], weights=[38, 32, 20, 10], k=1)[0]
        if sauce in ("麻辣", "藤椒", "泡椒") and spice_level == 0:
            spice_level = 1

        flavor = _pick(rng, flavor_templates).format(sauce=sauce)
        if spice_level == 0 and ("辣" in flavor or "麻" in flavor):
            flavor = flavor.replace("微辣", "不辣").replace("麻香", "清香")

        # Ingredients string (comma-separated, consistent with existing data).
        ing = [main, second, _pick(rng, sides)]
        if _maybe(rng, 0.35):
            ing.append(_pick(rng, sides))
        if add_carb:
            ing.append(carb)
        main_ingredients = ",".join(dict.fromkeys(ing))  # preserve order, dedupe

        # Allergens: vegetarian tends to still include soy/sesame; non-veg may include fish/shellfish occasionally.
        allergens: List[str] = []
        if vegetarian:
            if _maybe(rng, 0.55):
                allergens.append("含大豆")
            if _maybe(rng, 0.25):
                allergens.append("含芝麻")
            if _maybe(rng, 0.12):
                allergens.append("含花生")
        else:
            if main in ("虾仁", "鱿鱼"):
                allergens.append("含贝类")
            if main == "鱼片":
                allergens.append("含鱼类")
            if _maybe(rng, 0.22):
                allergens.append("含蛋")
            if _maybe(rng, 0.18):
                allergens.append("含大豆")

        # Random additional allergen note.
        if _maybe(rng, 0.10):
            allergens.append(_pick(rng, allergen_pool))

        allergens_str = ",".join(dict.fromkeys([a for a in allergens if a])) if allergens else ""

        # Price: influenced by protein + method.
        base = 12.0
        if main in ("肥牛", "牛肉"):
            base += 14.0
        elif main in ("虾仁", "鱿鱼", "鱼片"):
            base += 10.0
        elif main in ("五花肉", "猪里脊", "鸡腿"):
            base += 7.0
        elif vegetarian:
            base += 3.0

        if method in ("烤", "焗", "油炸", "干锅"):
            base += 4.0
        if add_carb:
            base += 3.0

        price = round(base + rng.uniform(-2.0, 6.0), 2)
        price = max(8.0, min(price, 88.0))

        # Reasonable description.
        spicy_text = {0: "不辣", 1: "微辣", 2: "中辣", 3: "重辣"}[spice_level]
        desc_bits = [
            f"{cuisine}灵感的{method}做法",
            f"搭配{sauce}调味",
            f"口感层次丰富，{spicy_text}可口",
        ]
        if add_carb:
            desc_bits.append(f"配{carb}更满足")
        if vegetarian:
            desc_bits.append("清爽不腻，素食友好")
        description = "，".join(desc_bits) + "。"

        dishes.append(
            Dish(
                id=dish_id,
                dish_name=name,
                price=price,
                description=description,
                category="混合菜系",
                spice_level=spice_level,
                flavor=flavor,
                main_ingredients=main_ingredients,
                cooking_method=method.replace("清炒", "炒").replace("爆炒", "炒"),
                is_vegetarian=vegetarian,
                allergens=allergens_str,
                is_available=1,
                created_at=now,
                updated_at=now,
            )
        )

    return dishes


def insert_dishes(dishes: List[Dish]) -> int:
    if not dishes:
        return 0

    sql = """
        INSERT INTO menu_items (
            id, dish_name, price, description, category,
            spice_level, flavor, main_ingredients, cooking_method,
            is_vegetarian, allergens, is_available, created_at, updated_at
        )
        VALUES (
            %(id)s, %(dish_name)s, %(price)s, %(description)s, %(category)s,
            %(spice_level)s, %(flavor)s, %(main_ingredients)s, %(cooking_method)s,
            %(is_vegetarian)s, %(allergens)s, %(is_available)s, %(created_at)s, %(updated_at)s
        )
    """

    with DataBaseConnection() as db:
        # Safety: avoid collisions if someone already inserted these ids.
        ids = [d.id for d in dishes]
        db.cursor.execute(
            f"SELECT COUNT(*) AS c FROM menu_items WHERE id BETWEEN {min(ids)} AND {max(ids)}"
        )
        exists = db.cursor.fetchone()["c"]
        if exists:
            raise RuntimeError(
                f"ID range collision detected: {exists} rows already exist in [{min(ids)}, {max(ids)}]."
            )

        payload = [d.__dict__ for d in dishes]
        db.cursor.executemany(sql, payload)
        db.connection.commit()
        return db.cursor.rowcount


def get_next_id() -> int:
    with DataBaseConnection() as db:
        db.cursor.execute("SELECT COALESCE(MAX(id), 0) AS m FROM menu_items")
        return int(db.cursor.fetchone()["m"]) + 1


def main() -> None:
    start_id = get_next_id()
    dishes = generate_dishes(start_id=start_id, n=100)
    inserted = insert_dishes(dishes)
    print(f"Inserted rows: {inserted}")
    print(f"ID range: {dishes[0].id}..{dishes[-1].id}")
    print("Category: 混合菜系")


if __name__ == "__main__":
    main()

