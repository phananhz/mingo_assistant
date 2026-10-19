"""Read a Vietnamese business-location registration certificate from a PDF."""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import fitz

from mingo_assistant.services.organization_documents.organization_document_service import (
    OrganizationDocumentResult,
    OrganizationDocumentService,
    ProgressCallback,
)


class LocationCertificateService(OrganizationDocumentService):
    DOCUMENT_TYPE = "brc"

    """Reuse the installed OCR engines, but parse location certificates separately."""

    REQUIRED = ("parent_entity_name", "parent_entity_registration_number",
                "location_business_name", "location_business_code", "location_full_address")

    def _extract_page_with_ocr(self, legacy_engine, image_bytes: bytes, *, use_legacy: bool = False) -> str:
        # Reuse one set of detected lines for Vietnamese refinement instead of
        # detecting the same page with two complete OCR pipelines.
        import cv2
        import numpy as np
        from mingo_assistant.services.ocr.vietnamese_line_refiner import VietnameseLineRefiner
        result, _ = legacy_engine(image_bytes)
        lines = result or []
        if not use_legacy and self._vietnamese_ocr:
            if not hasattr(self, "_line_refiner"):
                self._line_refiner = VietnameseLineRefiner(self._vietnamese_ocr.model_dir)
            try:
                image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                lines = self._line_refiner.refine(image, lines)
            except Exception:
                # Optional model failures must keep basic scanning available.
                import logging
                logging.getLogger(__name__).exception("Vietnamese line refinement unavailable")
        return "\n".join(str(line[1]).strip() for line in lines)

    def extract_pdf(self, path: str | Path, progress_callback: ProgressCallback | None = None) -> OrganizationDocumentResult:
        pdf_path = Path(path)
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError("Vui lòng chọn Giấy chứng nhận đăng ký địa điểm kinh doanh dạng PDF.")
        if not pdf_path.is_file():
            raise FileNotFoundError("Không tìm thấy giấy chứng nhận địa điểm kinh doanh.")

        self._progress(progress_callback, 5, "Đang mở giấy chứng nhận địa điểm kinh doanh")
        with fitz.open(pdf_path) as document:
            direct_text = "\n".join(page.get_text("text") for page in document)
            detected_type = self._validate_expected_document_type(direct_text)
            if not detected_type:
                quick_text = self._extract_first_page_for_type_detection(document, progress_callback)
                self._validate_expected_document_type(quick_text)
            candidates: list[tuple[str, dict[str, str], str]] = []
            direct = self._parse_certificate(direct_text)
            if direct:
                candidates.append(("pdf_text", direct, direct_text))
            if not self._complete(direct):
                self._progress(progress_callback, 25, "Đang nhận diện giấy chứng nhận địa điểm kinh doanh")
                primary_text = self._extract_with_ocr(document, progress_callback)
                primary = self._parse_certificate(primary_text)
                if primary:
                    candidates.append(("vietnamese_lines" if self._vietnamese_ocr else "rapidocr", primary, primary_text))
                if not self._complete(primary):
                    self._progress(progress_callback, 75, "Đang đối chiếu chữ và số trên giấy chứng nhận")
                    fallback_text = self._extract_with_ocr(document, progress_callback, use_legacy=True)
                    fallback = self._parse_certificate(fallback_text)
                    if fallback:
                        candidates.append(("rapidocr", fallback, fallback_text))
                combined = self._combine_candidate_values(candidates)
                if not self._complete(combined):
                    self._progress(progress_callback, 90, "Đang tăng cường ảnh giấy chứng nhận khó đọc")
                    enhanced_text = self._extract_with_ocr(document, progress_callback, enhanced=True)
                    enhanced = self._parse_certificate(enhanced_text)
                    if enhanced:
                        source = "vietnamese_lines_enhanced" if self._vietnamese_ocr else "rapidocr_enhanced"
                        candidates.append((source, enhanced, enhanced_text))

        if not candidates:
            raise ValueError("Không nhận ra Giấy chứng nhận đăng ký địa điểm kinh doanh trong PDF đã chọn.")

        # Prefer complete labels and unbroken names from RapidOCR.  The modern
        # engine supplies accents where its text is otherwise equally complete.
        sources: dict[str, str] = {}
        values: dict[str, str] = {}
        confidences: dict[str, float] = {}
        for key in self.REQUIRED + ("location_address_detail", "location_ward", "location_province",
                                    "location_phone", "location_fax", "location_email", "location_website"):
            options = [(source, data[key]) for source, data, _ in candidates if data.get(key)]
            if not options:
                continue
            agreement_counts: dict[str, int] = {}
            for _source, option_value in options:
                canonical = self._compact(option_value)
                agreement_counts[canonical] = agreement_counts.get(canonical, 0) + 1
            source, value = max(
                options,
                key=lambda item: self._value_rank(
                    key,
                    item[0],
                    item[1],
                    agreement_counts.get(self._compact(item[1]), 1),
                ),
            )
            values[key] = value
            sources[key] = source
            confidences[key] = min(
                0.99,
                self._field_quality_for_brc(key, value)
                + (0.03 * (agreement_counts.get(self._compact(value), 1) - 1)),
            )
        if values.get("location_full_address"):
            values["location_full_address"] = self._enrich_address_accents(
                values["location_full_address"], candidates
            )
            confidences["location_full_address"] = self._field_quality_for_brc(
                "location_full_address", values["location_full_address"]
            )
            address = self._address_fields(values["location_full_address"])
            values.update(address)
            sources.update({key: sources["location_full_address"] for key in address})
            confidences.update({
                key: self._field_quality_for_brc(key, field_value)
                for key, field_value in address.items()
            })
        raw_source, _, raw_text = max(candidates, key=lambda item: (item[0] == "rapidocr", len(item[1])))
        missing = [key for key in self.REQUIRED if not values.get(key)]
        warnings = ["Cần kiểm tra lại dấu tiếng Việt ở tên và địa chỉ theo giấy gốc."] if raw_source != "pdf_text" else []
        if missing:
            warnings.append("Chưa nhận diện đủ: " + ", ".join(missing) + ".")
        low_confidence = [key for key in self.REQUIRED if values.get(key) and confidences.get(key, 0.0) < 0.80]
        if low_confidence:
            warnings.append("Cần đối chiếu lại các trường có độ tin cậy thấp: " + ", ".join(low_confidence) + ".")
        required_scores = [confidences.get(key, 0.0) for key in self.REQUIRED]
        self._progress(progress_callback, 100, "Đã nhận diện giấy chứng nhận địa điểm kinh doanh")
        return OrganizationDocumentResult(
            values=values, raw_text=raw_text,
            extraction_method="text" if all(source == "pdf_text" for source in sources.values()) else "ocr",
            warnings=warnings, field_sources=sources,
            field_confidences=confidences,
            quality_score=round(sum(required_scores) / len(required_scores), 3),
            processing_route=tuple(dict.fromkeys(source for source, _, _ in candidates)),
            document_type="brc",
        )

    def _combine_candidate_values(self, candidates: list[tuple[str, dict[str, str], str]]) -> dict[str, str]:
        """Check aggregate completeness before paying for the enhanced OCR pass."""
        combined: dict[str, str] = {}
        for _source, values, _raw_text in candidates:
            for key, value in values.items():
                if value and not combined.get(key):
                    combined[key] = value
        return combined

    def _complete(self, values: dict[str, str] | None) -> bool:
        return bool(
            values and all(values.get(key) for key in self.REQUIRED)
            and values.get("location_ward") and not any(
                ":" in values.get(key, "")
                for key in ("parent_entity_name", "location_business_name", "location_full_address")
            )
        )

    def _value_rank(self, key: str, source: str, value: str, agreement: int = 1) -> tuple[float, int, int, int]:
        source_priority = {
            "pdf_text": 5,
            "vietnamese_lines_enhanced": 4,
            "vietnamese_lines": 3,
            "rapidocr_enhanced": 2,
            "rapidocr": 1,
        }.get(source, 0)
        length_tiebreaker = 0 if key in {
            "parent_entity_registration_number", "location_business_code",
            "location_phone", "location_fax", "location_email",
        } else min(len(value), 250)
        return self._field_quality_for_brc(key, value), agreement, source_priority, length_tiebreaker

    def _field_quality_for_brc(self, key: str, value: str) -> float:
        value = str(value or "").strip()
        if not value:
            return 0.0
        if key == "location_business_code":
            return 0.99 if re.fullmatch(r"\d{5}", value) else 0.35
        if key == "parent_entity_registration_number":
            return 0.99 if re.fullmatch(r"\d{10}(?:\d{3})?", value) else 0.35
        if key in {"parent_entity_name", "location_business_name"}:
            return self._field_quality("organization_owner_name", value)
        if key in {"location_full_address", "location_address_detail"}:
            return self._field_quality("organization_owner_address_detail", value)
        if key in {"location_ward", "location_province"}:
            return self._field_quality("organization_owner_province", value)
        if key in {"location_phone", "location_fax"}:
            return self._field_quality("organization_owner_phone", value)
        if key == "location_email":
            return self._field_quality("organization_owner_email", value)
        if key == "location_website":
            return self._field_quality("organization_owner_website", value)
        return 0.80

    def _parse_certificate(self, text: str) -> dict[str, str]:
        lines = self._lines(text)
        compact = [self._compact(line).replace("s6", "so").replace("s0", "so") for line in lines]
        if not any(
            "giaychungnh" in line
            and self._contains_fuzzy(line, "diadiemkinhdoanh", threshold=0.76)
            for line in compact
        ):
            return {}

        def first(
            *labels: str,
            section: int | None = None,
            threshold: float = 0.76,
            starts_with: tuple[str, ...] = (),
        ) -> int:
            return next((
                index
                for index, line in enumerate(lines)
                if (section is None or self._section_number(line) == section)
                and (
                    not starts_with
                    or re.sub(r"^\d+", "", compact[index]).startswith(starts_with)
                )
                and self._label_matches(line, labels, threshold=threshold)
            ), -1)

        def take(index: int, stop: tuple[str, ...], *, max_lines: int = 4) -> str:
            if index < 0:
                return ""
            chunks = [lines[index].split(":", 1)[1].strip()] if ":" in lines[index] else []
            for line, folded in zip(
                lines[index + 1:index + 1 + max_lines],
                compact[index + 1:index + 1 + max_lines],
            ):
                if self._is_stop_line(line, folded, stop):
                    break
                chunks.append(line)
            return " ".join(chunk for chunk in chunks if chunk).strip(" ,;")

        location_code = first(
            "masodiadiemkinhdoanh", "masdiadiemkinhdoanh", "masodiadimkinhdoanh",
            threshold=0.70, starts_with=("ma",),
        )
        name = first(
            "tendiadiemkinhdoanh", "tendiadimkinhdoanh", section=1, threshold=0.70,
            starts_with=("ten",),
        )
        address = first("diachi", "djachi", "dachi", section=2, threshold=0.62)
        parent = first(
            "tendoanhnghiepchinhanh", "tendoanhnghiepchinhanhchuquan", threshold=0.70,
            starts_with=("ten",),
        )
        parent_code = first(
            "masodoanhnghiepchinhanh", "masdoanhnghiepchinhanh", threshold=0.70,
            starts_with=("ma",),
        )
        if parent < 0 or parent_code < 0:
            return {}
        location_name = take(name, ("tendiadiemkinhdoanhviet", "2", "diachi"), max_lines=5)
        full_address = take(
            address,
            ("dienthoai", "sofax", "fax", "thudientu", "email", "website", "3"),
            max_lines=9,
        )
        parent_name = take(parent, ("masodoanhnghiep", "diachitrusochinh", "diachitrusochinh"), max_lines=3)
        location_name = self._restore_name(location_name)
        parent_name = self._restore_name(parent_name)
        if " - " in location_name:
            prefix, company_suffix = location_name.split(" - ", 1)
            if self._compact(company_suffix) == self._compact(parent_name):
                location_name = f"{prefix} - {parent_name}"
        values = {
            "location_business_code": self._code(take(location_code, ("dangky", "1", "tendiadiem"), max_lines=2), 5),
            "location_business_name": location_name,
            "location_full_address": self._restore_address(full_address),
            "parent_entity_name": parent_name,
            "parent_entity_registration_number": self._code(take(parent_code, ("diachitruso", "hoten", "3thongtin"), max_lines=2), 10),
        }
        for key, markers in {
            "location_phone": ("dienthoai",), "location_fax": ("sofax", "fax"),
            "location_email": ("thudientu", "thudientr", "email"), "location_website": ("website",),
        }.items():
            index = next((
                i for i, line in enumerate(lines)
                if self._label_matches(line, markers, threshold=0.72)
            ), -1)
            if index >= 0:
                value = lines[index].split(":", 1)[-1].strip() if ":" in lines[index] else ""
                if key == "location_email":
                    match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value)
                    value = match.group() if match else ""
                values[key] = value

        if values["location_full_address"]:
            values.update(self._address_fields(values["location_full_address"]))
        return values

    def _label_matches(self, line: str, labels: tuple[str, ...], *, threshold: float) -> bool:
        label = self._compact(line.split(":", 1)[0]).replace("s6", "so").replace("s0", "so")
        label = re.sub(r"^\d+", "", label)
        for candidate in labels:
            normalized = self._compact(candidate)
            if normalized in label or label in normalized:
                if min(len(normalized), len(label)) >= 4:
                    return True
            if SequenceMatcher(None, label, normalized).ratio() >= threshold:
                return True
        return False

    @staticmethod
    def _section_number(line: str) -> int | None:
        match = re.match(r"\s*([1-5])(?:\s*[.):-]|\s+)", line)
        return int(match.group(1)) if match else None

    @staticmethod
    def _contains_fuzzy(value: str, expected: str, *, threshold: float) -> bool:
        if expected in value:
            return True
        if len(value) < 6:
            return False
        window = len(expected)
        return any(
            SequenceMatcher(None, value[start:start + window], expected).ratio() >= threshold
            for start in range(max(1, len(value) - window + 1))
        )

    def _is_stop_line(self, line: str, compact: str, markers: tuple[str, ...]) -> bool:
        section = self._section_number(line)
        for marker in markers:
            if marker.isdigit() and section == int(marker):
                return True
            if compact.startswith(marker):
                return True
        textual = tuple(marker for marker in markers if not marker.isdigit())
        return bool(textual and self._label_matches(line, textual, threshold=0.72))

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
