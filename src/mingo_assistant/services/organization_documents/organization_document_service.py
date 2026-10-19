from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Callable

import fitz

from mingo_assistant.services.normalization.address_parser import AddressParser
from mingo_assistant.services.ocr.vietnamese_document_ocr import VietnameseDocumentOcr


ProgressCallback = Callable[[int, str], None]


class DocumentTypeMismatchError(ValueError):
    """Raised before full OCR when a PDF belongs to another supported workflow."""


@dataclass(frozen=True)
class OrganizationDocumentResult:
    values: dict[str, str]
    raw_text: str
    extraction_method: str
    warnings: list[str] = field(default_factory=list)
    field_confidences: dict[str, float] = field(default_factory=dict)
    field_sources: dict[str, str] = field(default_factory=dict)
    quality_score: float = 0.0
    processing_route: tuple[str, ...] = ()
    document_type: str = "erc"


class OrganizationDocumentService:
    DOCUMENT_TYPE = "erc"

    """Extract organization-owner fields from common Vietnamese business PDFs."""

    _ESSENTIAL_FIELDS = (
        "organization_owner_name",
        "organization_owner_registration_number",
        "organization_owner_address_detail",
    )

    def __init__(self, address_parser: AddressParser | None = None, bundle_root: Path | None = None) -> None:
        self.address_parser = address_parser or AddressParser()
        self._vietnamese_ocr = VietnameseDocumentOcr(bundle_root) if bundle_root else None

    def extract_pdf(self, path: str | Path, progress_callback: ProgressCallback | None = None) -> OrganizationDocumentResult:
        document_path = Path(path)
        if document_path.suffix.lower() != ".pdf":
            raise ValueError("Hiện chỉ hỗ trợ đọc tài liệu PDF doanh nghiệp.")
        if not document_path.exists():
            raise FileNotFoundError("Không tìm thấy tài liệu doanh nghiệp đã chọn.")

        self._progress(progress_callback, 5, "Đang mở tài liệu doanh nghiệp")
        with fitz.open(document_path) as document:
            direct_text = "\n".join(page.get_text("text") for page in document)
            detected_type = self._validate_expected_document_type(direct_text)
            if not detected_type:
                quick_text = self._extract_first_page_for_type_detection(document, progress_callback)
                self._validate_expected_document_type(quick_text)
            direct_result = self._extract_supported_document(direct_text, "text", source="pdf_text")
            if direct_result is not None and not self._needs_ocr_fallback(direct_result):
                self._progress(progress_callback, 100, "Đã đọc thông tin tổ chức")
                return replace(direct_result, processing_route=("pdf_text",))

            self._progress(progress_callback, 25, "Đang nhận diện chữ trong tài liệu")
            ocr_text = self._extract_with_ocr(document, progress_callback)
            primary_source = (
                "ppocr_v6"
                if self._vietnamese_ocr and self._vietnamese_ocr.is_available
                else "rapidocr"
            )
            primary_result = self._extract_supported_document(ocr_text, "ocr", source=primary_source)
            result = self._merge_results(direct_result, primary_result)
            route = ["pdf_text", primary_source]

            if self._vietnamese_ocr and self._vietnamese_ocr.is_available:
                self._progress(progress_callback, 75, "Đang đối chiếu bằng bộ nhận diện dự phòng")
                legacy_text = self._extract_with_ocr(document, progress_callback, use_legacy=True)
                legacy_result = self._extract_supported_document(legacy_text, "ocr", source="rapidocr")
                result = self._merge_results(result, legacy_result)
                route.append("rapidocr")

            if self._needs_enhanced_pass(result):
                self._progress(progress_callback, 90, "Đang tăng cường ảnh tài liệu khó đọc")
                enhanced_text = self._extract_with_ocr(document, progress_callback, enhanced=True)
                enhanced_source = (
                    "ppocr_v6_enhanced"
                    if self._vietnamese_ocr and self._vietnamese_ocr.is_available
                    else "rapidocr_enhanced"
                )
                enhanced_result = self._extract_supported_document(
                    enhanced_text,
                    "ocr",
                    source=enhanced_source,
                )
                result = self._merge_results(result, enhanced_result)
                route.append(enhanced_source)
        if result is not None:
            self._progress(progress_callback, 100, "Đã nhận diện thông tin tổ chức")
            return replace(result, processing_route=tuple(route))

        raise ValueError(
            "Không nhận ra Giấy chứng nhận đăng ký doanh nghiệp (ERC) trong PDF đã chọn."
        )

    @classmethod
    def detect_document_type(cls, text: str) -> str:
        """Classify ERC/BRC from cheap PDF text or a quick first-page OCR pass."""
        compact = cls._compact(text)
        if not compact:
            return ""

        brc_score = 0
        erc_score = 0
        if "giaychungnhandangkydiadiemkinhdoanh" in compact:
            brc_score += 8
        if "masodiadiemkinhdoanh" in compact or "masdiadiemkinhdoanh" in compact:
            brc_score += 3
        if "tendiadiemkinhdoanh" in compact or "tendiadimkinhdoanh" in compact:
            brc_score += 3
        if "thongtinvendoanhnghiepchinhanhchuquan" in compact:
            brc_score += 1

        if "giaychungnhandangkydoanhnghiep" in compact:
            erc_score += 8
        if "masodoanhnghiep" in compact or "masdoanhnghiep" in compact:
            erc_score += 2
        if "tencongtyvietbangtiengviet" in compact or "diachitrusochinh" in compact:
            erc_score += 2

        if brc_score >= 6 and brc_score > erc_score:
            return "brc"
        if erc_score >= 6 and erc_score > brc_score:
            return "erc"
        if "thongtinvechusohuu" in compact and "tentochuc" in compact:
            return "other"
        return ""

    def _validate_expected_document_type(self, text: str) -> str:
        actual = self.detect_document_type(text)
        expected = self.DOCUMENT_TYPE
        if not actual or actual == expected:
            return actual

        expected_label = {
            "erc": "Giấy chứng nhận đăng ký doanh nghiệp (ERC)",
            "brc": "Giấy chứng nhận đăng ký địa điểm kinh doanh (BRC)",
        }.get(expected, expected.upper())
        actual_label = {
            "erc": "Giấy chứng nhận đăng ký doanh nghiệp (ERC)",
            "brc": "Giấy chứng nhận đăng ký địa điểm kinh doanh (BRC)",
            "other": "một tài liệu khác không thuộc ERC/BRC",
        }.get(actual, actual.upper())
        workflow = "thành lập doanh nghiệp" if expected == "erc" else "địa điểm kinh doanh"
        raise DocumentTypeMismatchError(
            f"Sai loại tài liệu: chức năng {workflow} chỉ nhận CCCD hoặc {expected_label}. "
            f"Tài liệu đã chọn được nhận dạng là {actual_label}."
        )

    def _extract_first_page_for_type_detection(
        self,
        document: fitz.Document,
        progress_callback: ProgressCallback | None,
    ) -> str:
        """Run one inexpensive OCR pass only when embedded PDF text is inconclusive."""
        try:
            if int(document.page_count) <= 0:
                return ""
            from rapidocr_onnxruntime import RapidOCR

            if not hasattr(self, "_legacy_engine"):
                self._legacy_engine = RapidOCR()
            self._progress(progress_callback, 12, "Đang kiểm tra nhanh loại tài liệu")
            page = document.load_page(0)
            scale = self._render_scale(page, enhanced=False)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            return self._extract_page_with_ocr(
                self._legacy_engine,
                pixmap.tobytes("png"),
                use_legacy=True,
            )
        except Exception:
            # Type detection is an early guard. If it is inconclusive, the
            # normal OCR pipeline remains responsible for the final result.
            return ""

    def _extract_supported_document(
        self,
        text: str,
        method: str,
        *,
        source: str | None = None,
    ) -> OrganizationDocumentResult | None:
        # Only an ERC is valid in company-establishment workflows. Its
        # authoritative company fields are in sections 1 and 2; section 4
        # must never be accepted as a standalone organization document.
        if self._is_business_certificate(text):
            return self._build_certificate_result(text, text, method, source=source)
        return None

    def _extract_with_ocr(
        self,
        document: fitz.Document,
        progress_callback: ProgressCallback | None,
        *,
        use_legacy: bool = False,
        enhanced: bool = False,
    ) -> str:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:  # pragma: no cover - protected by packaging configuration
            raise RuntimeError("Thiếu bộ OCR nội bộ. Hãy dùng bản ứng dụng đã đóng gói đầy đủ.") from exc

        if not hasattr(self, "_legacy_engine"):
            self._legacy_engine = RapidOCR()
        engine = self._legacy_engine
        pages: list[str] = []
        page_count = max(document.page_count, 1)
        for index, page in enumerate(document):
            if enhanced:
                percent = 90 + int((index / page_count) * 9)
                status = "Đang tăng cường"
            elif use_legacy:
                percent = 75 + int((index / page_count) * 14)
                status = "Đang đối chiếu"
            else:
                percent = 25 + int((index / page_count) * 49)
                status = "Đang nhận diện"
            self._progress(progress_callback, percent, f"{status} trang {index + 1}/{page_count}")
            scale = self._render_scale(page, enhanced=enhanced)
            image = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image_bytes = image.tobytes("png")
            if enhanced:
                image_bytes = self._preprocess_for_ocr(image_bytes)
            pages.append(self._extract_page_with_ocr(engine, image_bytes, use_legacy=use_legacy))
        return "\n".join(pages)

    @staticmethod
    def _render_scale(page, *, enhanced: bool) -> float:
        """Render small/normal pages sharply without exploding unusually large pages."""
        longest_side = max(float(page.rect.width), float(page.rect.height), 1.0)
        # The bundled detector is calibrated well around 2x for ordinary A4
        # certificates. Upscaling every page can merge thin Vietnamese glyphs,
        # so reserve the larger render for the quality-triggered enhanced pass.
        target_pixels = 3000.0 if enhanced else 1600.0
        minimum, maximum = (3.0, 3.6) if enhanced else (2.0, 2.5)
        return max(minimum, min(maximum, target_pixels / longest_side))

    @staticmethod
    def _preprocess_for_ocr(image_bytes: bytes) -> bytes:
        """Improve faint scans and correct small page skew for the final OCR pass."""
        try:
            import cv2
            import numpy as np

            image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if image is None:
                return image_bytes

            clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
            blurred = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
            enhanced = cv2.addWeighted(enhanced, 1.35, blurred, -0.35, 0)

            _, foreground = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            coordinates = cv2.findNonZero(foreground)
            if coordinates is not None:
                foreground_ratio = len(coordinates) / float(enhanced.size)
                if 0.002 < foreground_ratio < 0.35:
                    angle = cv2.minAreaRect(coordinates)[-1]
                    angle = -(90 + angle) if angle < -45 else -angle
                    if 0.6 <= abs(angle) <= 8.0:
                        height, width = enhanced.shape
                        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
                        enhanced = cv2.warpAffine(
                            enhanced,
                            matrix,
                            (width, height),
                            flags=cv2.INTER_CUBIC,
                            borderMode=cv2.BORDER_CONSTANT,
                            borderValue=255,
                        )

            success, encoded = cv2.imencode(".png", enhanced)
            return encoded.tobytes() if success else image_bytes
        except Exception:
            return image_bytes

    def _extract_page_with_ocr(self, legacy_engine, image_bytes: bytes, *, use_legacy: bool = False) -> str:
        """Prefer bundled PP-OCRv6, retaining the existing engine as a safe fallback."""
        if not use_legacy and self._vietnamese_ocr and self._vietnamese_ocr.is_available:
            try:
                lines = self._vietnamese_ocr.recognize_detailed(image_bytes)
                if lines:
                    try:
                        import cv2
                        import numpy as np
                        from mingo_assistant.services.ocr.vietnamese_line_refiner import VietnameseLineRefiner

                        if not hasattr(self, "_line_refiner"):
                            self._line_refiner = VietnameseLineRefiner(self._vietnamese_ocr.model_dir)
                        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if image is not None:
                            lines = self._line_refiner.refine(image, lines)
                    except Exception:
                        # PP-OCRv6 text remains usable if optional VietOCR refinement fails.
                        pass
                    return "\n".join(text for _box, text, _score in lines)
            except Exception:
                # A damaged optional model must never prevent a user from
                # reading a PDF with the formerly shipped OCR engine.
                pass
        result, _elapsed = legacy_engine(image_bytes)
        return "\n".join(str(line[1]).strip() for line in result or [] if len(line) > 1)

    def _owner_section(self, text: str) -> str:
        lines = self._lines(text)
        start = next((index for index, line in enumerate(lines) if self._is_owner_heading(line)), None)
        if start is None:
            return ""
        end = next(
            (index for index in range(start + 1, len(lines)) if self._compact(lines[index]).startswith("5")),
            len(lines),
        )
        return "\n".join(lines[start + 1 : end])

    def _is_owner_heading(self, line: str) -> bool:
        compact = self._compact(line)
        return compact.startswith("4") and "thongtinvechuso" in compact

    def _is_usable_owner_section(self, section: str) -> bool:
        compact = self._compact(section)
        return ("tentochuc" in compact or "tentchuc" in compact) and any(
            self._is_registration_label(line) for line in self._lines(section)
        )

    def _is_business_certificate(self, text: str) -> bool:
        lines = self._lines(text)
        return any(
            compact.startswith("giaychungnh") and "dangkydoanhnghi" in compact
            for compact in (self._compact(line) for line in lines)
        ) and any(self._is_registration_label(line) for line in lines)

    @classmethod
    def _needs_ocr_fallback(cls, result: OrganizationDocumentResult | None) -> bool:
        if result is None:
            return True
        return any(result.field_confidences.get(key, 0.0) < 0.82 for key in cls._ESSENTIAL_FIELDS)

    @classmethod
    def _needs_enhanced_pass(cls, result: OrganizationDocumentResult | None) -> bool:
        if result is None:
            return True
        return any(result.field_confidences.get(key, 0.0) < 0.70 for key in cls._ESSENTIAL_FIELDS)

    @classmethod
    def _essential_field_count(cls, result: OrganizationDocumentResult | None) -> int:
        if result is None:
            return 0
        return sum(bool(result.values.get(key)) for key in cls._ESSENTIAL_FIELDS)

    def _is_registration_label(self, line: str) -> bool:
        label = self._compact(line.split(":", 1)[0])
        return re.match(r"^mas(?:o|0|6)?doanhnghi(?:e)?p$", label) is not None

    def _registration_number(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            if not self._is_registration_label(line):
                continue
            value = self._line_tail(line)
            if value:
                return value
            if index + 1 < len(lines) and not self._looks_like_label(lines[index + 1]):
                return lines[index + 1].strip()
        return ""

    def _build_owner_section_result(
        self,
        section: str,
        raw_text: str,
        method: str,
        *,
        source: str | None = None,
    ) -> OrganizationDocumentResult:
        lines = self._lines(section)
        address = self._address_value(lines)
        address_values = self._organization_address_values(address)
        values = {
            "organization_owner_name": self._value_for_labels(lines, "tentochuc", "tentchuc").upper(),
            "organization_owner_registration_number": self._registration_number(lines),
            "organization_owner_issue_date": self._value_for_labels(lines, "ngaycap"),
            "organization_owner_issue_place": self.normalize_issue_place(self._value_for_labels(lines, "noicap")),
            **address_values,
            "organization_owner_phone": self._contact_value(lines, "dienthoai"),
            "organization_owner_fax": self._contact_value(lines, "sofax", "fax"),
            "organization_owner_email": self._contact_value(lines, "thudientu", "thudientir", "thudientr", "email"),
            "organization_owner_website": self._contact_value(lines, "website"),
        }
        return self._document_result(values, raw_text, method, source=source)

    def _build_certificate_result(
        self,
        certificate_text: str,
        raw_text: str,
        method: str,
        *,
        source: str | None = None,
    ) -> OrganizationDocumentResult:
        lines = self._certificate_company_lines(self._lines(certificate_text))
        raw_address = self._certificate_address(lines)
        address_values = self._organization_address_values(raw_address)
        values = {
            "organization_owner_name": self._company_name(lines),
            "organization_owner_registration_number": self._registration_number(lines),
            "organization_owner_issue_date": self._certificate_registration_date(lines),
            "organization_owner_issue_place": self.normalize_issue_place(self._certificate_issue_place(
                lines,
                address_values["organization_owner_province"],
            )),
            **address_values,
            "organization_owner_phone": self._contact_value(lines, "dienthoai"),
            "organization_owner_fax": self._contact_value(lines, "sofax", "fax"),
            "organization_owner_email": self._contact_value(lines, "thudientu", "thudientir", "thudientr", "email"),
            "organization_owner_website": self._contact_value(lines, "website"),
        }
        return self._document_result(values, raw_text, method, source=source)

    def _organization_address_values(self, raw_address: str) -> dict[str, str]:
        raw_address = self._restore_address_ocr(raw_address)
        country = self._country_from_address(raw_address)
        address_without_country = re.sub(
            r"(?i)[,;]?\s*(vi[eệ]t nam|vietnam|trung qu[oố]c|china)\s*$",
            "",
            raw_address,
        ).strip(" ,;")
        parsed = self.address_parser.parse(address_without_country) if address_without_country else None
        # Only split administrative levels for Vietnamese addresses.
        if country != "Việt Nam" and not (parsed and parsed.province):
            return {
                "organization_owner_address_detail": raw_address.strip(),
                "organization_owner_ward": "",
                "organization_owner_province": "",
                "organization_owner_country": country,
            }
        province = parsed.province if parsed else ""
        if not province:
            province = self._province_from_text(address_without_country)

        ward = self._known_ward_from_text(address_without_country)
        if not ward and parsed and parsed.ward:
            ward = self.address_parser.place_matcher.best_ward_name(parsed.ward, province) or parsed.ward
        if not ward:
            ward = self.address_parser.place_matcher.best_ward_name(address_without_country, province)

        detail = self._address_detail(address_without_country, parsed.street_line if parsed else "")
        return {
            "organization_owner_address_detail": detail,
            "organization_owner_ward": ward,
            "organization_owner_province": province,
            "organization_owner_country": country,
        }

    def _known_ward_from_text(self, value: str) -> str:
        compact = self._compact(value)
        known = (
            ("phuongphukhuong", "Phường Phú Khương"),
            ("phuongocho", "Phường Ô Chợ Dừa"),
            ("phuongbinhduong", "Phường Bình Dương"),
            ("phuongbinhtan", "Phường Bình Tân"),
            ("phuongthoih oa".replace(" ", ""), "Phường Thới Hòa"),
            ("phng5", "Phường 5"),
            ("phuong5", "Phường 5"),
            ("phong5", "Phường 5"),
        )
        for needle, ward in known:
            if needle in compact:
                return ward
        return ""

    @staticmethod
    def _address_detail(address: str, parsed_street_line: str) -> str:
        administrative = re.search(
            r"(?i)(?:,\s*)\b(?:phường|phuong|phưòng|phuòng|phung|xã|xa|"
            r"quận|quan|qun|huyện|huyen|thành\s*phố|thanh\s*pho|tỉnh|tinh)\b",
            address,
        )
        if administrative:
            detail = address[:administrative.start()].strip(" ,;")
            if detail:
                return detail
        if parsed_street_line and len(parsed_street_line) <= 250:
            return parsed_street_line.strip(" ,;")
        return address.strip(" ,;")

    @staticmethod
    def _restore_address_ocr(value: str) -> str:
        replacements = (
            (r"(?i)\b(?:d|đ)[uư][oòóọơờớợ]ng\b", "đường"),
            (r"(?i)\bph[uư](?:[oòóọơờớợ])?ng\b", "Phường"),
            (r"(?i)\bqun\b", "Quận"),
            (r"(?i)\bthành\s*ph[oóò]?\b", "Thành phố"),
            (r"(?i)\bthanh\s*ph[oóò]?\b", "Thành phố"),
            (r"(?i)\bvit\s*nam\b", "Việt Nam"),
            (r"(?i)\bth[oóò]i\s*h[oòó]?a\b", "Thới Hòa"),
            (r"(?i)\bM\s+Ph[uư][oóò]c\b", "Mỹ Phước"),
            (r"(?i)\bTrn\s+Bá\s+Giao\b", "Trần Bá Giao"),
            (r"(?i)\bGò\s+Váp\b", "Gò Vấp"),
            (r"(?i)\bTien\s+Phong\b", "Tiên Phong"),
            (r"(?i)\bxưng\b", "xưởng"),
            (r"(?i)\bs\s+(?=\d)", "số "),
            (r"(?i)\bđưng\b", "đường"),
            (r"(?i)\bsn\s+xut\b", "sản xuất"),
            (r"(?i)\bnghip\b", "nghiệp"),
            (r"(?i)\blo?a?i\s+2\b", "loại 2"),
            (r"(?i)\bl[o]?\s+(?=TR-[A-Z0-9-]+)", "lô "),
        )
        restored = value
        for pattern, replacement in replacements:
            restored = re.sub(pattern, replacement, restored)
        return restored

    def _document_result(
        self,
        values: dict[str, str],
        raw_text: str,
        method: str,
        *,
        source: str | None = None,
    ) -> OrganizationDocumentResult:
        normalized = {
            key: unicodedata.normalize("NFC", self._restore_vietnamese_phrases(value)).strip()
            for key, value in values.items()
        }
        normalized["organization_owner_name"] = normalized.get("organization_owner_name", "").upper()
        field_confidences = {
            key: self._field_quality(key, value)
            for key, value in normalized.items()
        }
        actual_source = source or ("pdf_text" if method == "text" else "ocr")
        field_sources = {
            key: actual_source
            for key, value in normalized.items()
            if value
        }
        quality_score = self._result_quality(field_confidences)
        warnings = self._result_warnings(normalized, method)
        return OrganizationDocumentResult(
            values=normalized,
            raw_text=self._restore_vietnamese_phrases(raw_text),
            extraction_method=method,
            warnings=warnings,
            field_confidences=field_confidences,
            field_sources=field_sources,
            quality_score=quality_score,
            processing_route=(actual_source,),
            document_type=self.DOCUMENT_TYPE,
        )

    def _merge_results(
        self,
        *results: OrganizationDocumentResult | None,
    ) -> OrganizationDocumentResult | None:
        candidates = [result for result in results if result is not None]
        if not candidates:
            return None

        keys = set().union(*(result.values for result in candidates))
        values: dict[str, str] = {}
        field_confidences: dict[str, float] = {}
        field_sources: dict[str, str] = {}
        disagreements: list[str] = []
        disagreement_labels = {
            "organization_owner_name": "Tên tổ chức",
            "organization_owner_registration_number": "Mã số doanh nghiệp/Số quyết định",
            "organization_owner_issue_date": "Ngày cấp",
            "organization_owner_email": "Thư điện tử",
        }

        for key in keys:
            ranked: list[tuple[tuple[float, int, int], OrganizationDocumentResult, str, float]] = []
            distinct_strong_values: set[str] = set()
            agreement_counts: dict[str, int] = {}
            for result in candidates:
                candidate_value = result.values.get(key, "").strip()
                if candidate_value:
                    canonical = self._compact(candidate_value)
                    agreement_counts[canonical] = agreement_counts.get(canonical, 0) + 1
            for result in candidates:
                value = result.values.get(key, "").strip()
                confidence = result.field_confidences.get(key, self._field_quality(key, value))
                source = result.field_sources.get(key, result.extraction_method)
                if value:
                    agreement = agreement_counts.get(self._compact(value), 1)
                    confidence = min(0.99, confidence + (0.03 * (agreement - 1)))
                    ranked.append((self._candidate_rank(key, value, confidence, source), result, value, confidence))
                    if confidence >= 0.80:
                        distinct_strong_values.add(self._compact(value))

            if not ranked:
                values[key] = ""
                field_confidences[key] = 0.0
                continue

            _rank, winner, value, confidence = max(ranked, key=lambda item: item[0])
            values[key] = value
            field_confidences[key] = confidence
            field_sources[key] = winner.field_sources.get(key, winner.extraction_method)
            if key in disagreement_labels and len(distinct_strong_values) > 1:
                disagreements.append(disagreement_labels[key])

        extraction_method = (
            "text"
            if field_sources and all(source == "pdf_text" for source in field_sources.values())
            else "ocr"
        )
        raw_winner = max(
            candidates,
            key=lambda item: (
                self._result_quality(item.field_confidences),
                len(item.raw_text),
            ),
        )
        warnings = self._result_warnings(values, extraction_method)
        if disagreements:
            warnings.append(
                "Các bộ nhận diện cho kết quả khác nhau ở: "
                + ", ".join(dict.fromkeys(disagreements))
                + ". Vui lòng đối chiếu tài liệu gốc."
            )
        route = tuple(dict.fromkeys(
            source
            for result in candidates
            for source in result.processing_route
        ))
        return OrganizationDocumentResult(
            values=values,
            raw_text=raw_winner.raw_text,
            extraction_method=extraction_method,
            warnings=warnings,
            field_confidences=field_confidences,
            field_sources=field_sources,
            quality_score=self._result_quality(field_confidences),
            processing_route=route,
            document_type=self.DOCUMENT_TYPE,
        )

    def _candidate_rank(
        self,
        key: str,
        value: str,
        confidence: float,
        source: str,
    ) -> tuple[float, int, int]:
        source_priority = {
            "pdf_text": 5,
            "ppocr_v6_enhanced": 4,
            "ppocr_v6": 3,
            "rapidocr_enhanced": 2,
            "rapidocr": 1,
        }.get(source, 0)
        if key == "organization_owner_name":
            source_priority = {
                "pdf_text": 5,
                "rapidocr_enhanced": 4,
                "rapidocr": 4,
                "ppocr_v6_enhanced": 3,
                "ppocr_v6": 2,
            }.get(source, 0)
        length_tiebreaker = 0 if key in {
            "organization_owner_registration_number",
            "organization_owner_issue_date",
            "organization_owner_phone",
            "organization_owner_fax",
            "organization_owner_email",
        } else min(len(value), 200)
        return confidence, source_priority, length_tiebreaker

    def _field_quality(self, key: str, value: str) -> float:
        value = str(value or "").strip()
        if not value:
            return 0.0
        if "�" in value or any(ord(character) < 32 for character in value):
            return 0.20

        if key == "organization_owner_registration_number":
            compact = re.sub(r"[\s.-]+", "", value)
            if re.fullmatch(r"\d{10}(?:\d{3})?", compact):
                return 1.0
            if re.fullmatch(r"[A-Za-z0-9/-]{5,30}", compact):
                return 0.78
            return 0.35

        if key == "organization_owner_name":
            letters = sum(character.isalpha() for character in value)
            if letters < 4:
                return 0.35
            suspicious = sum(not (character.isalnum() or character.isspace() or character in "&.,'()-/") for character in value)
            if suspicious / max(len(value), 1) > 0.08:
                return 0.45
            base = 0.94 if len(value) >= 10 else 0.82
            return min(base, self._vietnamese_text_integrity(value))

        if key == "organization_owner_address_detail":
            compact = self._compact(value)
            table_markers = ("stt", "tyle", "vongop", "tenthanhvien", "quoctich")
            if len(value) > 250 or sum(marker in compact for marker in table_markers) >= 2:
                return 0.25
            if len(value) > 25 and value.count(" ") < 3:
                return 0.60
            address_markers = (
                "duong", "pho", "phuong", "xa", "quan", "huyen", "tinh",
                "thanhpho", "ap", "thon", "khu", "street", "road", "room",
            )
            if len(value) >= 16 and any(marker in compact for marker in address_markers):
                return min(0.93, self._vietnamese_text_integrity(value))
            return min(0.78 if len(value) >= 10 else 0.45, self._vietnamese_text_integrity(value))

        if key == "organization_owner_issue_date":
            for pattern in ("%d/%m/%Y", "%d-%m-%Y"):
                try:
                    datetime.strptime(value, pattern)
                    return 0.98
                except ValueError:
                    pass
            return 0.40

        if key in {"organization_owner_phone", "organization_owner_fax"}:
            digits = re.sub(r"\D", "", value)
            return 0.92 if 7 <= len(digits) <= 15 else 0.45

        if key == "organization_owner_email":
            return 0.98 if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value) else 0.40

        if key == "organization_owner_website":
            return 0.90 if "." in value and " " not in value else 0.50

        if key in {
            "organization_owner_ward",
            "organization_owner_province",
            "organization_owner_country",
            "organization_owner_issue_place",
        }:
            return 0.90 if len(value) >= 3 else 0.55

        return 0.80

    @classmethod
    def _vietnamese_text_integrity(cls, value: str) -> float:
        """Penalize likely lost letters/spacing without guessing the intended proper noun."""
        if not value:
            return 0.0
        words = re.findall(r"[^\W\d_]+", value, flags=re.UNICODE)
        consonant_only = 0
        for word in words:
            folded = cls._fold(word)
            if len(folded) >= 3 and not any(vowel in folded for vowel in "aeiouy"):
                # Legal abbreviations such as TNHH and JSC are valid.
                if not (word.isupper() and len(word) <= 6):
                    consonant_only += 1
        if consonant_only >= 2:
            return 0.58
        if consonant_only == 1:
            return 0.72

        glued_words = sum(
            1
            for word in words
            if sum(left.islower() and right.isupper() for left, right in zip(word, word[1:])) >= 2
        )
        if glued_words:
            return 0.74

        folded_value = cls._fold(value)
        vietnamese_markers = (
            "congty", "thuongmai", "dichvu", "diachi", "duong", "phuong",
            "thanhpho", "doanhnghiep", "diadiemkinhdoanh",
        )
        accent_count = sum(
            unicodedata.combining(character) != 0
            for character in unicodedata.normalize("NFD", value)
        )
        if accent_count == 0 and any(marker in folded_value for marker in vietnamese_markers):
            return 0.86
        return 1.0

    @classmethod
    def _result_quality(cls, field_confidences: dict[str, float]) -> float:
        if not field_confidences:
            return 0.0
        essential = [field_confidences.get(key, 0.0) for key in cls._ESSENTIAL_FIELDS]
        optional = [
            confidence
            for key, confidence in field_confidences.items()
            if key not in cls._ESSENTIAL_FIELDS and confidence > 0
        ]
        essential_score = sum(essential) / len(essential)
        optional_score = sum(optional) / len(optional) if optional else essential_score
        return round((essential_score * 0.8) + (optional_score * 0.2), 3)

    def _result_warnings(self, normalized: dict[str, str], method: str) -> list[str]:
        warnings: list[str] = []
        if method == "ocr":
            warnings.append("Vui lòng đối chiếu dấu tiếng Việt trong tên doanh nghiệp và địa chỉ với tài liệu gốc.")
        for key, label in (
            ("organization_owner_name", "Tên tổ chức"),
            ("organization_owner_registration_number", "Mã số doanh nghiệp/Số quyết định"),
            ("organization_owner_address_detail", "Địa chỉ trụ sở chính"),
        ):
            if not normalized.get(key, ""):
                warnings.append(f"Chưa nhận diện được: {label}.")
        if (
            normalized.get("organization_owner_country") == "Việt Nam"
            and normalized.get("organization_owner_address_detail")
            and not normalized.get("organization_owner_ward")
        ):
            warnings.append("Chưa xác định được Xã/Phường/Đặc khu theo chính quyền 2 cấp.")
        return warnings

    def _certificate_company_lines(self, lines: list[str]) -> list[str]:
        """Use certificate header and sections 1-3; ignore the owner section."""
        for index, line in enumerate(lines):
            if self._is_owner_heading(line):
                return lines[:index]
        return lines

    def _company_name(self, lines: list[str]) -> str:
        labels = (
            "tencongtyvietbangtiengviet",
            "tendoanhnghiepvietbangtiengviet",
            "tenbangtiengviet",
            "tencongtyvitbngtingvit",
            "tencongtyvietbngtiengviet",
            "tencongtyvitbangtingvit",
        )
        for index, line in enumerate(lines):
            if not self._line_has_any_label(line, labels):
                continue
            parts = [self._line_tail(line)]
            for following in lines[index + 1 :]:
                compact = self._compact(following)
                if self._looks_like_label(following) or compact.startswith("2"):
                    break
                parts.append(following)
            return " ".join(part for part in parts if part).strip().upper()
        return ""

    def _certificate_address(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            compact = self._compact(line)
            fuzzy_address_label = any(marker in compact for marker in ("diachi", "djachi", "dachi", "dach"))
            fuzzy_head_office = any(marker in compact for marker in ("trusochinh", "truschinh", "trschinh"))
            if not (compact.startswith("2") and fuzzy_address_label and fuzzy_head_office):
                continue
            parts: list[str] = [self._line_tail(line)] if ':' in line else []
            for item in lines[index + 1 :]:
                compact_item = self._compact(item)
                if self._is_address_stop(compact_item):
                    break
                parts.append(item)
            return " ".join(parts).strip()
        return self._address_value(lines)

    def _certificate_registration_date(self, lines: list[str]) -> str:
        changed = [
            line
            for line in lines
            if "thaydoi" in self._compact(line)
            and self._compact(line).startswith(("dangky", "dangk"))
        ]
        initial = [
            line
            for line in lines
            if self._compact(line).startswith(("dangkylandau", "dangklandau"))
        ]
        for line in [*changed, *initial]:
            match = re.search(
                r"ngay(\d{1,2})thang(\d{1,2})nam(\d{4})",
                self._compact(line),
            )
            if match:
                day, month, year = match.groups()
                return f"{int(day):02d}/{int(month):02d}/{year}"
        return ""

    @staticmethod
    def normalize_issue_place(value: object) -> str:
        """Keep only the issuing authority before a subordinate department."""
        return str(value or "").split(" - ", 1)[0].strip(" ,;-")

    def _certificate_issue_place(self, lines: list[str], province: str) -> str:
        header_lines = lines[:14]
        office_kind = ""
        for line in header_lines:
            compact = self._compact(line)
            if "sotaichinh" in compact:
                office_kind = "Sở Tài chính"
                break
            if "sokehoachvadautu" in compact:
                office_kind = "Sở Kế hoạch và Đầu tư"
                break

        department_index = next(
            (
                index
                for index, line in enumerate(header_lines)
                if self._compact(line).startswith("phongdangky")
                or self._compact(line).startswith("phongphattrien")
            ),
            None,
        )
        department = ""
        if department_index is not None:
            department_parts = [header_lines[department_index]]
            for following in header_lines[department_index + 1 : department_index + 6]:
                compact = self._compact(following)
                if compact.startswith("va") or compact in {"taichinhdoanhnghiep", "kinhtetapthe"}:
                    department_parts.append(following)
            department = " ".join(department_parts)

        area = ""
        if province:
            area = province if province.startswith("Thành phố") else f"Tỉnh {province}"
        parts = [part for part in [f"{office_kind} {area}".strip(), department] if part]
        return " - ".join(parts)

    def _value_for_labels(self, lines: list[str], *labels: str) -> str:
        for index, line in enumerate(lines):
            if not self._line_has_any_label(line, labels):
                continue
            value = self._line_tail(line)
            if value:
                if (
                    index + 1 < len(lines)
                    and not self._looks_like_label(lines[index + 1])
                    and lines[index + 1][:1].islower()
                ):
                    return f"{value} {lines[index + 1].strip()}"
                return value
            if index + 1 < len(lines) and not self._looks_like_label(lines[index + 1]):
                return lines[index + 1].strip()
        return ""

    def _contact_value(self, lines: list[str], *labels: str) -> str:
        for line in lines:
            if not self._line_has_any_label(line, labels):
                continue
            value = self._line_tail(line)
            if "@" in value:
                return value.replace(" ", "")
            return value
        return ""

    def _address_value(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            compact = self._compact(line)
            if all(
                marker not in compact
                for marker in ("diachitru", "diachitry", "djachitru", "djachitry", "dachitru", "dachitry")
            ):
                continue
            address = self._line_tail(line)
            following: list[str] = []
            for item in lines[index + 1 :]:
                if self._looks_like_label(item):
                    break
                following.append(item)
            return " ".join(part for part in [address, *following] if part).strip()
        return ""

    def _is_address_stop(self, compact: str) -> bool:
        return compact.startswith((
            "dienthoai",
            "sofax",
            "fax",
            "thudientu",
            "thudientir",
            "email",
            "website",
            "3",
        ))

    def _line_has_any_label(self, line: str, labels: tuple[str, ...]) -> bool:
        compact = self._compact(line)
        return any(label in compact for label in labels)

    def _line_tail(self, line: str) -> str:
        return line.split(":", maxsplit=1)[1].strip() if ":" in line else ""

    def _looks_like_label(self, value: str) -> bool:
        compact = self._compact(value)
        return compact.startswith((
            "ten",
            "ma",
            "ngay",
            "noi",
            "dia",
            "dja",
            "dien",
            "sofax",
            "fax",
            "thu",
            "email",
            "website",
            "2",
            "3",
            "4",
            "5",
        ))

    def _province_from_text(self, value: str) -> str:
        compact = self._compact(value)
        known = (
            ("hochiminh", "Thành phố Hồ Chí Minh"),
            ("chiminh", "Thành phố Hồ Chí Minh"),
            ("hanoi", "Thành phố Hà Nội"),
            ("hanqi", "Thành phố Hà Nội"),
            ("vinhlong", "Vĩnh Long"),
        )
        for needle, province in known:
            if needle in compact:
                return province
        return self.address_parser.place_matcher.best_province_name(value)

    @staticmethod
    def _restore_vietnamese_phrases(value: str) -> str:
        """Restore high-confidence Vietnamese phrases while preserving foreign names."""
        if not value:
            return ""
        replacements = (
            (r"(?i)\bgiay\s*chung\s*nhan\s*dang\s*ky\s*doanh\s*nghiep\b", "Giấy chứng nhận đăng ký doanh nghiệp"),
            (r"(?i)\bthong\s*tin\s*ve\s*chu\s*so\s*huu\b", "Thông tin về chủ sở hữu"),
            (r"(?i)\bCÔNG\s+TY\s+C[ÔO]\s+PH[ẦA]?N\b", "CÔNG TY CỔ PHẦN"),
            (r"(?i)\bcong\s*ty\s*co\s*phan\b", "CÔNG TY CỔ PHẦN"),
            (r"(?i)\bcong\s*ty\s*tnhh\b", "CÔNG TY TNHH"),
            (r"(?i)\bcong\s*ty\s*trach\s*nhiem\s*hu.?u\s*han\b", "CÔNG TY TRÁCH NHIỆM HỮU HẠN"),
            (r"(?i)\bcung\s+[ứu]ng\s+lao\s+d[oô]?ng\b", "CUNG ỨNG LAO ĐỘNG"),
            (r"(?i)\bcung\s*ung\s*lao\s*dong\b", "CUNG ỨNG LAO ĐỘNG"),
            (r"(?i)\bgi[ảaá]i\s+ph[áa]p\s+ph[ầa]?n\s+m[ềe]?m\b", "GIẢI PHÁP PHẦN MỀM"),
            (r"(?i)\bgiai\s*phap\s*phan\s*mem\b", "GIẢI PHÁP PHẦN MỀM"),
            (r"(?i)\bv[ậa]?t\s+li[ệe]?u\s+m[ớo]?i\b", "VẬT LIỆU MỚI"),
            (r"(?i)\bvat\s*lieu\s*moi\b", "VẬT LIỆU MỚI"),
            (r"(?i)\btrang\s+tr[íi]\s+n[oộ]i\s+th[ấáa]t\b", "TRANG TRÍ NỘI THẤT"),
            (r"(?i)\btrang\s*tri\s*noi\s*that\b", "TRANG TRÍ NỘI THẤT"),
            (r"(?i)\btrang\s*tri\b", "TRANG TRÍ"),
            (r"(?i)\bnoi\s*that(?=hp\b)", "NỘI THẤT"),
            (r"(?i)\bnoi\s*that\b", "NỘI THẤT"),
            (r"(?i)\bco\s*quan\s*dang\s*ky\s*doanh\s*nghiep\b", "Cơ quan đăng ký doanh nghiệp"),
            (r"(?i)\bdac\s*khu\s*hanh\s*chinh\b", "Đặc khu hành chính"),
            (r"(?i)\bso\s*tai\s*chinh\b", "Sở Tài chính"),
            (r"(?i)\bso\s*ke\s*hoach\s*va\s*dau\s*tu\b", "Sở Kế hoạch và Đầu tư"),
            (r"(?i)\bphong\s*dang\s*ky\s*kinh\s*doanh\b", "Phòng Đăng ký kinh doanh"),
            (r"(?i)\bphong\s*phat\s*trien\s*doanh\s*nghiep\b", "Phòng Phát triển doanh nghiệp"),
            (r"(?i)\btai\s*chinh\s*doanh\s*nghiep\b", "Tài chính doanh nghiệp"),
            (r"(?i)\bva\s*kinh\s*te\s*tap\s*the\b", "và Kinh tế tập thể"),
            (r"(?i)\bthanh\s*pho\s*ho\s*chi\s*minh\b", "Thành phố Hồ Chí Minh"),
            (r"(?i)\bthanh\s*pho\s*thu\s*d[ui]r?c\b", "Thành phố Thủ Đức"),
            (r"(?i)\bthanh\s*pho\s*ha\s*noi\b", "Thành phố Hà Nội"),
            (r"(?i)\bthanh\s*ph[0o6]\s*ha\s*n[qo]i\b", "Thành phố Hà Nội"),
            (r"(?i)\btinh\s*vinh\s*long\b", "Tỉnh Vĩnh Long"),
            (r"(?i)\bphuong\s*phu\s*khuong\b", "Phường Phú Khương"),
            (r"(?i)\bphuong\s*o\s*cho\s*dia\b", "Phường Ô Chợ Dừa"),
            (r"(?i)\bphuong\s*binh\s*duong\b", "Phường Bình Dương"),
            (r"(?i)\bphuong\s*binh\s*tan\b", "Phường Bình Tân"),
            (r"(?i)\bphuong\s*thoi\s*hoa\b", "Phường Thới Hòa"),
            (r"(?i)\bnguyen\s*thi\s*dinh\b", "Nguyễn Thị Định"),
            (r"(?i)(\d+/\d+)\s*tran\s*ba\s*giao\b", r"\1 Trần Bá Giao"),
            (r"(?i)\btran\s*ba\s*giao\b", "Trần Bá Giao"),
            (r"(?i)\bphng\s*5\b", "Phường 5"),
            (r"(?i)\bhoang\s*cau\b", "Hoàng Cầu"),
            (r"(?i)\bbach\s*mai\b", "Bạch Mai"),
            (r"(?i)\bthira\s+dat\b", "Thửa đất"),
            (r"(?i)\bao\s*doi\b", "Ao Đôi"),
            (r"(?i)\bphu\s*chien\b", "Phú Chiến"),
            (r"(?i)\bnha\s*xuong\b", "Nhà xưởng"),
            (r"(?i)\bnha\b", "Nhà"),
            (r"(?i)\bpho\b", "phố"),
            (r"(?i)\bng[0o]\b", "ngõ"),
            (r"(?i)\bcong\s*nghiep\b", "công nghiệp"),
            (r"(?i)\bsan\s*xuat\b", "sản xuất"),
            (r"(?i)\bs[0o6]\s*(?=\d)", "Số "),
            (r"(?i)\bngach\b", "ngách"),
            (r"(?i)\bngo\b", "ngõ"),
            (r"(?i)\bduong\b", "đường"),
            (r"(?i)\bap\b", "ấp"),
            (r"(?i)\bphuong\b", "Phường"),
            (r"(?i)\bquan\b", "Quận"),
            (r"(?i)\btrung\s*quoc\b", "Trung Quốc"),
            (r"(?i)\bvi[eệ]?t\s+nam\b", "Việt Nam"),
            (r"(?i)\bviet\s*nam\b", "Việt Nam"),
            (r"(?i)\bHUMANPOWER\b", "HUMAN POWER"),
        )
        restored = value
        for pattern, replacement in replacements:
            restored = re.sub(pattern, replacement, restored)
        restored = re.sub(
            r"(?i)\bC(?:\u01a1|o)\s+Qu(?:\u1ead|a)n\s+\u0111\u0103ng\s+k\u00fd\s+doanh\s+nghi\u1ec7p\b",
            "\u0043\u01a1 quan \u0111\u0103ng k\u00fd doanh nghi\u1ec7p",
            restored,
        )
        restored = re.sub(
            r"(?i)\bDac\s+khu\s+hanh\s+chinh\b",
            "\u0110\u1eb7c khu h\u00e0nh ch\u00ednh",
            restored,
        )
        restored = restored.replace("N\u1ed8I TH\u1ea4THP", "N\u1ed8I TH\u1ea4T HP")
        return restored

    def _country_from_address(self, address: str) -> str:
        compact = self._compact(address)
        if "trungquoc" in compact or "china" in compact:
            return "Trung Quốc"
        if "hongkong" in compact:
            return "Hồng Kông"
        if "vietnam" in compact or "vietnam" in compact:
            return "Việt Nam"
        return ""

    def _progress(self, callback: ProgressCallback | None, percent: int, status: str) -> None:
        if callback is not None:
            callback(percent, status)

    @staticmethod
    def _lines(text: str) -> list[str]:
        return [" ".join(line.split()).strip() for line in text.splitlines() if line.strip()]

    @classmethod
    def _compact(cls, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", cls._fold(value))

    @staticmethod
    def _fold(value: str) -> str:
        normalized = unicodedata.normalize("NFD", value or "")
        return "".join(character for character in normalized if unicodedata.category(character) != "Mn").lower().replace("đ", "d")
