# test_file/hld_test/test_services.py
import os
import sys
import logging
from pathlib import Path

# 项目根：test_file/hld_test/test_services.py 往上两级
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# ---- 导入 App.services 下的两个服务 ----
from App.services.llm_service import extract_requirements

try:
    from App.services import doc_service
except Exception as e:
    print(f"[warn] 无法导入 App.services.doc_service: {e}")
    doc_service = None


# 现成的样例文档（在 test_file/Feasibility/ 下，确实存在）
MOCK_DOCX = PROJECT_ROOT / "test_file" / "datasets" / "course_selection_v1.docx"

# 兜底文本：覆盖清晰 / 模糊 / 矛盾各一条，方便肉眼校验提取效果
FALLBACK_TEXT = (
    "系统应允许学生在规定时间内选课，并在课程人数达到上限时禁止继续选课。\n"
    "系统应快速响应学生的选课请求。\n"
    "系统界面应友好美观。\n"
    "允许学生每学期选8门课程；同时每学期最多只能选6门课程。\n"
)


def load_test_text() -> str:
    """优先解析 mock_requirements.docx；失败则用内置文本。"""
    if doc_service is None:
        print("[doc] doc_service 不可用，使用内置文本")
        return FALLBACK_TEXT

    if not hasattr(doc_service, "parse_docx"):
        print("[doc] doc_service 里没有 parse_docx，使用内置文本")
        return FALLBACK_TEXT

    if not MOCK_DOCX.exists():
        print(f"[doc] 未找到 {MOCK_DOCX}，使用内置文本")
        return FALLBACK_TEXT

    print(f"[doc] 读取样例文档: {MOCK_DOCX}")
    try:
        text, para_index = doc_service.parse_docx(str(MOCK_DOCX))
        print(f"[doc] 段落数: {len(para_index)}")
        preview = [p.get("raw", "")[:40] for p in para_index[:3]]
        print(f"[doc] 前 3 段预览: {preview}")
        return text
    except Exception as e:
        print(f"[doc] parse_docx 失败，改用内置文本: {e}")
        return FALLBACK_TEXT


def run_llm_test(text: str) -> bool:
    print("\n=== 开始调用 LLM 提取需求 ===")
    result = extract_requirements(text)
    if result is None:
        print("❌ 提取失败（检查 App/.env 里的 DEEPSEEK_API_KEY 与网络）")
        return False
    print(f"✅ 共提取 {len(result.requirements)} 条需求")
    for r in result.requirements:
        print(f"  [{r.req_id}] {r.title} ({r.req_type}) | 验收 {len(r.acceptance_criteria)} 条")
    return True


if __name__ == "__main__":
    print(f"[env] 项目根: {PROJECT_ROOT}")
    text = load_test_text()
    print(f"[text] 待提取文本长度: {len(text)}")
    ok = run_llm_test(text)
    sys.exit(0 if ok else 1)