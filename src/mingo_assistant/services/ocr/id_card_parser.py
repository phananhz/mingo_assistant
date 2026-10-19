from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher

from mingo_assistant.services.normalization.administrative_place_matcher import AdministrativePlaceMatcher


CCCD_ISSUE_PLACE_LEGACY = "Cục Cảnh sát Quản lý Hành chính về Trật tự Xã hội"
CCCD_ISSUE_PLACE_CURRENT = "Bộ Công an"
CURRENT_ID_CARD_START_DATE = date(2024, 7, 1)


@dataclass
class ExtractedIdCard:
    full_name: str = ""
    id_number: str = ""
    date_of_birth: str = ""
    gender: str = ""
    nationality: str = ""
    raw_permanent_address: str = ""
    permanent_address: str = ""
    address_status: str = ""
    address_message: str = ""
    place_of_origin: str = ""
    issue_date: str = ""
    issue_place: str = ""
    expiry_date: str = ""
    raw_text: str = ""
    unknown_lines: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_form_values(self) -> dict[str, str]:
        return {
            "legal_representative_full_name": self.full_name,
            "legal_representative_id_number": self.id_number,
            "legal_representative_date_of_birth": self.date_of_birth,
            "legal_representative_gender": self.gender,
            "legal_representative_nationality": self.nationality,
            "legal_representative_raw_permanent_address": self.raw_permanent_address,
            "legal_representative_permanent_address": self.permanent_address,
            "legal_representative_address_status": self.address_status,
            "legal_representative_address_message": self.address_message,
            "legal_representative_issue_date": self.issue_date,
            "legal_representative_issue_place": self.issue_place,
            "legal_representative_expiry_date": self.expiry_date,
        }


