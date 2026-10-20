"""Read a Vietnamese business-location registration certificate from a PDF."""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import fitz

from mingo_assistant.services.organization_documents.pdf_text import extract_certificate_text

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

    def extract_pdf(self, path: str | Path, progress_callback: ProgressCallback | None = None) -> OrganizationDocumentResult:
        pdf_path = Path(path)
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError("Vui lòng chọn Giấy chứng nhận đăng ký địa điểm kinh doanh dạng PDF.")
        if not pdf_path.is_file():
            raise FileNotFoundError("Không tìm thấy giấy chứng nhận địa điểm kinh doanh.")

        self._progress(progress_callback, 5, "Đang mở giấy chứng nhận địa điểm kinh doanh")
        with fitz.open(pdf_path) as document:
            direct_text = extract_certificate_text(document)
            detected_type = self._validate_expected_document_type(direct_text)
            if not detected_type:
                quick_text = self._extract_first_page_for_type_detection(document, progress_callback)
                self._validate_expected_document_type(quick_text)
            candidates: list[tuple[str, dict[str, str], str]] = []
            direct = self._parse_certificate(direct_text)
            if direct:
                candidates.append(("pdf_text", direct, direct_text))
            if not self._candidates_are_reliable(candidates):
                self._progress(progress_callback, 25, "Đang nhận diện giấy chứng nhận địa điểm kinh doanh")
                primary_text = self._extract_with_ocr(document, progress_callback)
                primary = self._parse_certificate(primary_text)
                if primary:
                    primary_source = (
                        "ppocr_v6"
                        if self._vietnamese_ocr and self._vietnamese_ocr.is_available
                        else "rapidocr"
                    )
                    candidates.append((primary_source, primary, primary_text))
                if not self._candidates_are_reliable(candidates):
                    self._progress(progress_callback, 75, "Đang đối chiếu chữ và số trên giấy chứng nhận")
                    fallback_text = self._extract_with_ocr(document, progress_callback, use_legacy=True)
                    fallback = self._parse_certificate(fallback_text)
                    if fallback:
                        candidates.append(("rapidocr", fallback, fallback_text))
                if not self._candidates_are_reliable(candidates):
                    self._progress(progress_callback, 90, "Đang tăng cường ảnh giấy chứng nhận khó đọc")
                    enhanced_text = self._extract_with_ocr(document, progress_callback, enhanced=True)
                    source = (
                        "ppocr_v6_enhanced"
                        if self._vietnamese_ocr and self._vietnamese_ocr.is_available
                        else "rapidocr_enhanced"
                    )
                    for candidate_text in dict.fromkeys((
                        enhanced_text,
                        *getattr(self, "_last_enhanced_text_candidates", ()),
                    )):
                        enhanced = self._parse_certificate(candidate_text)
                        if enhanced:
                            candidates.append((source, enhanced, candidate_text))

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
            agreeing_sources: dict[str, set[str]] = {}
            for option_source, option_value in options:
                canonical = self._agreement_key(option_value)
                agreeing_sources.setdefault(canonical, set()).add(option_source.removesuffix("_enhanced"))
            source, value = max(
                options,
                key=lambda item: self._value_rank(
                    key,
                    item[0],
                    item[1],
                    len(agreeing_sources[self._agreement_key(item[1])]),
                ),
            )
            values[key] = value
            sources[key] = source
            confidences[key] = min(
                0.99,
                self._field_quality_for_brc(key, value)
                + (0.03 * (len(agreeing_sources[self._agreement_key(value)]) - 1)),
            )
        reconciled_parent = self._parent_name_from_location(values)
        if reconciled_parent:
            values["parent_entity_name"] = reconciled_parent
            sources["parent_entity_name"] = sources.get(
                "location_business_name",
                sources.get("parent_entity_name", "ocr"),
            )
            confidences["parent_entity_name"] = self._field_quality_for_brc(
                "parent_entity_name",
                reconciled_parent,
            )
        if values.get("location_full_address"):
            values["location_full_address"] = self._enrich_address_accents(
                values["location_full_address"], candidates
            )
            address = self._address_fields(values["location_full_address"])
            values["location_full_address"] = self._canonicalize_address_places(
                values["location_full_address"],
                address,
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
        disagreement_labels = {
            "parent_entity_name": "Tên doanh nghiệp/chi nhánh chủ quản",
            "location_business_name": "Tên địa điểm kinh doanh",
            "location_full_address": "Địa chỉ địa điểm kinh doanh",
        }
        disagreements = [
            label
            for key, label in disagreement_labels.items()
            if len({
                self._agreement_key(data[key])
                for _source, data, _raw_text in candidates
                if data.get(key) and self._field_quality_for_brc(key, data[key]) >= .80
            }) > 1
        ]
        if disagreements:
            warnings.append(
                "Các bộ nhận diện cho kết quả khác nhau ở: "
                + ", ".join(disagreements)
                + ". Vui lòng đối chiếu tài liệu gốc."
            )
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

    def _value_rank(self, key: str, source: str, value: str, agreement: int = 1) -> tuple[float, int, int, int, int, int]:
        source_priority = {
            "pdf_text": 5,
            "ppocr_v6_enhanced": 4,
            "ppocr_v6": 3,
            "rapidocr_enhanced": 2,
            "rapidocr": 1,
        }.get(source, 0)
        length_tiebreaker = 0 if key in {
            "parent_entity_registration_number", "location_business_code",
            "location_phone", "location_fax", "location_email",
        } else min(len(value), 250)
        return (self._field_quality_for_brc(key, value), agreement, int(source == "pdf_text"),
                self._accent_count(value), length_tiebreaker, source_priority)

    def _candidates_are_reliable(
        self,
        candidates: list[tuple[str, dict[str, str], str]],
    ) -> bool:
        """Require reliable field content, not only non-empty strings."""
        if not candidates:
            return False
        best_scores: dict[str, float] = {}
        best_values: dict[str, str] = {}
        for key in self.REQUIRED + ("location_ward", "location_province"):
            options = [
                (self._field_quality_for_brc(key, values.get(key, "")), values.get(key, ""))
                for _source, values, _raw_text in candidates
                if values.get(key)
            ]
            if not options:
                return False
            best_scores[key], best_values[key] = max(options)
        if any(
            ":" in best_values.get(key, "")
            for key in ("parent_entity_name", "location_business_name", "location_full_address")
        ):
            return False
        required_scores = [best_scores[key] for key in self.REQUIRED]
        return min(required_scores) >= 0.78 and sum(required_scores) / len(required_scores) >= 0.86

    def _field_quality_for_brc(self, key: str, value: str) -> float:
        value = str(value or "").strip()
        if not value:
            return 0.0
        if key == "location_business_code":
            return 0.99 if re.fullmatch(r"\d{5}", value) else 0.35
        if key == "parent_entity_registration_number":
            return 0.99 if re.fullmatch(r"\d{10}(?:\d{3})?", value) else 0.35
        if key in {"parent_entity_name", "location_business_name"}:
            compact = self._compact(value)
            if ":" in value or "nuocngoai" in compact or "foreignlanguage" in compact:
                return 0.42
            return self._field_quality("organization_owner_name", value)
        if key in {"location_full_address", "location_address_detail"}:
            score = self._field_quality("organization_owner_address_detail", value)
            if key == "location_full_address" and not self._address_fields(value).get("location_province"):
                # An embedded OCR layer can contain a complete-looking but
                # damaged address. It must not outrank a readable image pass.
                score = min(score, .70)
            return score
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
                elif key in {"location_phone", "location_fax"}:
                    # Empty side-by-side fields can be reconstructed as
                    # ``Điện thoại: Fax:`` by a PDF text layer.  A contact
                    # number must contain enough digits to be real data.
                    if len(re.sub(r"\D", "", value)) < 6:
                        value = ""
                if value:
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
        if not match:
            return None
        number = int(match.group(1))
        tail = OrganizationDocumentService._compact(line[match.end():])
        headings = {1: ("ten",), 2: ("dia", "dja", "dach", "da"),
                    3: ("thongtin", "nguoi"), 4: ("thongtin", "doanhnghiep", "chinhanh"),
                    5: ("thongtin",)}
        return number if tail.startswith(headings[number]) else None

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
        if compact.startswith("ten") and (
            "ngoai" in compact or "foreignlanguage" in compact
        ):
            return True
        for marker in markers:
            if marker.isdigit():
                if section == int(marker):
                    return True
                continue  # a house number starting with 3 is not section 3
            if compact.startswith(marker):
                return True
        textual = tuple(marker for marker in markers if not marker.isdigit())
        looks_like_heading = section is not None or ":" in line or compact.startswith(("ten", "maso"))
        return bool(looks_like_heading and textual and self._label_matches(line, textual, threshold=0.72))

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

    def _canonicalize_address_places(
        self,
        full_address: str,
        address: dict[str, str],
    ) -> str:
        """Put official ward/province spellings back into the displayed address."""
        ward = address.get("location_ward", "")
        province = address.get("location_province", "")
        parts = [part.strip() for part in full_address.split(",") if part.strip()]
        for index, part in enumerate(parts):
            compact = self._compact(part)
            if ward and compact.startswith(("phuong", "phung", "xa", "thitran")):
                parts[index] = ward
            elif province and compact.startswith(("tinh", "thanhpho", "thanhph")):
                # A source can contain both Thành phố Thủ Đức and Thành phố
                # Hồ Chí Minh. Only replace the actual province segment.
                province_name = re.sub(r"^(?:tinh|thanhpho)", "", self._compact(province))
                part_name = re.sub(r"^(?:tinh|thanhpho|thanhph)", "", compact)
                if SequenceMatcher(None, part_name, province_name).ratio() >= .85:
                    parts[index] = province
                    if compact.startswith("tinh") and not self._compact(province).startswith("tinh"):
                        parts[index] = f"Tỉnh {province}"
        return ", ".join(parts)

    def _parent_name_from_location(self, values: dict[str, str]) -> str:
        """Use the repeated company suffix to repair a damaged parent name."""
        location_name = values.get("location_business_name", "")
        parent_name = values.get("parent_entity_name", "")
        if " - " not in location_name or not parent_name:
            return ""
        suffix = location_name.split(" - ", 1)[1].strip()
        if ":" in suffix or not self._compact(suffix).startswith("congty"):
            return ""
        similarity = SequenceMatcher(
            None,
            self._compact(suffix),
            self._compact(parent_name),
        ).ratio()
        if similarity < 0.80:
            return ""
        suffix_rank = (
            self._field_quality_for_brc("parent_entity_name", suffix),
            len(self._compact(suffix)),
            self._accent_count(suffix),
        )
        parent_rank = (
            self._field_quality_for_brc("parent_entity_name", parent_name),
            len(self._compact(parent_name)),
            self._accent_count(parent_name),
        )
        return suffix if suffix_rank > parent_rank else parent_name

    @staticmethod
    def _accent_count(value: str) -> int:
        return sum(
            unicodedata.combining(character) != 0
            for character in unicodedata.normalize("NFD", value)
        )

    @staticmethod
    def _code(value: str, digits: int) -> str:
        # A branch has a 13-digit identifier, sometimes printed as 10-3.
        # Never truncate it to its parent company's 10-digit identifier.
        suffix = r"(?:[ -]?\d{3})?" if digits == 10 else ""
        match = re.search(rf"(?<!\d)\d{{{digits}}}{suffix}(?!\d)", value)
        return re.sub(r"\D", "", match.group()) if match else ""

    def _restore_name(self, value: str) -> str:
        if " - " in value:
            prefix, suffix = value.split(" - ", 1)
            number = re.search(r"\s+(?:(?:S[ỐO0])\s+)?\d+[A-Z]?$", prefix, re.IGNORECASE)
            label = prefix[:number.start()] if number else prefix
            qualifier = number.group() if number else ""
            if len(label.split()) <= 4 and SequenceMatcher(None, self._compact(label), "diadiemkinhdoanh").ratio() >= 0.72:
                qualifier = re.sub(r"(?i)\bS[O0]\b", "SỐ", qualifier)
                value = f"ĐỊA ĐIỂM KINH DOANH{qualifier} - {suffix}"
        value = re.sub(r"(?i)\b[ĐD][ỊI]A\s+[ĐD]I[ỂÊE]M\s+KINH\s+DOANH\b", "ĐỊA ĐIỂM KINH DOANH", value)
        value = self._restore_vietnamese_phrases(value)
        # The company name can also occur as the suffix of a BRC location.
        prefix, separator, suffix = value.partition(" - ")
        if separator:
            return f"{prefix.upper()}{separator}{self._restore_company_name(suffix)}"
        return self._restore_company_name(value)

    def _restore_address(self, value: str) -> str:
        value = self._restore_address_ocr(value)
        value = re.sub(r"(?i)\bph(?:[uư]r?[oòóọơờớợ]ng|[uư]ng)\b", "Phường", value)
        value = re.sub(r"(?i)\bxa\b", "Xã", value)
        value = re.sub(r"(?i)\btinh\b", "Tỉnh", value)
        value = re.sub(r"(?i)\bthanh\s*ph(?:o|h)?\b", "Thành phố", value)
        value = re.sub(r"(?i)\bto\s+(?=\d)", "Tổ ", value)
        return self._restore_vietnamese_phrases(value).strip()
