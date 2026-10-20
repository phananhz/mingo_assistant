"""Certificate extraction for amendment dossiers; existing procedures stay unchanged."""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import replace
from difflib import SequenceMatcher

from mingo_assistant.services.organization_documents.organization_document_service import (
    OrganizationDocumentResult, OrganizationDocumentService,
)


class BusinessAmendmentDocumentService(OrganizationDocumentService):
    RECOGNIZED_FIELDS = ("organization_owner_name", "organization_owner_registration_number")
    # This workflow only displays name/code. Unused addresses or representative
    # fields must not trigger a full-document OCR pass after these are read.
    _ESSENTIAL_FIELDS = RECOGNIZED_FIELDS

    def extract_pdf(self, path, progress_callback=None) -> OrganizationDocumentResult:
        self._refinement_used = False
        result = super().extract_pdf(path, progress_callback)
        route = result.processing_route + (("vietocr_lines",) if self._refinement_used else ())
        values = {key: result.values.get(key, "") for key in self.RECOGNIZED_FIELDS}
        warnings = ["Đối chiếu tên doanh nghiệp và mã số doanh nghiệp/mã số thuế với PDF trước khi áp dụng."]
        if not values["organization_owner_name"]:
            warnings.append("Chưa nhận diện được tên doanh nghiệp.")
        if not re.fullmatch(r"\d{10}(?:\d{3})?", values["organization_owner_registration_number"]):
            warnings.append("Mã số doanh nghiệp cần kiểm tra lại.")
        return replace(result, values=values, warnings=warnings, processing_route=route,
                       field_sources={key: value for key, value in result.field_sources.items() if key in values},
                       field_confidences={key: value for key, value in result.field_confidences.items() if key in values})

    def _extract_page_with_ocr(self, legacy_engine, image_bytes: bytes, *, use_legacy: bool = False) -> str:
        if use_legacy or not self._vietnamese_ocr or not self._vietnamese_ocr.is_available:
            return super()._extract_page_with_ocr(legacy_engine, image_bytes, use_legacy=use_legacy)
        try:
            import cv2
            import numpy as np
            from PIL import Image
            from mingo_assistant.services.ocr.vietnamese_line_refiner import VietnameseLineRefiner

            lines, _ = self._vietnamese_ocr._get_engine()(image_bytes, text_score=0.25)
            lines = list(lines or [])
            if not hasattr(self, "_line_refiner"):
                self._line_refiner = VietnameseLineRefiner(self._vietnamese_ocr.model_dir)
            refiner = self._line_refiner
            if not refiner.weights.is_file():
                return "\n".join(str(line[1]) for line in lines)
            image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
            # Refine names and addresses only. Numeric fields and contacts keep
            # their original OCR candidates for the shared numeric validation.
            address_section = False
            for index, (box, text, score) in enumerate(lines):
                folded = self._compact(text)
                if folded.startswith("2") and "chi" in folded:
                    address_section = True
                elif folded.startswith(("dienthoai", "dien", "sofax", "fax", "3", "kt", "truong", "phong")):
                    address_section = False
                name_line = any(marker in folded for marker in ("congty", "hoch", "hovaten", "chucdanh", "churcdanh"))
                address_line = address_section or ("chi" in folded and any(marker in folded for marker in ("lien", "lin", "thuong")))
                if not (name_line or address_line) or "@" in text or len(text) < 8 or any(marker in folded for marker in ("nuocngoai", "nucngoai", "viettat", "vittt")):
                    continue
                xs, ys = zip(*box)
                crop = image[max(0, int(min(ys)) - 2):int(max(ys)) + 3,
                             max(0, int(min(xs)) - 2):int(max(xs)) + 3]
                if not crop.size:
                    continue
                candidate, confidence = refiner._load().predict(Image.fromarray(crop[:, :, ::-1]), return_prob=True)
                accepted = refiner.accept(text, candidate, confidence)
                if ":" in text and ":" in candidate and any(marker in folded for marker in ("hoch", "hovaten")):
                    original_name, candidate_name = text.split(":", 1)[1].strip(), candidate.split(":", 1)[1].strip()
                    accepted = (confidence >= 0.8 and not re.search(r"\d", original_name + candidate_name)
                                and SequenceMatcher(None, self._compact(original_name), self._compact(candidate_name)).ratio() >= 0.85
                                and len(original_name.split()) == len(candidate_name.split()))
                    candidate = text.split(":", 1)[0] + ": " + candidate_name
                if accepted:
                    # Accepted text must preserve every numeric token and stay
                    # very close to the detected line, including its label.
                    # Keep existing Vietnamese accents when the only difference
                    # is a different accent on the same word (e.g. lô/lộ).
                    old_words = re.findall(r"\w+", text)
                    new_parts = re.findall(r"\w+|\W+", candidate)
                    old_index = 0
                    for part_index, part in enumerate(new_parts):
                        if not part.isalnum():
                            continue
                        if old_index < len(old_words):
                            old = old_words[old_index]
                            if address_line and not name_line and self._compact(old) == self._compact(part) and self._vietnamese_marks(old):
                                new_parts[part_index] = old
                        old_index += 1
                    lines[index] = (box, "".join(new_parts), float(confidence))
                    self._refinement_used = True
            return "\n".join(str(line[1]).strip() for line in lines)
        except Exception:
            logging.getLogger(__name__).exception("Amendment line refinement unavailable")
            return super()._extract_page_with_ocr(legacy_engine, image_bytes, use_legacy=use_legacy)

    def _extract_supported_document(self, text, method, *, source=None):
        # An amendment requires the registered company, not the owner's papers.
        if not self._is_business_certificate(text):
            return None
        return self._build_certificate_result(text, text, method, source=source)

    def _label_matches(self, label: str, candidates: tuple[str, ...]) -> bool:
        folded = re.sub(r"^\d+", "", self._compact(label))
        if folded.startswith("loaigiayto") and not any(candidate.startswith("loai") for candidate in candidates):
            return False
        return any(folded == candidate or SequenceMatcher(None, folded, candidate).ratio() >= 0.83
                   for candidate in candidates)

    def _value(self, lines: list[str], labels: tuple[str, ...], *, multiline=False) -> str:
        # Prefer exact labels anywhere in the section before fuzzy labels.
        # Otherwise "Loại giấy tờ" can win over "Số giấy tờ" farther below.
        candidates = []
        for index, line in enumerate(lines):
            label = line.split(":", 1)[0]
            if not self._label_matches(label, labels):
                continue
            folded = re.sub(r"^\d+", "", self._compact(label))
            score = max(SequenceMatcher(None, folded, candidate).ratio() for candidate in labels)
            candidates.append((score, -index, index, line))
        for _, _, index, line in sorted(candidates, reverse=True):
            parts = [line.split(":", 1)[1].strip()] if ":" in line else []
            for following in lines[index + 1:]:
                compact = self._compact(following)
                if ":" in following or re.match(r"^[1-9][.]\s*[A-Za-zÀ-ỹ]", following) or compact.startswith(("kt", "ttru", "truongphong", "photruong", "hotruong", "phongdang", "phongphat", "bangchu")):
                    break
                if parts and parts[0] and not multiline:
                    break
                parts.append(following)
                if not multiline:
                    break
            return " ".join(part for part in parts if part).strip()
        return ""

    def _merge_results(self, *results):
        result = super()._merge_results(*results)
        if result is None:
            return None
        labels = {"legal_representative_full_name": "Tên người đại diện", "legal_representative_id_number": "Số giấy tờ người đại diện",
                  "legal_representative_passport_number": "Hộ chiếu", "legal_representative_issue_date": "Ngày cấp giấy tờ",
                  "organization_capital": "Vốn điều lệ", "organization_owner_address_detail": "Địa chỉ trụ sở"}
        differing = []
        for key, label in labels.items():
            candidates = {unicodedata.normalize("NFC", item.values[key]).casefold().strip()
                          if key in {"legal_representative_full_name", "organization_owner_address_detail"}
                          else self._compact(item.values[key])
                          for item in results if item and item.values.get(key)}
            if len(candidates) > 1:
                differing.append(label)
        warnings = list(result.warnings)
        if differing:
            warnings.append("Các bộ OCR khác kết quả tại: " + ", ".join(differing) + ". Cần đối chiếu PDF.")
        return replace(result, warnings=list(dict.fromkeys(warnings)))

    def _date_from_line(self, line: str) -> str:
        match = re.search(r"ngay(\d{1,2})thang(\d{1,2})nam(\d{4})", self._compact(line))
        if match:
            day, month, year = match.groups()
            return f"{int(day):02d}/{int(month):02d}/{year}"
        match = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", line)
        if match:
            day, month, year = match.groups()
            return f"{int(day):02d}/{int(month):02d}/{year}"
        return ""

    @staticmethod
    def _numeric_value(text: str) -> str:
        match = re.search(r"\d[\d., ]*", text)
        return re.sub(r"\D", "", match.group()) if match else ""

    def _build_certificate_result(self, certificate_text, raw_text, method, *, source=None):
        base = super()._build_certificate_result(certificate_text, raw_text, method, source=source)
        all_lines = self._lines(certificate_text)
        # Stop at section 4 even for two-member companies whose heading differs
        # from the owner heading used by the existing organization parser.
        company_lines = []
        for line in all_lines:
            if re.match(r"^4\s*[.]", line):
                break
            company_lines.append(line)
        values = dict(base.values)
        values["organization_english_name"] = self._value(company_lines, ("tencongtyvietbangtiengnuocngoai", "tendoanhnghiepvietbangtiengnuocngoai"), multiline=True)
        values["organization_short_name"] = self._value(company_lines, ("tencongtyviettat", "tendoanhnghiepviettat"))
        values["organization_original_address"] = self._certificate_address(company_lines)
        values["organization_first_registration_date"] = next((self._date_from_line(line) for line in company_lines
                                                               if self._compact(line).startswith(("dangkylandau", "dangklandau"))), "")
        capital = self._value(company_lines, ("vondieule", "vondieu1e", "vondieul"))
        values["organization_capital"] = self._numeric_value(capital)
        values["organization_share_par_value"] = self._numeric_value(self._value(company_lines, ("menhgiacophan",)))
        values["organization_share_count"] = self._numeric_value(self._value(company_lines, ("tongsocophan",)))
        start = next((i for i, line in enumerate(all_lines)
                      if self._label_matches(line, ("nguoidaidientheophapluatcuacongty", "nguoidaidientheophapluatcuadoanhnghiep"))), None)
        representative = all_lines[start + 1:] if start is not None else []
        rep_values = {
            "full_name": self._value(representative, ("hochudemvaten", "hochurdemvaten", "hovaten")).upper(),
            "position": self._value(representative, ("chucdanh", "churcdanh")),
            "date_of_birth": self._date_from_line(self._value(representative, ("ngaythangnamsinh", "sinhngay"))),
            "gender": self._value(representative, ("gioitinh",)),
            "nationality": self._value(representative, ("quoctich",)),
            "id_number": self._value(representative, ("sodinhdanhcanhan", "s6dinhdanhcanhan", "sogiaytophaplycuacanhan", "sochungminhnhandan")),
            "passport_number": self._value(representative, ("hochieu nuocngoai".replace(" ", ""), "sohochieu", "hochieu")),
            "issue_date": self._date_from_line(self._value(representative, ("ngaycap",))),
            "issue_place": self._value(representative, ("noicap",), multiline=True),
            "permanent_address": self._value(representative, ("diachithuongtru",), multiline=True),
            "contact_address": self._value(representative, ("diachilienlac",), multiline=True),
        }
        gender = self._compact(rep_values["gender"])
        rep_values["gender"] = "Nam" if gender == "nam" else "Nữ" if gender in {"nu", "nir", "nitr", "n"} else rep_values["gender"]
        position = self._compact(rep_values["position"])
        if position in {"giamdoc", "giamdc", "giamd6c"}:
            rep_values["position"] = "Giám đốc"
        elif position in {"tonggiamdoc", "tonggiamdc", "tnggiamdc"}:
            rep_values["position"] = "Tổng giám đốc"
        if self._compact(rep_values["nationality"]) in {"trungquoc", "trungquc"}:
            rep_values["nationality"] = "Trung Quốc"
        for suffix, value in rep_values.items():
            values[f"legal_representative_{suffix}"] = value
        return self._document_result(values, raw_text, method, source=source)

    def _document_result(self, values, raw_text, method, *, source=None):
        result = super()._document_result(values, raw_text, method, source=source)
        preserved = dict(result.values)
        for key in ("organization_english_name", "organization_short_name", "organization_original_address"):
            if key in values:
                preserved[key] = unicodedata.normalize("NFC", values[key]).strip()
        return replace(result, values=preserved, raw_text=raw_text)

    def _is_address_stop(self, compact):
        return compact.startswith(("sfax", "dien", "thu")) or super()._is_address_stop(compact)

    @staticmethod
    def _vietnamese_marks(value):
        return sum(c in "àáạảãăắằặẳẵâấầậẩẫèéẹẻẽêếềệểễìíịỉĩòóọỏõôốồộổỗơớờợởỡùúụủũưứừựửữỳýỵỷỹđ" for c in value.casefold())

    def _candidate_rank(self, key, value, confidence, source):
        rank = super()._candidate_rank(key, value, confidence, source)
        if key in {"organization_owner_address_detail", "organization_original_address", "organization_owner_ward", "organization_owner_issue_place", "legal_representative_full_name", "legal_representative_position", "legal_representative_contact_address"}:
            marks = self._vietnamese_marks(value)
            # Quality first, diacritics second, then the existing source ranking.
            return rank[0], marks * 10 + rank[1], rank[2]
        return rank

    def _field_quality(self, key, value):
        if key == "legal_representative_full_name" and value:
            allowed = "abcdefghijklmnopqrstuvwxyzàáạảãăắằặẳẵâấầậẩẫèéẹẻẽêếềệểễìíịỉĩòóọỏõôốồộổỗơớờợởỡùúụủũưứừựửữỳýỵỷỹđ"
            if any(c.isalpha() and c not in allowed for c in value.casefold()):
                return 0.40
        if key == "organization_owner_issue_place" and value and "sở" not in value.casefold():
            return 0.60
        if key == "legal_representative_id_number" and value:
            return 0.98 if re.fullmatch(r"\d{9}|\d{12}", value.strip()) else 0.40
        if key == "legal_representative_passport_number" and value:
            return 0.80 if re.fullmatch(r"[A-Z0-9]{6,12}", value.strip()) else 0.40
        return super()._field_quality(key, value)

    def _result_warnings(self, normalized, method):
        warnings = super()._result_warnings(normalized, method)
        for key, label in (("organization_capital", "Vốn điều lệ"), ("legal_representative_full_name", "Người đại diện pháp luật")):
            if not normalized.get(key):
                warnings.append(f"Chưa nhận diện được: {label}.")
        if method == "ocr":
            warnings.append("Đối chiếu tên, giấy tờ và địa chỉ người đại diện với PDF; dữ liệu OCR cần xác nhận trước khi xuất.")
        return warnings
