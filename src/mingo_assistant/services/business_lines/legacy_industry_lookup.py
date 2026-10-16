from __future__ import annotations

import json
from pathlib import Path

from mingo_assistant.services.business_lines.industry_lookup import (
    IndustryCatalog,
    IndustryNode,
    IndustryRow,
)


LEGACY_INDUSTRY_DATASET = "vsic_2018.json"
LEGACY_INDUSTRY_SOURCE_TITLE = (
    "Hệ thống ngành kinh tế Việt Nam 2018 - Quyết định 27/2018/QĐ-TTg"
)

# Deliberately empty. A dossier workflow may use VSIC 2018 only after its
# stable case type is explicitly added here and the workflow is wired to the
# legacy catalog. The standalone lookup page is not governed by this allowlist.
LEGACY_INDUSTRY_LOOKUP_CASE_TYPES: frozenset[str] = frozenset()


def load_legacy_industry_catalog(project_root: Path) -> IndustryCatalog:
    """Load only VSIC 2018 data; never fall back to the current VSIC catalog."""

    candidates = [
        project_root / "assets" / "business_lines" / LEGACY_INDUSTRY_DATASET,
        project_root / "assets" / "reference" / "business_lines" / LEGACY_INDUSTRY_DATASET,
        project_root / "data" / "reference" / "business_lines" / LEGACY_INDUSTRY_DATASET,
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        with candidate.open("r", encoding="utf-8-sig") as file:
            payload = json.load(file)
        return IndustryCatalog(
            source_path=candidate,
            source_title=str(payload.get("source_title") or LEGACY_INDUSTRY_SOURCE_TITLE),
            nodes=[
                _node_from_dict(item)
                for item in payload.get("items", [])
                if isinstance(item, dict)
            ],
            display_rows=[
                _row_from_dict(item)
                for item in payload.get("display_rows", []) or []
                if isinstance(item, dict)
            ],
        )
    return IndustryCatalog(
        source_path=None,
        nodes=[],
        source_title=LEGACY_INDUSTRY_SOURCE_TITLE,
    )


def dossier_can_use_legacy_industry_lookup(case_type: str) -> bool:
    """Return whether a dossier type is explicitly allowed to use VSIC 2018."""

    return case_type.strip() in LEGACY_INDUSTRY_LOOKUP_CASE_TYPES


def _node_from_dict(item: dict[str, object]) -> IndustryNode:
    return IndustryNode(
        code=str(item.get("code", "")).strip(),
        name=str(item.get("name", "")).strip(),
        detail=str(item.get("detail", "")).strip(),
        children=[
            _node_from_dict(child)
            for child in item.get("children", []) or []
            if isinstance(child, dict)
        ],
    )


def _row_from_dict(item: dict[str, object]) -> IndustryRow:
    raw_levels = item.get("levels", [])
    levels = [str(value).strip() for value in raw_levels] if isinstance(raw_levels, list) else []
    return IndustryRow(
        levels=[*levels[:5], "", "", "", "", ""][:5],
        name=str(item.get("name", "")).strip(),
        detail=str(item.get("detail", "")).strip(),
    )
