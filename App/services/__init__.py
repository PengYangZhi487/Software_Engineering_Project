# App/services/__init__.py
"""
Services 层对外入口。
当前导出 llm / doc / quality / locate 四个底层服务。
req / case / track / auth 待接口定型后再加入。
"""
from .llm_service import Requirement, RequirementList, extract_requirements
from .doc_service import parse_docx, parse_txt, parse_document
from .quality_service import check_ambiguous, check_requirements, has_ambiguous
from .locate_service import locate_requirement, enrich_source_location

__all__ = [
    "Requirement", "RequirementList", "extract_requirements",
    "parse_docx", "parse_txt", "parse_document",
    "check_ambiguous", "check_requirements", "has_ambiguous",
    "locate_requirement", "enrich_source_location",
]