"""
将菜单检索到的原始拼接串转成「给顾客看」的提示上下文（去掉内部菜品 ID）。

入库格式示例：菜品ID:5|菜品名称:xxx|价格:¥...
向量检索仍会携带完整文本；仅在进入 LLM 提示词前做裁剪，不影响 menu_ids 与其它逻辑。
"""

from __future__ import annotations

import re
from typing import List


_LEADING_ID_PATTERN = re.compile(r"^菜品ID:\d+\|")


def sanitize_menu_line_for_prompt(raw_line: str) -> str:
    """去掉行首「菜品ID:数字|」，保留菜品名称及后续可读字段。"""
    if not raw_line:
        return ""
    line = raw_line.strip()
    line = _LEADING_ID_PATTERN.sub("", line, count=1)
    return line


def sanitize_menu_contents_for_prompt(contents: List[str]) -> List[str]:
    """批量清洗检索到的菜品块，用于拼进 LLM user 侧上下文。"""
    out = []
    for item in contents or []:
        cleaned = sanitize_menu_line_for_prompt(item)
        if cleaned:
            out.append(cleaned)
    return out
