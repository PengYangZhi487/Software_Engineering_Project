# App/services/locate_service.py
"""
段落定位：为 LLM 提取出的需求反查来源段落的物理位置（FR-3.1 source_location 配套）。
纯函数，只依赖 difflib，可独立单测。
"""
import difflib
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def locate_requirement(
    query: str,
    para_index: List[Dict],
    threshold: float = 0.30,
) -> Optional[Dict]:
    """
    在 para_index 中找与 query 最相似的段落。

    入参:
        query:      需求描述（或标题）
        para_index: [{"para_no": 3, "raw": "CR-001 登录认证"}, ...]
        threshold:  最低相似度门槛，低于它认为"没匹配上"

    返回: {"para_no": ..., "raw": ..., "ratio": ...} 或 None
    """
    if not query or not para_index:
        return None

    best: Optional[Dict] = None
    for p in para_index:
        raw = p.get("raw") or ""
        if not raw:
            continue
        ratio = difflib.SequenceMatcher(None, query, raw).ratio()
        if ratio < threshold:
            continue
        if best is None or ratio > best["ratio"]:
            best = {
                "para_no": p.get("para_no"),
                "raw": raw,
                "ratio": round(ratio, 3),
            }
    return best


def enrich_source_location(
    requirements: List[Dict],
    para_index: List[Dict],
    threshold: float = 0.30,
) -> List[Dict]:
    """
    就地给每条需求补 source_location 字段。
    先按 description 匹配，失败再按 title 匹配；仍失败填 None。

    入参 requirements 结构: [{"req_id": "CR-001", "title": "...", "description": "..."}]
    返回同一列表（已写入 source_location 字段）。
    """
    for req in requirements:
        loc = locate_requirement(req.get("description", ""), para_index, threshold)
        if loc is None and req.get("title"):
            loc = locate_requirement(req["title"], para_index, threshold)
        req["source_location"] = loc

        if loc:
            logger.info(
                "%s → para_no=%s (ratio=%.2f)",
                req.get("req_id"), loc["para_no"], loc["ratio"],
            )
        else:
            logger.warning("%s 未匹配到段落", req.get("req_id"))
    return requirements