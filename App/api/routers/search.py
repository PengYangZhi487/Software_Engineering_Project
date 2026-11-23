"""全局搜索：一次搜需求 / 用例 / 质量问题。

GET /api/projects/{project_id}/search?q=xxx

搜索在内存里做（数据量小、规则与页面一致）：需求按编号/标题/描述，
用例按编号/标题/预期/步骤/关联需求，质量问题按标题/说明/编号/命中词。
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from App.api import repository
from App.api.routers.cases import _to_out as _case_out
from App.api.routers.requirements import _to_out as _req_out
from App.api.schemas import QualityIssue, SearchOut
from App.services import req_service
from App.services.quality_scan import scan_requirements

router = APIRouter(prefix="/api", tags=["search"])


def _hit(keyword: str, *parts: object) -> bool:
    kw = keyword.lower()
    return any(kw in str(part or "").lower() for part in parts)


@router.get(
    "/projects/{project_id}/search",
    response_model=SearchOut,
    summary="全局搜索（需求 / 用例 / 质量问题）",
)
def search(
    project_id: int,
    q: str = Query(..., min_length=1, description="搜索词"),
    limit: int = 50,
) -> SearchOut:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    keyword = q.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="搜索词不能为空")

    requirements = req_service.get_requirements(project_id)
    hit_reqs = [
        r for r in requirements
        if _hit(keyword, r["req_id"], r["title"], r["description"])
    ][:limit]

    cases = repository.list_cases(project_id)
    hit_cases = [
        c for c in cases
        if _hit(
            keyword,
            c.get("tc_id"),
            c.get("title"),
            c.get("expected_result"),
            c.get("req_id"),
            " ".join(c.get("steps") or []),
            " ".join(c.get("preconditions") or []),
        )
    ][:limit]

    issues = scan_requirements(requirements)
    decisions = repository.get_quality_decisions(project_id)
    for issue in issues:
        issue["decision"] = decisions.get(issue["fingerprint"], "open")
    hit_issues = [
        i for i in issues
        if _hit(keyword, i["title"], i["detail"], " ".join(i["req_ids"]), " ".join(i["words"]))
    ][:limit]

    return SearchOut(
        query=keyword,
        requirements=[_req_out(r) for r in hit_reqs],
        cases=[_case_out(c) for c in hit_cases],
        quality=[QualityIssue(**i) for i in hit_issues],
        total=len(hit_reqs) + len(hit_cases) + len(hit_issues),
    )
