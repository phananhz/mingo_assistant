from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from docx import Document


EXPECTED_LEVEL4_COUNT = 464
DEFAULT_SOURCE_PATH = Path("TemplatesBefore/27_2018_QD-TTg_387358.docx")
OUTPUT_PATH = Path("assets/business_lines/vsic_2018.json")
SOURCE_TITLE = "Hệ thống ngành kinh tế Việt Nam 2018 - Quyết định 27/2018/QĐ-TTg"


def main() -> int:
    args = _parse_args()
    if not args.source_docx.exists():
        raise FileNotFoundError(f"Không tìm thấy file nguồn: {args.source_docx}")

    document = Document(str(args.source_docx))
    catalog_rows = _catalog_rows(_find_catalog_table(document))
    details_by_code = _details_by_code(document)
    display_rows = _level4_display_rows(catalog_rows, details_by_code)

    payload = {
        "source_title": SOURCE_TITLE,
        "source_file": str(args.source_docx),
        "official_source_url": "https://vanban.chinhphu.vn/?docid=194154&pageid=27160",
        "scope": "level_4_only",
        "actual_counts": {"4": len(display_rows)},
        "display_rows": display_rows,
        "items": [
            {
                "code": row["levels"][3],
                "name": row["name"],
                "detail": row["detail"],
                "children": [],
            }
            for row in display_rows
        ],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {OUTPUT_PATH}")
    print(f"level 4: {len(display_rows)}")
    print(f"with direct detail: {sum(bool(row['detail']) for row in display_rows)}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import level-4 VSIC 2018 business lines from Decision 27/2018/QD-TTg DOCX."
    )
    parser.add_argument(
        "source_docx",
        nargs="?",
        type=Path,
        default=DEFAULT_SOURCE_PATH,
        help=f"Path to the Decision 27/2018 DOCX. Default: {DEFAULT_SOURCE_PATH}",
    )
    return parser.parse_args()


def _find_catalog_table(document: Document):
    expected_header = ["Cấp 1", "Cấp 2", "Cấp 3", "Cấp 4", "Cấp 5", "Tên ngành"]
    for table in document.tables:
        if not table.rows:
            continue
        header = [_clean(cell.text) for cell in table.rows[0].cells]
        if header[:6] == expected_header:
            return table
    raise RuntimeError("Không tìm thấy bảng danh mục ngành kinh tế 6 cột trong file DOCX.")


def _catalog_rows(table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_number, row in enumerate(table.rows[1:], start=2):
        cells = [_clean(cell.text) for cell in row.cells][:6]
        if not any(cells) or _is_header_row(cells) or _is_total_row(cells):
            continue
        if not cells[5]:
            raise RuntimeError(f"Dòng {row_number} thiếu tên ngành: {cells}")
        rows.append(cells)
    return rows


def _level4_display_rows(
    catalog_rows: list[list[str]], details_by_code: dict[str, str]
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for cells in catalog_rows:
        code = cells[3]
        if not re.fullmatch(r"\d{4}", code):
            continue
        if code in seen:
            raise RuntimeError(f"Mã ngành cấp 4 bị trùng: {code}")
        seen.add(code)
        rows.append(
            {
                "levels": ["", "", "", code, ""],
                "name": cells[5],
                "detail": details_by_code.get(code, ""),
            }
        )

    if len(rows) != EXPECTED_LEVEL4_COUNT:
        raise RuntimeError(
            f"Phụ lục phải có {EXPECTED_LEVEL4_COUNT} mã cấp 4 được liệt kê, "
            f"nhưng đã đọc được {len(rows)} mã."
        )
    return rows


def _details_by_code(document: Document) -> dict[str, str]:
    details: dict[str, list[str]] = {}
    current_codes: list[str] = []
    for paragraph in document.paragraphs:
        text = _clean(paragraph.text)
        if not text:
            continue
        heading_codes = _heading_codes(text)
        if heading_codes:
            current_codes = heading_codes
            for code in current_codes:
                details.setdefault(code, [])
            continue
        for code in current_codes:
            details[code].append(text)
    return {code: " ".join(parts).strip() for code, parts in details.items() if parts}


def _heading_codes(text: str) -> list[str]:
    # Most headings use a colon. The official source has one known composite
    # heading (7222-72220) without it, so composite headings also accept a
    # whitespace separator.
    match = re.match(
        r"^((?:[A-V]|\d{2,5})(?:\s*[-–]\s*(?:[A-V]|\d{2,5}))*)\s*:\s+.+$",
        text,
    )
    if not match:
        match = re.match(r"^(\d{2,5}(?:\s*[-–]\s*\d{2,5})+)\s+\D.+$", text)
    if not match:
        return []
    codes = re.findall(r"[A-V]|\d{2,5}", match.group(1))
    return codes if all(_is_valid_code(code) for code in codes) else []


def _is_valid_code(code: str) -> bool:
    return bool(re.fullmatch(r"[A-V]|\d{2,5}", code))


def _is_header_row(cells: list[str]) -> bool:
    return cells == ["Cấp 1", "Cấp 2", "Cấp 3", "Cấp 4", "Cấp 5", "Tên ngành"]


def _is_total_row(cells: list[str]) -> bool:
    return not cells[5] and all(re.fullmatch(r"\d+", value or "") for value in cells[:5])


def _clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


if __name__ == "__main__":
    sys.exit(main())
