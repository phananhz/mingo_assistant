"""Reproducible, offline ERC/BRC benchmark using image-only PDFs.

Run with PYTHONPATH=src. Default fixtures are synthetic; an explicit manifest
can select user-supplied PDFs. Runtime profiles are never read.
Fixtures and reports go to the ignored tmp/ directory by default.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from io import BytesIO
import json
from pathlib import Path
import sys
import time

import fitz
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
COMPANY = "CÔNG TY TNHH GIẢI PHÁP SỐ MINH AN"
LOCATION = f"ĐỊA ĐIỂM KINH DOANH SỐ 12 - {COMPANY}"
ADDRESS = "Số 128 đường Nguyễn Thị Định, Phường Bình Trưng, Thành phố Hồ Chí Minh, Việt Nam"
FIELDS = {
    "erc": {
        "organization_owner_name": COMPANY,
        "organization_owner_registration_number": "0312345678",
        "organization_owner_address_detail": "Số 128 đường Nguyễn Thị Định",
    },
    "brc": {
        "parent_entity_name": COMPANY,
        "parent_entity_registration_number": "0312345678001",
        "location_business_name": LOCATION,
        "location_business_code": "00012",
        "location_full_address": ADDRESS,
    },
}


def make_fixtures(output: Path, font: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for kind in FIELDS:
        lines = [
            "BỘ TÀI CHÍNH - TÀI LIỆU GIẢ LẬP KIỂM THỬ OCR",
            "GIẤY CHỨNG NHẬN ĐĂNG KÝ " + ("DOANH NGHIỆP" if kind == "erc" else "ĐỊA ĐIỂM KINH DOANH"),
        ]
        if kind == "erc":
            lines += [
                "Mã số doanh nghiệp: 0312345678",
                "Đăng ký lần đầu: ngày 15 tháng 10 năm 2026",
                "1. Tên công ty",
                f"Tên công ty viết bằng tiếng Việt: {COMPANY}",
                "Tên công ty viết bằng tiếng nước ngoài:",
                "2. Địa chỉ trụ sở chính:",
                "Số 128 đường Nguyễn Thị Định, Phường Bình Trưng,",
                "Thành phố Hồ Chí Minh, Việt Nam",
                "Điện thoại: 0900000012",
                "Thư điện tử: test@example.com",
                "3. Vốn điều lệ: 1.000.000.000 đồng",
                "4. Thông tin về chủ sở hữu",
            ]
        else:
            lines += [
                "Mã số địa điểm kinh doanh: 00012",
                "1. Tên địa điểm kinh doanh:",
                "ĐỊA ĐIỂM KINH DOANH SỐ 12 -",
                COMPANY,
                "Tên địa điểm kinh doanh viết bằng tiếng nước ngoài:",
                "2. Địa chỉ:",
                "Số 128 đường Nguyễn Thị Định, Phường Bình Trưng,",
                "Thành phố Hồ Chí Minh, Việt Nam",
                "Điện thoại: 0900000012",
                "Thư điện tử: test@example.com",
                "3. Thông tin về người đứng đầu",
                "Họ và tên: NGUYỄN VĂN KIỂM THỬ",
                "4. Thông tin về doanh nghiệp/chi nhánh chủ quản:",
                f"Tên doanh nghiệp/chi nhánh: {COMPANY}",
                "Mã số doanh nghiệp/chi nhánh: 0312345678001",
                "Địa chỉ trụ sở chính của doanh nghiệp/chi nhánh: Thành phố Hồ Chí Minh",
            ]
        with fitz.open() as source:
            page = source.new_page(width=595, height=842)
            page.insert_font(fontname="benchmark", fontfile=str(font))
            for index, line in enumerate(lines):
                page.insert_text((40, 65 + index * 27), line, fontsize=10.5, fontname="benchmark")
            image = Image.open(BytesIO(page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png"))).convert("RGB")
        for variant in ("scan", "skew"):
            candidate = image.copy()
            if variant == "skew":
                candidate = ImageEnhance.Contrast(candidate).enhance(0.55)
                candidate = candidate.filter(ImageFilter.GaussianBlur(0.35))
                candidate = candidate.rotate(2.7, resample=Image.Resampling.BICUBIC, expand=False, fillcolor="white")
            preview = output / f"{kind}_{variant}.png"
            candidate.save(preview)
            stream = BytesIO()
            candidate.save(stream, format="PNG")
            with fitz.open() as document:
                page = document.new_page(width=595, height=842)
                page.insert_image(page.rect, stream=stream.getvalue())
                document.save(output / f"{kind}_{variant}.pdf")


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def character_error_rate(expected: str, actual: str) -> float:
    expected, actual = normalized(expected), normalized(actual)
    previous = list(range(len(actual) + 1))
    for row, left in enumerate(expected, 1):
        current = [row]
        for column, right in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[column] + 1, previous[column - 1] + (left != right)))
        previous = current
    return round(previous[-1] / max(len(expected), 1), 4)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "tmp" / "certificate-ocr-benchmark")
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/arial.ttf"))
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--label", default="current")
    parser.add_argument("--manifest", type=Path, help="Local JSON list of {case, kind, pdf, expected} for private fixtures")
    parser.add_argument("--source-root", type=Path, help="Optional preserved src/ tree for a before/after comparison")
    parser.add_argument("--cases", nargs="+", default=["erc_scan", "brc_scan"])
    args = parser.parse_args()
    if args.prepare_only:
        make_fixtures(args.output, args.font)
        print(f"Synthetic scan fixtures: {args.output}", flush=True)
        return 0
    if args.source_root:
        sys.path.insert(0, str(args.source_root.resolve()))
    from mingo_assistant.services.normalization.address_parser import AddressParser
    from mingo_assistant.services.normalization.administrative_place_matcher import AdministrativePlaceMatcher
    from mingo_assistant.services.organization_documents.location_certificate_service import LocationCertificateService
    from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService

    address_parser = AddressParser(AdministrativePlaceMatcher(ROOT / "assets/administrative_places/vietnam_admin_2025.json"))
    services = {
        "erc": OrganizationDocumentService(address_parser=address_parser, bundle_root=ROOT),
        "brc": LocationCertificateService(address_parser=address_parser, bundle_root=ROOT),
    }
    cases = json.loads(args.manifest.read_text(encoding="utf-8")) if args.manifest else [
        {"case": name, "kind": name.split("_", 1)[0], "pdf": str(args.output / f"{name}.pdf"),
         "expected": FIELDS[name.split("_", 1)[0]]}
        for name in args.cases
    ]
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for case in cases:
        name, kind, path = case["case"], case["kind"], Path(case["pdf"])
        expected_fields = case["expected"]
        started = time.perf_counter()
        record = {"case": name}
        try:
            result = services[kind].extract_pdf(path)
            record["result"] = asdict(result)
            record["fields"] = {
                key: {
                    "expected": expected,
                    "actual": result.values.get(key, ""),
                    "exact": normalized(expected) == normalized(result.values.get(key, "")),
                    "cer": character_error_rate(expected, result.values.get(key, "")),
                }
                for key, expected in expected_fields.items()
            }
            exact = sum(field["exact"] for field in record["fields"].values())
            print(f"{name}: {exact}/{len(expected_fields)} fields exact", flush=True)
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            print(f"{name}: {record['error']}", flush=True)
        record["seconds"] = round(time.perf_counter() - started, 2)
        records.append(record)
        (args.output / f"{args.label}.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return int(any("error" in record for record in records))


if __name__ == "__main__":
    raise SystemExit(main())
