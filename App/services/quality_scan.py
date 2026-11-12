"""P4：确定性的需求质量扫描（规则引擎）。

原则：只做能稳定复现、可解释的检查。
- 模糊表达：词表命中（与 quality_service 同一套词）
- 缺验收条件 / 缺描述
- 数值口径冲突：同一主题下出现不同数字（门数、容量、退课周数）
- 相反表述冲突：同一主题同时存在「不可 / 不得」与「可 / 允许」

更复杂的语义冲突、重复需求识别留到二期，由人做最终判断。
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from App.services.quality_service import check_ambiguous, dedup_words

NUMERIC_RULES: list[dict[str, Any]] = [
    {"id": "max_courses", "label": "选课门数", "keywords": ("门",), "pattern": r"(\d+)\s*门",
     "hint": "课程门数上限不一致"},
    {"id": "capacity", "label": "课程容量", "keywords": ("容量", "扩容", "人数"), "pattern": r"(\d+)\s*人",
     "hint": "课程容量口径不一致"},
    {"id": "withdraw_window", "label": "退课时限", "keywords": ("退课",), "pattern": r"(\d+)\s*周",
     "hint": "退课截止时间不一致"},
]

NEGATION_RULES: list[dict[str, Any]] = [
    {"id": "grade_edit", "label": "成绩修改", "topic": "成绩", "verb": "修改"},
]

NEGATIVE_WORDS = ("不可", "不得", "禁止", "不允许")
POSITIVE_WORDS = ("可", "允许")


def _text(row: dict) -> str:
    return f"{row.get('title') or ''} {row.get('description') or ''}"


def scan_requirements(rows: Iterable[dict]) -> list[dict]:
    rows = list(rows)
    issues: list[dict] = []
    seq = 0

    def add(kind: str, severity: str, title: str, detail: str, req_ids: list[str],
            words: list[str] | None = None) -> None:
        nonlocal seq
        seq += 1
        issues.append({
            "issue_id": f"Q-{seq:03d}",
            "kind": kind,
            "severity": severity,
            "title": title,
            "detail": detail,
            "req_ids": req_ids,
            "words": words or [],
        })

    # 1. 模糊表达 / 缺验收 / 缺描述
    for row in rows:
        rid = row.get("req_id", "")
        words = dedup_words(check_ambiguous(_text(row)))
        if words:
            add(
                "ambiguous", "warn",
                f"「{'、'.join(words)}」等表述不可量化",
                f"{rid} 含不可量化的表述，建议补充可验证的指标。",
                [rid], words,
            )
        if not (row.get("acceptance") or []):
            add("missing_acceptance", "warn", "缺少验收条件",
                f"{rid} 没有可验证的验收条件，无法判断是否实现。", [rid])

    # 2. 数值口径冲突
    for rule in NUMERIC_RULES:
        found: list[tuple[int, str, str]] = []
        for row in rows:
            text = _text(row)
            if not any(k in text for k in rule["keywords"]):
                continue
            numbers = [int(x) for x in re.findall(rule["pattern"], text)]
            if numbers:
                found.append((min(numbers), row.get("req_id", ""), row.get("title", "")))
        if len({n for n, _, _ in found}) > 1:
            found.sort()
            detail = "；".join(f"{rid}「{title}」= {n}" for n, rid, title in found)
            add("conflict", "danger", f"{rule['label']}不一致",
                f"{rule['hint']}：{detail}", [rid for _, rid, _ in found])

    # 3. 相反表述冲突
    for rule in NEGATION_RULES:
        topic, verb = rule["topic"], rule["verb"]
        neg = [r for r in rows if topic in _text(r) and verb in _text(r)
               and any(w in _text(r) for w in NEGATIVE_WORDS)]
        pos = [r for r in rows if topic in _text(r) and verb in _text(r)
               and not any(w in _text(r) for w in NEGATIVE_WORDS)
               and any(w in _text(r) for w in POSITIVE_WORDS)]
        if neg and pos:
            involved = neg + pos
            detail = "；".join(f"{r.get('req_id')}「{r.get('title')}」" for r in involved)
            add("conflict", "danger", f"{rule['label']}表述相反",
                f"同时存在禁止与允许两种表述，需要产品方确认：{detail}",
                [r.get("req_id", "") for r in involved])

    return issues