class IdCardParser:
    def __init__(self, place_matcher: AdministrativePlaceMatcher | None = None) -> None:
        self.place_matcher = place_matcher or AdministrativePlaceMatcher()

    def parse(self, raw_text: str) -> ExtractedIdCard:
        lines = [self._clean_line(line) for line in raw_text.splitlines()]
        lines = [line for line in lines if line]
        joined = "\n".join(lines)

        card = ExtractedIdCard(raw_text=raw_text)
        card.id_number = self._find_id_number(joined)
        card.date_of_birth = self._find_date_of_birth(lines, joined)
        card.gender = self._find_gender(lines) or self._gender_from_id_number(card.id_number)
        card.nationality = self._find_nationality(joined)
        card.full_name = self._find_name(lines)
        card.issue_date = self._find_issue_date(lines)
        card.issue_place = self._infer_issue_place(card.issue_date, joined)
        card.expiry_date = self._find_expiry(lines)
        raw_permanent_address = self._find_address(
            lines,
            ["thuong tru", "noi cu tru", "cu tru", "residence", "place of residence"],
        )
        self._set_card_permanent_address(card, raw_permanent_address)
        card.place_of_origin = self._find_address(
            lines,
            [
                "que quan",
                "noi dang ky khai sinh",
                "origin",
                "ongin",
                "place of origin",
                "place of birth",
                "nguyen quan",
            ],
        )
        card.place_of_origin = self.place_matcher.normalize_address(card.place_of_origin)
        completed_address = self._complete_residence_with_origin(
            card.permanent_address,
            card.place_of_origin,
        )
        if completed_address and completed_address != card.raw_permanent_address:
            normalized = self.place_matcher.analyze_address(completed_address)
            card.permanent_address = normalized.normalized_address
            card.address_status = normalized.status
            card.address_message = normalized.message
        card.unknown_lines = lines
        return card

    def parse_qr(self, qr_text: str) -> ExtractedIdCard:
        parts = [part.strip() for part in re.split(r"\|+", qr_text.strip())]
        parts = [part for part in parts if part]
        card = ExtractedIdCard(raw_text=qr_text)

        if len(parts) >= 7:
            card.id_number = self._cccd_number(parts[0])
            card.full_name = parts[2].upper()
            card.date_of_birth = self._format_compact_date(parts[3])
            card.gender = self._normalize_gender(parts[4]) or self._gender_from_id_number(card.id_number)
            self._set_card_permanent_address(card, parts[5])
            card.issue_date = self._format_compact_date(parts[6])
        elif len(parts) >= 6:
            card.id_number = self._cccd_number(parts[0])
            card.full_name = parts[1].upper()
            card.date_of_birth = self._format_compact_date(parts[2])
            card.gender = self._normalize_gender(parts[3]) or self._gender_from_id_number(card.id_number)
            self._set_card_permanent_address(card, parts[4])
            card.issue_date = self._format_compact_date(parts[5])
        else:
            card.warnings.append("Mã QR CCCD không đúng định dạng dữ liệu cá nhân thường gặp.")
            return card

        if not card.id_number:
            card.warnings.append("Mã QR không có số CCCD 12 số; thông tin CMND cũ đã được bỏ qua.")
        card.issue_place = self._infer_issue_place(card.issue_date, qr_text)
        card.nationality = "Vi\u1ec7t Nam"
        card.unknown_lines = parts
        return card

    def _set_card_permanent_address(self, card: ExtractedIdCard, raw_address: str) -> None:
        normalized = self.place_matcher.analyze_address(raw_address)
        card.raw_permanent_address = normalized.raw_address
        card.permanent_address = normalized.normalized_address
        card.address_status = normalized.status
        card.address_message = normalized.message
        if normalized.needs_confirmation and normalized.message:
            card.warnings.append(normalized.message)

    def _origin_from_residence(self, residence: str) -> str:
        if not residence:
            return ""
        parts = [part.strip(" ,.;") for part in residence.split(",") if part.strip(" ,.;")]
        if len(parts) >= 3:
            return ", ".join(parts[-3:])
        return residence
    def _clean_line(self, line: str) -> str:
        return " ".join(line.replace(":", ": ").split())

    def _fold(self, value: str) -> str:
        value = value.replace(chr(273), "d").replace(chr(272), "D")
        normalized = unicodedata.normalize("NFKD", value)
        ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return ascii_text.lower()

    def _similarity(self, left: str, right: str) -> float:
        return SequenceMatcher(None, left, right).ratio()

    def _find_id_number(self, text: str) -> str:
        matches = re.findall(r"\b\d{12}\b", text)
        return matches[0] if matches else ""

    def _cccd_number(self, value: str) -> str:
        digits = re.sub(r"\D", "", value or "")
        return digits if re.fullmatch(r"\d{12}", digits) else ""

    def _find_first_date(self, text: str) -> str:
        dates = self._collect_dates(text)
        if dates:
            return dates[0]
        return ""

    def _find_date_of_birth(self, lines: list[str], joined: str) -> str:
        keyword_date = self._find_date_after_keywords(lines, ["sinh", "birth", "dato", "duto"])
        if keyword_date:
            return keyword_date

        candidates = [item for item in self._collect_dates(joined) if self._is_plausible_birth_date(item)]
        if candidates:
            return candidates[0]
        dates = self._collect_dates(joined)
        return dates[0] if dates else ""

    def _collect_dates(self, text: str) -> list[str]:
        dates: list[str] = []
        for match in re.finditer(r"\b[0-9OolI]{1,2}\s*[/-]\s*[0-9OolI]{1,2}\s*[/-]\s*[0-9OolI]{4}\b", text):
            normalized = self._normalize_ocr_date(match.group(0))
            if normalized:
                dates.append(normalized)
        return dates

    def _is_plausible_birth_date(self, value: str) -> bool:
        day, month, year = self._date_parts(value)
        current_year = date.today().year
        return 1900 <= year <= current_year

    def _date_sort_key(self, value: str) -> tuple[int, int, int]:
        day, month, year = self._date_parts(value)
        return (year, month, day)

    def _date_parts(self, value: str) -> tuple[int, int, int]:
        day, month, year = value.split("/")
        return (int(day), int(month), int(year))

    def _normalize_ocr_date(self, value: str) -> str:
        fixed = value.translate(str.maketrans({"O": "0", "o": "0", "l": "1", "I": "1"}))
        parts = [part.strip() for part in re.split(r"[/-]", fixed)]
        if len(parts) != 3:
            return ""
        day, month, year = parts
        if not (day.isdigit() and month.isdigit() and year.isdigit()):
            return ""
        day_int = int(day)
        month_int = int(month)
        if not (1 <= day_int <= 31 and 1 <= month_int <= 12 and len(year) == 4):
            return ""
        return f"{day_int:02d}/{month_int:02d}/{year}"

    def _find_date_after_keywords(self, lines: list[str], keywords: list[str]) -> str:
        folded_keywords = [self._fold(keyword) for keyword in keywords]
        for index, line in enumerate(lines):
            folded = self._fold(line)
            if any(keyword in folded for keyword in folded_keywords):
                nearby = " ".join(lines[max(0, index - 2) : index + 5])
                date = self._find_first_date(nearby)
                if date and self._is_plausible_birth_date(date):
                    return date
        return ""

    def _find_expiry(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            folded = self._fold(line)
            if "gia tri" in folded or "gia tr" in folded or "co gia" in folded or "expiry" in folded:
                date = self._find_first_date(line)
                if date:
                    return date
                nearby = " ".join(lines[index : index + 3])
                return self._find_first_date(nearby)
        return ""

    def _find_issue_date(self, lines: list[str]) -> str:
        markers = ["ngay cap", "date of issue", "year of issue", "ngay, thang, nam cap"]
        for index, line in enumerate(lines):
            folded = self._fold(line)
            if not any(marker in folded for marker in markers):
                continue
            date_value = self._find_first_date(" ".join(lines[index : index + 4]))
            if date_value:
                return date_value
        return ""

    def _infer_issue_place(self, issue_date: str, raw_text: str = "") -> str:
        """Return one of the two issuing authorities used by the CCCD form.

        QR payloads contain the issue date but not the issuing authority. Cards
        issued from 01/07/2024 use the new Identity Card design displaying
        "Bộ Công an"; earlier CCCD cards use the C06 authority. When OCR has
        read an authority explicitly, that text takes precedence over the date.
        """
        folded = self._fold(raw_text)
        if "bo cong an" in folded or "ministry of public security" in folded:
            return CCCD_ISSUE_PLACE_CURRENT
        legacy_markers = (
            "cuc canh sat quan ly hanh chinh ve trat tu xa hoi",
            "cuc canh sat qlhc ve ttxh",
        )
        if any(marker in folded for marker in legacy_markers):
            return CCCD_ISSUE_PLACE_LEGACY

        try:
            day, month, year = self._date_parts(issue_date)
            issued_on = date(year, month, day)
        except (AttributeError, TypeError, ValueError):
            return ""
        if issued_on >= CURRENT_ID_CARD_START_DATE:
            return CCCD_ISSUE_PLACE_CURRENT
        return CCCD_ISSUE_PLACE_LEGACY

    def _find_gender(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            folded = self._fold(line).replace("ü", "u")
            if "sex" not in folded and "gioi tinh" not in folded:
                continue
            gender = self._gender_from_text(line)
            if gender:
                return gender
            for next_line in lines[index + 1 : index + 3]:
                if self._is_label_or_document_noise(next_line):
                    break
                gender = self._gender_from_text(next_line)
                if gender:
                    return gender
        return ""

    def _gender_from_text(self, value: str) -> str:
        folded = self._fold(value).replace("ü", "u")
        if "viet nam" in folded:
            return ""
        if "nữ" in value.lower() or re.search(r"\b(nu|female|f)\b", folded):
            return "Nữ"
        if re.search(r"\b(nam|male|m)\b", folded):
            return "Nam"
        return ""

    def _gender_from_id_number(self, id_number: str) -> str:
        if not re.fullmatch(r"\d{12}", id_number or ""):
            return ""
        gender_code = int(id_number[3])
        return "Nữ" if gender_code % 2 else "Nam"

    def _find_nationality(self, text: str) -> str:
        folded = self._fold(text)
        if "viet nam" in folded or "vnm" in folded:
            return "Việt Nam"
        return ""

    def _find_value_after_keywords(self, lines: list[str], keywords: list[str]) -> str:
        folded_keywords = [self._fold(keyword) for keyword in keywords]
        for index, line in enumerate(lines):
            folded = self._fold(line)
            if any(keyword in folded for keyword in folded_keywords):
                value = self._value_on_label_line(line, keywords)
                if value:
                    return value
                for next_line in lines[index + 1 : index + 4]:
                    if self._is_label_or_document_noise(next_line):
                        continue
                    return next_line.strip()
        return ""

    def _find_name(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            folded = self._fold(line)
            if "ho va ten" in folded or "full name" in folded:
                value = self._value_on_label_line(line, ["ho va ten", "full name"])
                if self._is_name_candidate(value):
                    return value.upper()
                for next_line in lines[index + 1 : index + 5]:
                    if self._is_name_candidate(next_line):
                        return next_line.strip().upper()

        candidates = [
            line
            for line in lines
            if self._is_name_candidate(line)
        ]
        return candidates[0].upper() if candidates else ""

    def _find_address(self, lines: list[str], keywords: list[str]) -> str:
        folded_keywords = [self._fold(keyword) for keyword in keywords]
        for index, line in enumerate(lines):
            if self._is_matching_address_marker(lines, index, folded_keywords):
                parts: list[str] = []
                if ":" in line:
                    value = line.split(":", 1)[1].strip()
                    if value:
                        parts.append(value)
                tail = self._address_tail_from_marker(line, folded_keywords)
                if not tail:
                    marker_block = " ".join(lines[index : index + 3])
                    tail = self._address_tail_from_marker(marker_block, folded_keywords)
                if tail:
                    parts.append(tail)
                for next_line in lines[index + 1 : index + 6]:
                    if self._is_current_address_marker(next_line, folded_keywords) or self._is_label_or_document_noise(next_line):
                        continue
                    if self._is_new_field(next_line) or self._is_other_address_marker(next_line, folded_keywords):
                        break
                    parts.append(next_line)
                address = self._join_ocr_address_lines(parts)
                if address:
                    return address
        return self._find_address_by_administrative_sequence(lines, folded_keywords)

    def _find_address_by_administrative_sequence(self, lines: list[str], folded_keywords: list[str]) -> str:
        marker_index = self._find_noisy_address_marker_index(lines, folded_keywords)
        if marker_index < 0:
            return ""
        parts: list[str] = []
        for line in lines[marker_index + 1 : marker_index + 8]:
            if self._is_current_address_marker(line, folded_keywords) or self._is_label_or_document_noise(line):
                continue
            if self._is_new_field(line) or self._is_other_address_marker(line, folded_keywords):
                break
            if self._looks_like_address_value(line):
                parts.append(line)
        return self._join_ocr_address_lines(parts)

    def _join_ocr_address_lines(self, parts: list[str]) -> str:
        """Rebuild an OCR address without treating every line break as a comma."""
        result = ""
        seen: set[str] = set()
        for part in parts:
            clean = part.strip(" ,.;")
            if not clean or self._is_label_or_document_noise(clean):
                continue
            key = self._fold(clean)
            if key in seen:
                continue
            seen.add(key)
            if not result:
                result = clean
                continue
            if re.search(r"[-/]$", result):
                result = result.rstrip(" -/") + " " + clean
            elif self._starts_administrative_address_part(clean):
                result += ", " + clean
            else:
                result += " " + clean
        return result

    def _starts_administrative_address_part(self, value: str) -> bool:
        folded = self._fold(value)
        prefixes = ("xa ", "phuong ", "thi tran ", "huyen ", "quan ", "thi xa ", "tinh ", "thanh pho ", "tp ")
        if folded.startswith(prefixes):
            return True
        # Unlabelled historical tails are accepted only when the administrative
        # dataset resolves the complete tail unambiguously.
        return self.place_matcher.analyze_address(value).status in {"converted", "current"}

    def _find_noisy_address_marker_index(self, lines: list[str], folded_keywords: list[str]) -> int:
        for index, line in enumerate(lines):
            if self._is_current_address_marker(line, folded_keywords) or self._is_noisy_address_marker(line, folded_keywords):
                return index
        return -1

    def _value_on_label_line(self, line: str, keywords: list[str]) -> str:
        if ":" in line:
            value = line.split(":", 1)[1].strip()
            if value and not self._is_label_or_document_noise(value):
                return value
        value = line
        replacements = [
            r"ho\s+va\s+ten",
            r"ho\s+v[aà]\s+t[eê]n",
            r"h[oọ]\s+v[aà]\s+t[eê]n",
            r"full\s+name",
            r"ful\s+name",
            r"full\s+narne",
            r"fullname",
            r"qu[oó]c\s+t[iị]ch",
            r"quoc\s+tich",
            r"nationality",
            r"gi[oơ]i\s+t[ií]nh",
            r"gioi\s+tinh",
            r"sex",
        ]
        for pattern in replacements:
            value = re.sub(pattern, "", value, flags=re.IGNORECASE)
        value = value.strip(" :/-")
        folded_value = self._fold(value)
        if any(marker in folded_value for marker in ["full", "ful", "name", "narne", "ho va", "ten"]):
            return ""
        if value and not self._is_label_or_document_noise(value):
            return value
        return ""

    def _is_name_candidate(self, line: str) -> bool:
        clean = line.strip(" :/-")
        folded = self._fold(clean)
        if not clean or len(clean.split()) < 2 or re.search(r"\d", clean):
            return False
        if self._is_label_or_document_noise(clean):
            return False
        blocked = [
            "can cuoc",
            "identity",
            "citizen",
            "full name",
            "ful name",
            "full narne",
            "fullname",
            "name",
            "ho va ten",
            "quoc tich",
            "nationality",
            "ngay sinh",
            "birth",
            "republic",
            "independence",
            "freedom",
            "happiness",
            "doc lap",
            "tu do",
            "hanh phuc",
            "que quan",
            "origin",
            "thuong tru",
            "residence",
            "gia tri",
            "expiry",
        ]
        return not any(word in folded for word in blocked)

    def _is_matching_address_marker(self, lines: list[str], index: int, folded_keywords: list[str]) -> bool:
        line = lines[index]
        if self._is_current_address_marker(line, folded_keywords):
            return True
        if self._is_noisy_address_marker(line, folded_keywords):
            return True
        folded = self._fold(line).strip(" :")
        if folded != "noi" or not self._expects_residence_marker(folded_keywords):
            return False
        nearby = " ".join(lines[index : index + 3])
        return self._is_current_address_marker(nearby, folded_keywords) or self._is_noisy_address_marker(nearby, folded_keywords)

    def _is_current_address_marker(self, line: str, folded_keywords: list[str]) -> bool:
        folded = self._fold(line)
        return any(keyword in folded for keyword in folded_keywords)

    def _is_noisy_address_marker(self, line: str, folded_keywords: list[str]) -> bool:
        folded = self._fold(line)
        if self._expects_origin_marker(folded_keywords):
            return self._has_fuzzy_marker(
                folded,
                ["que quan", "noi dang ky khai sinh", "place of origin", "place of birth", "place of ongin", "qui quan", "placo"],
            )
        if self._expects_residence_marker(folded_keywords):
            return self._has_fuzzy_marker(
                folded,
                ["noi thuong tru", "noi cu tru", "cu tru", "thuong tru", "uong uu", "place of residence", "place of residenc", "residenc"],
            )
        return False

    def _has_fuzzy_marker(self, folded: str, markers: list[str]) -> bool:
        compact = folded.replace(" ", "")
        for marker in markers:
            marker_folded = self._fold(marker)
            if marker_folded in folded or marker_folded.replace(" ", "") in compact:
                return True
            if self._similarity(compact, marker_folded.replace(" ", "")) >= 0.72:
                return True
            for token_count in range(2, 5):
                words = folded.split()
                windows = [" ".join(words[index : index + token_count]) for index in range(max(0, len(words) - token_count + 1))]
                if any(self._similarity(window.replace(" ", ""), marker_folded.replace(" ", "")) >= 0.76 for window in windows):
                    return True
        return False

    def _looks_like_address_value(self, line: str) -> bool:
        folded = self._fold(line)
        if len(folded) <= 2:
            return False
        if any(marker in folded for marker in ["xa", "phuong", "quan", "huyen", "tinh", "thanh pho", "tp"]):
            return True
        normalized = self.place_matcher.normalize_address(line)
        return self._fold(normalized) != folded

    def _is_other_address_marker(self, line: str, folded_keywords: list[str]) -> bool:
        folded = self._fold(line)
        residence_keywords = ["thuong tru", "noi cu tru", "cu tru", "residence", "place of residence"]
        origin_keywords = ["que quan", "noi dang ky khai sinh", "origin", "ongin", "place of origin", "place of birth", "nguyen quan"]
        has_residence = any(marker in folded for marker in ["thuong tru", "noi cu tru", "cu tru", "residence"]) or self._is_noisy_address_marker(line, residence_keywords)
        has_origin = any(marker in folded for marker in ["que quan", "dang ky khai sinh", "origin", "ongin", "place of birth"]) or self._is_noisy_address_marker(line, origin_keywords)
        if self._expects_residence_marker(folded_keywords):
            return has_origin
        if self._expects_origin_marker(folded_keywords):
            return has_residence
        return False

    def _expects_residence_marker(self, folded_keywords: list[str]) -> bool:
        return any(keyword in {"thuong tru", "noi cu tru", "cu tru", "residence", "place of residence"} for keyword in folded_keywords)

    def _expects_origin_marker(self, folded_keywords: list[str]) -> bool:
        return any(
            keyword in {"que quan", "noi dang ky khai sinh", "origin", "ongin", "place of origin", "place of birth", "nguyen quan"}
            for keyword in folded_keywords
        )

    def _is_address_marker_only(self, line: str) -> bool:
        folded = self._fold(line).strip(" :")
        markers = {
            "noi",
            "thuong tru",
            "noi cu tru",
            "cu tru",
            "place of residence",
            "que quan",
            "noi dang ky khai sinh",
            "place of origin",
            "place of birth",
        }
        return folded in markers

    def _address_tail_from_marker(self, line: str, folded_keywords: list[str]) -> str:
        if self._expects_residence_marker(folded_keywords):
            patterns = [
                r"place\s+of\s+residence",
                r"noi\s+thuong\s+tru",
                r"n[oơ]i\s+th[uư][oờ]ng\s+tr[uú]",
                r"noi\s+cu\s+tru",
                r"n[oơ]i\s+c[uư]\s+tr[uú]",
            ]
        else:
            patterns = [
                r"place\s+of\s+origin",
                r"place\s+of\s+birth",
                r"place\s+o[ií]\s+on?gin",
                r"que\s+quan",
                r"qu[eê]\s+qu[aá]n",
                r"noi\s+dang\s+ky\s+khai\s+sinh",
            ]
        latest_end = -1
        for pattern in patterns:
            matches = list(re.finditer(pattern, line, flags=re.IGNORECASE))
            if matches:
                latest_end = max(latest_end, matches[-1].end())
        tail = line[latest_end:].strip(" .:-I|/") if latest_end >= 0 else ""
        tail = self._trim_other_address_marker_tail(tail, folded_keywords)
        if tail and not self._is_label_or_document_noise(tail):
            return tail
        return ""

    def _trim_other_address_marker_tail(self, tail: str, folded_keywords: list[str]) -> str:
        if not tail:
            return tail
        if self._expects_residence_marker(folded_keywords):
            patterns = [r"place\s+of\s+origin", r"place\s+of\s+birth", r"place\s+o[ií]\s+on?gin", r"que\s+quan", r"qu[eê]\s+qu[aá]n", r"noi\s+dang\s+ky\s+khai\s+sinh"]
        else:
            patterns = [r"place\s+of\s+residence", r"noi\s+thuong\s+tru", r"n[oơ]i\s+th[uư][oờ]ng\s+tr[uú]", r"noi\s+cu\s+tru", r"n[oơ]i\s+c[uư]\s+tr[uú]"]
        patterns.extend(
            [
                r"ng[aà]y\s*,?\s*th[aá]ng\s*,?\s*n[aă]m\s+c[aấ]p",
                r"ng[aà]y\s+c[aấ]p",
                r"date\s*,?\s*month\s*,?\s*year\s+of\s+issue",
                r"date\s+of\s+issue",
                r"c[oó]\s+gi[aá]\s+tr[iị]",
                r"date\s+of\s+expiry",
            ]
        )
        cut_at: int | None = None
        for pattern in patterns:
            match = re.search(pattern, tail, flags=re.IGNORECASE)
            if match and (cut_at is None or match.start() < cut_at):
                cut_at = match.start()
        return tail[:cut_at].strip(" ,.;:-/") if cut_at is not None else tail

    def _is_new_field(self, line: str) -> bool:
        folded = self._fold(line)
        markers = [
            "ngay",
            "date",
            "quoc tich",
            "nationality",
            "gioi tinh",
            "sex",
            "gia tri",
            "gia tr",
            "co gia",
            "expiry",
            "thuong tru",
            "noi cu tru",
            "cu tru",
            "residence",
            "que quan",
            "noi dang ky khai sinh",
            "place of birth",
            "origin",
        ]
        return any(marker in folded for marker in markers)

    def _is_label_or_document_noise(self, line: str) -> bool:
        raw = line.strip().lower()
        if raw.startswith("---") or raw.startswith("scan "):
            return True
        folded = self._fold(line).strip(" :/-")
        if not folded:
            return True
        exact_markers = {
            "0o",
            "o0",
            "oo",
            "so",
            "no",
            "ho va ten",
            "full name",
            "ful name",
            "full narne",
            "fullname",
            "ngay sinh",
            "date of birth",
            "gioi tinh",
            "sex",
            "quoc tich",
            "nationality",
            "que quan",
            "place of origin",
            "noi thuong tru",
            "place of residence",
            "date of expiry",
            "date of oxpiry",
            "citizen identity card",
            "socialist republic of viet nam",
            "independence",
            "freedom",
            "happiness",
            "doc lap",
            "tu do",
            "hanh phuc",
        }
        if folded in exact_markers:
            return True
        fuzzy_markers = [
            "place oi ongin",
            "place oi origin",
            "place of ongin",
        ]
        if any(marker in folded for marker in fuzzy_markers):
            return True
        if folded.startswith("scan ") or folded.startswith("qr data"):
            return True
        return False

    def _dedupe_address_parts(self, parts: list[str]) -> str:
        result: list[str] = []
        seen: set[str] = set()
        for part in parts:
            clean = part.strip(" ,.;")
            if not clean or self._is_label_or_document_noise(clean):
                continue
            key = self._fold(clean)
            if key in seen:
                continue
            seen.add(key)
            result.append(clean)
        return ", ".join(result)

    def _complete_residence_with_origin(self, residence: str, origin: str) -> str:
        if not residence or not origin:
            return residence
        folded_residence = self._fold(residence)
        folded_origin = self._fold(origin)
        administrative_markers = [
            "phuong",
            "xa",
            "thi tran",
            "quan",
            "huyen",
            "thi xa",
            "tp",
            "thanh pho",
            "tinh",
        ]
        if any(marker in folded_residence for marker in administrative_markers):
            return residence
        if not any(marker in folded_origin for marker in administrative_markers):
            return residence
        return self._dedupe_address_parts([residence, origin])

    def _format_compact_date(self, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) != 8:
            return self._normalize_ocr_date(value) or value
        return f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"

    def _normalize_gender(self, value: str) -> str:
        folded = self._fold(value).replace("ü", "u")
        if folded in {"f", "female", "nu", "nữ"}:
            return "Nữ"
        if folded in {"m", "male", "nam"}:
            return "Nam"
        return value

