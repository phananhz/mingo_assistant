from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class IndustryNode:
    code: str
    name: str
    detail: str = ""
    children: list["IndustryNode"] = field(default_factory=list)


@dataclass(frozen=True)
class IndustryRow:
    levels: list[str]
    name: str
    detail: str = ""

    @property
    def included_detail(self) -> str:
        """Return the official scope text before the exclusion section."""
        return self.detail.split("Loại trừ:", 1)[0].strip()

    @property
    def excluded_detail(self) -> str:
        """Return the official exclusion text, when the source provides it."""
        parts = self.detail.split("Loại trừ:", 1)
        return parts[1].strip() if len(parts) == 2 else ""


@dataclass(frozen=True)
class IndustryCatalog:
    source_path: Path | None
    nodes: list[IndustryNode]
    source_title: str = "Hệ thống ngành kinh tế Việt Nam 2025"
    display_rows: list[IndustryRow] = field(default_factory=list)

    @property
    def is_available(self) -> bool:
        return bool(self.nodes)

    @classmethod
    def load_from_project(cls, project_root: Path) -> "IndustryCatalog":
        candidates = [
            project_root / "assets" / "business_lines" / "vsic_2025.json",
            project_root / "assets" / "reference" / "business_lines" / "vsic_2025.json",
            project_root / "data" / "reference" / "business_lines" / "vsic_2025.json",
        ]
        for candidate in candidates:
            if not candidate.exists():
                continue
            with candidate.open("r", encoding="utf-8-sig") as file:
                payload = json.load(file)
            return cls(
                source_path=candidate,
                source_title=str(payload.get("source_title") or cls.source_title),
                nodes=[cls._node_from_dict(item) for item in payload.get("items", []) if isinstance(item, dict)],
                display_rows=[
                    cls._row_from_dict(item)
                    for item in payload.get("display_rows", []) or []
                    if isinstance(item, dict)
                ],
            )
        return cls(source_path=None, nodes=[])

    @classmethod
    def _node_from_dict(cls, item: dict[str, object]) -> IndustryNode:
        return IndustryNode(
            code=str(item.get("code", "")).strip(),
            name=str(item.get("name", "")).strip(),
            detail=str(item.get("detail", "")).strip(),
            children=[
                cls._node_from_dict(child)
                for child in item.get("children", []) or []
                if isinstance(child, dict)
            ],
        )

    @classmethod
    def _row_from_dict(cls, item: dict[str, object]) -> IndustryRow:
        raw_levels = item.get("levels", [])
        levels = [str(value).strip() for value in raw_levels] if isinstance(raw_levels, list) else []
        return IndustryRow(
            levels=[*levels[:5], "", "", "", "", ""][:5],
            name=str(item.get("name", "")).strip(),
            detail=str(item.get("detail", "")).strip(),
        )

    def filter_rows(self, query: str) -> list[IndustryRow]:
        rows = self.display_rows or self._rows_from_nodes(self.nodes)
        folded_query = self._fold(query)
        if not folded_query:
            return rows
        return [
            row
            for row in rows
            if folded_query in self._fold(" ".join([*row.levels, row.name, row.detail]))
        ]

    def filter(self, query: str) -> list[IndustryNode]:
        folded_query = self._fold(query)
        if not folded_query:
            return self.nodes
        return [node for node in (self._filter_node(node, folded_query) for node in self.nodes) if node]

    def _filter_node(self, node: IndustryNode, folded_query: str) -> IndustryNode | None:
        children = [child for child in (self._filter_node(child, folded_query) for child in node.children) if child]
        haystack = self._fold(f"{node.code} {node.name} {node.detail}")
        if folded_query in haystack or children:
            return IndustryNode(node.code, node.name, node.detail, children)
        return None

    def _rows_from_nodes(self, nodes: list[IndustryNode]) -> list[IndustryRow]:
        rows: list[IndustryRow] = []
        for node in nodes:
            rows.extend(self._node_rows(node, 1))
        return rows

    def _node_rows(self, node: IndustryNode, level: int) -> list[IndustryRow]:
        levels = ["", "", "", "", ""]
        levels[min(level, 5) - 1] = node.code
        rows = [IndustryRow(levels, node.name, node.detail)]
        for child in node.children:
            rows.extend(self._node_rows(child, level + 1))
        return rows

    def _fold(self, value: str) -> str:
        text = unicodedata.normalize("NFD", value.strip().lower().replace("đ", "d"))
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        return " ".join(text.split())
