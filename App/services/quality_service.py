# App/services/quality_service.py
"""
需求质量检查：模糊词扫描（FR-3.3）。
纯函数，不依赖 DB / LLM，可独立单测。
"""
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 默认模糊词库。后续可外置到 config/ambiguous_words.json 或 DB 配置表。
DEFAULT_AMBIGUOUS_WORDS: List[str] = [
    # 性能类
    "快速", "高效", "及时", "尽快", "明显",
    # 质量类
    "良好", "友好", "美观", "便捷", "稳定",
    # 程度类
    "合理", "尽量", "适度", "充分", "适当",
    # 兼容 SRS 附录里出现的"明显等待"等
    "无卡顿", "无延迟",
]


def check_ambiguous(
    text: str,
    words: Optional[List[str]] = None,
) -> List[Dict]:
    """
    扫描文本中的模糊词，返回 [{word, start, end}]，按 start 升序。
    不修改原文，只定位，方便前端高亮。
    """
    if not text:
        return []
    words = words if words is not None else DEFAULT_AMBIGUOUS_WORDS
    hits: List[Dict] = []
    for w in words:
        if not w:
            continue
        for m in re.finditer(re.escape(w), text):
            hits.append({"word": w, "start": m.start(), "end": m.end()})
    hits.sort(key=lambda x: x["start"])
    return hits


def check_requirements(
    requirements: List[Dict],
    words: Optional[List[str]] = None,
) -> Dict[str, List[Dict]]:
    """
    批量扫描。
    入参: [{"req_id": "CR-015", "title": "...", "description": "..."}]
    出参: {"CR-015": [{"word": "快速", ...}], ...}，只返回有命中的需求。
    """
    result: Dict[str, List[Dict]] = {}
    for req in requirements:
        rid = req.get("req_id") or "<unknown>"
        blob = " ".join(
            str(req.get(k) or "") for k in ("title", "description")
        ).strip()
        hits = check_ambiguous(blob, words)
        if hits:
            result[rid] = hits
            logger.info("%s 命中模糊词: %s", rid, [h["word"] for h in hits])
    return result


def has_ambiguous(text: str, words: Optional[List[str]] = None) -> bool:
    """快速判断是否含模糊词，适合做 is_ambiguous 字段的标记。"""
    return bool(check_ambiguous(text, words))


# 追加到 App/services/quality_service.py
def dedup_words(hits: List[Dict]) -> List[str]:
    """提取命中的词（去重，保持首次出现顺序），用于展示。"""
    seen, out = set(), []
    for h in hits:
        w = h["word"]
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out