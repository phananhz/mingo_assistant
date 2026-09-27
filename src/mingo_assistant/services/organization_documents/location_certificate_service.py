"""Read a Vietnamese business-location registration certificate from a PDF."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import fitz

from mingo_assistant.services.organization_documents.organization_document_service import (
    OrganizationDocumentResult,
    OrganizationDocumentService,
    ProgressCallback,
)


class LocationCertificateService(OrganizationDocumentService):
    """Reuse the installed OCR engines, but parse location certificates separately."""

    REQUIRED = ("parent_entity_name", "parent_entity_registration_number",
                "location_business_name", "location_business_code", "location_full_address")

    def extract_pdf(self, path: str | Path, progress_callback: ProgressCallback | None = None) -> OrganizationDocumentResult:
        pdf_path = Path(path)
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError("Vui lòng chọn Giấy chứng nhận đăng ký địa điểm kinh doanh dạng PDF.")
        if not pdf_path.is_file():
            raise FileNotFoundError("Không tìm thấy giấy chứng nhận địa điểm kinh doanh.")

        self._progress(progress_callback, 5, "Đang mở giấy chứng nhận địa điểm kinh doanh")
        with fitz.open(pdf_path) as document:
            direct_text = "\n".join(page.get_text("text") for page in document)
            candidates: list[tuple[str, dict[str, str], str]] = []
            direct = self._parse_certificate(direct_text)
            if direct:
                candidates.append(("pdf_text", direct, direct_text))
            if not self._complete(direct):
                self._progress(progress_callback, 25, "Đang nhận diện giấy chứng nhận địa điểm kinh doanh")
                primary_text = self._extract_with_ocr(document, progress_callback)
                primary = self._parse_certificate(primary_text)
                if primary:
                    candidates.append(("ppocr_v6" if self._vietnamese_ocr and self._vietnamese_ocr.is_available else "rapidocr", primary, primary_text))
                if not self._complete(primary):
                    self._progress(progress_callback, 75, "Đang đối chiếu chữ và số trên giấy chứng nhận")
                    fallback_text = self._extract_with_ocr(document, progress_callback, use_legacy=True)
                    fallback = self._parse_certificate(fallback_text)
                    if fallback:
                        candidates.append(("rapidocr", fallback, fallback_text))

        if not candidates:
            raise ValueError("Không nhận ra Giấy chứng nhận đăng ký địa điểm kinh doanh trong PDF đã chọn.")

        # Prefer complete labels and unbroken names from RapidOCR.  The modern
        # engine supplies accents where its text is otherwise equally complete.
        sources: dict[str, str] = {}
        values: dict[str, str] = {}
        for key in self.REQUIRED + ("location_address_detail", "location_ward", "location_province",
                                    "location_phone", "location_fax", "location_email", "location_website"):
            options = [(source, data[key]) for source, data, _ in candidates if data.get(key)]
            if not options:
                continue
            source, value = max(options, key=lambda item: self._value_rank(key, item[0], item[1]))
            values[key] = value
            sources[key] = source
        if values.get("location_full_address"):
            values["location_full_address"] = self._enrich_address_accents(
                values["location_full_address"], candidates
            )
            address = self._address_fields(values["location_full_address"])
            values.update(address)
            sources.update({key: sources["location_full_address"] for key in address})
        raw_source, _, raw_text = max(candidates, key=lambda item: (item[0] == "rapidocr", len(item[1])))
        missing = [key for key in self.REQUIRED if not values.get(key)]
        warnings = ["Cần kiểm tra lại dấu tiếng Việt ở tên và địa chỉ theo giấy gốc."] if raw_source != "pdf_text" else []
        if missing:
            warnings.append("Chưa nhận diện đủ: " + ", ".join(missing) + ".")
        self._progress(progress_callback, 100, "Đã nhận diện giấy chứng nhận địa điểm kinh doanh")
        return OrganizationDocumentResult(
            values=values, raw_text=raw_text,
            extraction_method="text" if all(source == "pdf_text" for source in sources.values()) else "ocr",
            warnings=warnings, field_sources=sources,
            field_confidences={key: 0.95 if re.fullmatch(r"\d{5,13}", value) else 0.8 for key, value in values.items()},
            quality_score=round((len(self.REQUIRED) - len(missing)) / len(self.REQUIRED), 2),
            processing_route=tuple(source for source, _, _ in candidates),
        )

    def _complete(self, values: dict[str, str] | None) -> bool:
        return bool(
            values and all(values.get(key) for key in self.REQUIRED)
            and values.get("location_ward") and not any(
                ":" in values.get(key, "")
                for key in ("parent_entity_name", "location_business_name", "location_full_address")
            )
        )

    @staticmethod
    def _value_rank(key: str, source: str, value: str) -> tuple[int, int, int]:
        # Missing vowels make an accented OCR line less useful than a complete
        # unaccented line.  Keep exact codes and contact fields independent.
        if key in {"parent_entity_name", "location_business_name", "location_full_address", "location_address_detail"}:
            return (0 if ":" in value else 1, len(value), 1 if source == "pdf_text" else 0)
        return (1 if source == "pdf_text" else 0, len(value), 1 if source == "rapidocr" else 0)

    def _parse_certificate(self, text: str) -> dict[str, str]:
        lines = self._lines(text)
        compact = [self._compact(line).replace("s6", "so").replace("s0", "so") for line in lines]
        if not any("giaychungnh" in line and ("diadiemkinhdoanh" in line or "diadimkinhdoanh" in line)
                   for line in compact):
            return {}

        def first(*parts: str) -> int:
            return next((i for i, line in enumerate(compact) if all(part in line for part in parts)), -1)

        def take(index: int, stop: tuple[str, ...], *, max_lines: int = 4) -> str:
            if index < 0:
                return ""
            chunks = [lines[index].split(":", 1)[1].strip()] if ":" in lines[index] else []
            for line, folded in zip(lines[index + 1:index + max_lines], compact[index + 1:index + max_lines]):
                if any(folded.startswith(marker) for marker in stop):
                    break
                chunks.append(line)
            return " ".join(chunk for chunk in chunks if chunk).strip(" ,;")

        location_code = first("maso", "diadiemkinhdoanh")
        if location_code < 0:
            location_code = first("mas", "dadimkinhdoanh")
        name = first("ten", "diadiemkinhdoanh")
        if name < 0:
            name = first("ten", "dadimkinhdoanh")
        address = next((i for i, line in enumerate(compact) if line.startswith(("2diachi", "2dachi"))), -1)
        parent = first("ten", "doanhnghiep", "chinhanh")
        if parent < 0:
            parent = first("ten", "doanhnghip", "chinhanh")
        parent_code = first("maso", "doanhnghiep", "chinhanh")
        if parent_code < 0:
            parent_code = first("mas", "doanhnghip", "chinhanh")
        if parent < 0 or parent_code < 0:
            return {}
        location_name = take(name, ("tendiadiemkinhdoanhviet", "2diachi", "diachi"))
        full_address = take(address, ("dienthoai", "sofax", "thudientu", "website", "3thongtin"), max_lines=5)
        parent_name = take(parent, ("masodoanhnghiep", "diachitrusochinh", "diachitrusochinh"), max_lines=3)
        location_name = self._restore_name(location_name)
        parent_name = self._restore_name(parent_name)
        if " - " in location_name:
            prefix, company_suffix = location_name.split(" - ", 1)
            if self._compact(company_suffix) == self._compact(parent_name):
                location_name = f"{prefix} - {parent_name}"
        values = {
            "location_business_code": self._code(take(location_code, ("dangky", "1ten", "tendiadiem"), max_lines=2), 5),
            "location_business_name": location_name,
            "location_full_address": self._restore_address(full_address),
            "parent_entity_name": parent_name,
            "parent_entity_registration_number": self._code(take(parent_code, ("diachitruso", "hoten", "3thongtin"), max_lines=2), 10),
        }
        for key, markers in {
            "location_phone": ("dienthoai",), "location_fax": ("sofax", "fax"),
            "location_email": ("thudientu", "thudientr", "email"), "location_website": ("website",),
        }.items():
            index = next((i for i, line in enumerate(compact) if any(line.startswith(marker) for marker in markers)), -1)
            if index >= 0:
                value = lines[index].split(":", 1)[-1].strip() if ":" in lines[index] else ""
                if key == "location_email":
                    match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value)
                    value = match.group() if match else ""
                values[key] = value

        if values["location_full_address"]:
            values.update(self._address_fields(values["location_full_address"]))
        return values

    def _address_fields(self, full_address: str) -> dict[str, str]:
        parsed = self.address_parser.parse(full_address)
        street_parts = []
        for part in (part.strip() for part in full_address.split(",")):
            if self._compact(part).startswith(("phuong", "xa", "thanhpho", "tinh", "vietnam")):
                break
            street_parts.append(part)
        return {
            "location_address_detail": ", ".join(street_parts) or parsed.street_line,
            "location_ward": parsed.ward,
            "location_province": parsed.province,
        }

    def _enrich_address_accents(
        self, address: str, candidates: list[tuple[str, dict[str, str], str]]
    ) -> str:
        """Borrow a matching accented address segment without changing its letters."""
        def accent_count(value: str) -> int:
            return sum(
                unicodedata.combining(character) != 0
                for character in unicodedata.normalize("NFD", value)
            )

        parts = [part.strip() for part in address.split(",")]
        for _, candidate, _ in candidates:
            for alternative in candidate.get("location_full_address", "").split(","):
                alternative = alternative.strip()
                for index, part in enumerate(parts):
                    if self._compact(part) != self._compact(alternative):
                        continue
                    if accent_count(alternative) > accent_count(part):
                        parts[index] = alternative
        return ", ".join(parts)

    @staticmethod
    def _code(value: str, digits: int) -> str:
        match = re.search(rf"(?<!\d)\d{{{digits}}}(?!\d)", value)
        return match.group() if match else ""

    def _restore_name(self, value: str) -> str:
        value = re.sub(r"(?i)\bDIA DIEM KINH DOANH\b", "ĐỊA ĐIỂM KINH DOANH", value)
        value = self._restore_vietnamese_phrases(value)
        return value.upper()

    def _restore_address(self, value: str) -> str:
        return self._restore_vietnamese_phrases(value).strip()
