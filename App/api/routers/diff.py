"""P7：两版文档比对 + 受影响用例。

GET /api/projects/{project_id}/document-diff?base_doc_id=&target_doc_id=

- 不传 id 时：target = 最新文档，base = 次新文档
- 比对是段落级精确比对（difflib），不做语义判断
- 影响分析分两层：
    关联影响：变更段落对应的需求 → 这些需求下挂的用例（自动列出）
    实际影响：用例是否真的需要改，由人复核（页面只给提示，不自动判定）
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from App.api import repository
from App.api.schemas import DiffCase, DiffChange, DiffOut, DiffSummary
from App.services import req_service
from App.services.diff_service import changed_numbers, diff_paragraphs

router = APIRouter(prefix="/api", tags=["diff"])


@router.get(
    "/projects/{project_id}/document-diff",
    response_model=DiffOut,
    summary="两版文档比对与受影响用例",
)
def document_diff(
    project_id: int,
    base_doc_id: int | None = Query(None, description="旧版本，默认次新文档"),
    target_doc_id: int | None = Query(None, description="新版本，默认最新文档"),
) -> DiffOut:
    if repository.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    docs = repository.list_documents(project_id)  # 按 doc_id 倒序
    if len(docs) < 2:
        raise HTTPException(
            status_code=400,
            detail="至少需要两个版本的文档才能比对，请先上传新版本",
        )

    base_id = base_doc_id or docs[1].doc_id
    target_id = target_doc_id or docs[0].doc_id
    if base_id == target_id:
        raise HTTPException(status_code=400, detail="base 与 target 不能是同一份文档")

    base_meta = repository.get_document(base_id)
    target_meta = repository.get_document(target_id)
    if base_meta is None or target_meta is None:
        raise HTTPException(status_code=404, detail="指定的文档不存在")
    if base_meta.project_id != project_id or target_meta.project_id != project_id:
        raise HTTPException(status_code=400, detail="文档不属于该项目")

    base_src = repository.get_document_source(base_id)
    target_src = repository.get_document_source(target_id)
    if base_src is None or target_src is None:  # pragma: no cover
        raise HTTPException(status_code=404, detail="文档内容缺失")

    raw_changes = diff_paragraphs(base_src[1], target_src[1])

    requirements = req_service.get_requirements(project_id)

    def para_to_reqs(doc_id: int, include_unassigned: bool = False) -> dict[int, list[str]]:
        mapping: dict[int, list[str]] = {}
        for req in requirements:
            owner = req.get("doc_id")
            # 老数据里 requirements 可能没有 doc_id（早期直接灌库），按「属于旧版本」处理
            if owner != doc_id and not (include_unassigned and owner is None):
                continue
            location = req.get("source_location") or {}
            para_no = location.get("para_no")
            if para_no is None:
                continue
            mapping.setdefault(int(para_no), []).append(req["req_id"])
        return mapping

    base_map = para_to_reqs(base_id, include_unassigned=True)
    target_map = para_to_reqs(target_id)

    cases_by_req: dict[str, list[dict]] = {}
    for case in repository.list_cases(project_id):
        cases_by_req.setdefault(case.get("req_id") or "", []).append(case)

    changes: list[DiffChange] = []
    affected_req_ids: set[str] = set()
    affected_case_ids: set[int] = set()

    for index, item in enumerate(raw_changes, start=1):
        req_ids: list[str] = []
        if item["base_para"] is not None:
            req_ids.extend(base_map.get(int(item["base_para"]), []))
        if item["target_para"] is not None:
            req_ids.extend(target_map.get(int(item["target_para"]), []))
        req_ids = list(dict.fromkeys(req_ids))

        cases: list[DiffCase] = []
        for req_id in req_ids:
            for case in cases_by_req.get(req_id, []):
                cases.append(
                    DiffCase(
                        tc_id=int(case["tc_id"]),
                        title=case["title"],
                        req_id=case.get("req_id"),
                        status=case["status"],
                        test_type=case["test_type"],
                    )
                )
                affected_case_ids.add(int(case["tc_id"]))
        affected_req_ids.update(req_ids)

        removed_numbers, added_numbers = changed_numbers(item["base_text"], item["target_text"])

        changes.append(
            DiffChange(
                change_id=f"C-{index:03d}",
                kind=item["kind"],
                base_para=item["base_para"],
                target_para=item["target_para"],
                base_text=item["base_text"],
                target_text=item["target_text"],
                removed_numbers=removed_numbers,
                added_numbers=added_numbers,
                req_ids=req_ids,
                cases=cases,
            )
        )

    summary = DiffSummary(
        added=sum(1 for c in changes if c.kind == "added"),
        removed=sum(1 for c in changes if c.kind == "removed"),
        changed=sum(1 for c in changes if c.kind == "changed"),
        affected_requirements=len(affected_req_ids),
        affected_cases=len(affected_case_ids),
    )

    return DiffOut(base=base_meta, target=target_meta, summary=summary, changes=changes)
