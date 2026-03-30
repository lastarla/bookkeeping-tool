from __future__ import annotations

EXPENSE_CATEGORIES = [
    "餐饮",
    "交通",
    "日用",
    "购物",
    "娱乐",
    "医疗",
    "住房",
    "教育",
    "其他支出",
]

INCOME_CATEGORIES = [
    "工资",
    "报销",
    "转账",
    "退款",
    "理财",
    "其他收入",
]

ALL_CATEGORIES = set(EXPENSE_CATEGORIES + INCOME_CATEGORIES)

DEFAULT_CATEGORY_BY_DIRECTION = {
    "expense": "其他支出",
    "income": "其他收入",
}


def normalize_category(direction: str, category: str | None) -> str:
    normalized = (category or "").strip()
    if normalized in ALL_CATEGORIES:
        return normalized
    return DEFAULT_CATEGORY_BY_DIRECTION[direction]
