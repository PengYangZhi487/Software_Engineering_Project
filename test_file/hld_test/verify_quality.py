# test_file/hld_test/verify_quality.py
import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# 让 LLM 相关日志别太吵，只关注业务日志
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

from App.services import (
    parse_docx,
    extract_requirements,
    check_ambiguous,
    locate_requirement,
)

DATASET = PROJECT_ROOT / "test_file" / "datasets" / "course_selection_v1.docx"

# SRS 5.4 声明的"模糊需求 6 条"
EXPECTED_AMBIGUOUS = {f"CR-{i:03d}" for i in range(15, 21)}


def main() -> int:
    if not DATASET.exists():
        print(f"数据集不存在: {DATASET}")
        return 1

    text, para_index = parse_docx(str(DATASET))
    print(f"[doc] 段落数: {len(para_index)}  文本长度: {len(text)}")

    result = extract_requirements(text)
    if result is None:
        print("LLM 提取失败")
        return 1
    reqs = [r.model_dump() for r in result.requirements]
    print(f"[llm] 提取 {len(reqs)} 条需求\n")

    # ---------------- FR-3.3 模糊词检查 ----------------
    print("=" * 50)
    print("FR-3.3 模糊词检查")
    print("=" * 50)
    hits_by_req: dict = {}
    for r in reqs:
        blob = f"{r.get('title') or ''} {r.get('description') or ''}".strip()
        hits = check_ambiguous(blob)
        if hits:
            hits_by_req[r["req_id"]] = [h["word"] for h in hits]
            print(f"  {r['req_id']:<8} {r['title']:<14} → {hits_by_req[r['req_id']]}")

    hit_ids = set(hits_by_req.keys())
    print(f"\n命中需求 {len(hit_ids)} 条；SRS 预期 {len(EXPECTED_AMBIGUOUS)} 条 (CR-015~CR-020)")

    missing = EXPECTED_AMBIGUOUS - hit_ids
    extra = hit_ids - EXPECTED_AMBIGUOUS
    if missing:
        print(f"  ⚠ 漏检: {sorted(missing)}")
    if extra:
        print(f"  ⚠ 多检: {sorted(extra)}（可能是词库过宽，需调词库）")
    if not missing and not extra:
        print("  ✅ 模糊词命中与 SRS 完全一致")

    # ---------------- FR-3.1 段落定位 ----------------
    print("\n" + "=" * 50)
    print("FR-3.1 段落定位 (source_location)")
    print("=" * 50)
    ok = 0
    for r in reqs:
        loc = (
            locate_requirement(r.get("description", ""), para_index)
            or locate_requirement(r.get("title", ""), para_index)
        )
        if loc:
            ok += 1
            # 只打印首尾两条做示例
            if r["req_id"] in ("CR-001", "CR-025"):
                print(f"  {r['req_id']} → para_no={loc['para_no']} ratio={loc['ratio']}")
        else:
            print(f"  {r['req_id']} 未匹配 ⚠")

    print(f"\n定位成功 {ok}/{len(reqs)} 条")
    if ok == len(reqs):
        print("  ✅ 全部定位成功，source_location 可落库")

    return 0


if __name__ == "__main__":
    sys.exit(main())