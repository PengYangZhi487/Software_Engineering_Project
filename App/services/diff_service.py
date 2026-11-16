"""P7：两版文档的段落级比对。

用 difflib.SequenceMatcher 对「段落原文」做精确比对，输出：
- changed：同一位置的段落被改写（数字/描述变化最常见）
- added / removed：整段新增或删除

只做确定性比对，不做语义判断；「是否真的需要改用例」由人确认。
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable


def _texts(paragraphs: Iterable[dict]) -> list[str]:
    return [p.get("raw") or "" for p in paragraphs]


def diff_paragraphs(base: list[dict], target: list[dict]) -> list[dict]:
    """返回变更列表（按文档顺序）。"""
    base_texts = _texts(base)
    target_texts = _texts(target)

    matcher = SequenceMatcher(None, base_texts, target_texts, autojunk=False)
    changes: list[dict] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        if tag == "replace":
            paired = min(i2 - i1, j2 - j1)
            for k in range(paired):
                changes.append(
                    {
                        "kind": "changed",
                        "base_para": base[i1 + k].get("para_no"),
                        "target_para": target[j1 + k].get("para_no"),
                        "base_text": base_texts[i1 + k],
                        "target_text": target_texts[j1 + k],
                    }
                )
            for i in range(i1 + paired, i2):
                changes.append(
                    {
                        "kind": "removed",
                        "base_para": base[i].get("para_no"),
                        "target_para": None,
                        "base_text": base_texts[i],
                        "target_text": "",
                    }
                )
            for j in range(j1 + paired, j2):
                changes.append(
                    {
                        "kind": "added",
                        "base_para": None,
                        "target_para": target[j].get("para_no"),
                        "base_text": "",
                        "target_text": target_texts[j],
                    }
                )
        elif tag == "delete":
            for i in range(i1, i2):
                changes.append(
                    {
                        "kind": "removed",
                        "base_para": base[i].get("para_no"),
                        "target_para": None,
                        "base_text": base_texts[i],
                        "target_text": "",
                    }
                )
        elif tag == "insert":
            for j in range(j1, j2):
                changes.append(
                    {
                        "kind": "added",
                        "base_para": None,
                        "target_para": target[j].get("para_no"),
                        "base_text": "",
                        "target_text": target_texts[j],
                    }
                )

    return changes


def changed_numbers(base_text: str, target_text: str) -> tuple[list[str], list[str]]:
    """抽出两段里的数字，方便前端标出「哪里变了」。"""
    import re

    base_nums = re.findall(r"\d+(?:\.\d+)?", base_text)
    target_nums = re.findall(r"\d+(?:\.\d+)?", target_text)
    removed = [n for n in base_nums if n not in target_nums]
    added = [n for n in target_nums if n not in base_nums]
    return removed, added
