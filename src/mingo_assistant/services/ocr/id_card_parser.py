from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher

from mingo_assistant.services.normalization.administrative_place_matcher import AdministrativePlaceMatcher


@dataclass
class ExtractedIdCard:
    full_name: str = ""
    id_number: str = ""
    date_of_birth: str = ""
    gender: str = ""
    nationality: str = ""
    permanent_address: str = ""
    place_of_origin: str = ""
    issue_date: str = ""
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
            "legal_representative_permanent_address": self.permanent_address,
            "legal_representative_place_of_origin": self.place_of_origin,
            "legal_representative_issue_date": self.issue_date,
            "legal_representative_expiry_date": self.expiry_date,
        }


@dataclass
class MrzData:
    full_name: str = ""
    id_number: str = ""
    date_of_birth: str = ""
    gender: str = ""
    nationality: str = ""
    expiry_date: str = ""


@dataclass
class QrData:
    full_name: str = ""
    id_number: str = ""
    date_of_birth: str = ""
    gender: str = ""
    permanent_address: str = ""
    issue_date: str = ""


class IdCardParser:
    def __init__(self, place_matcher: AdministrativePlaceMatcher | None = None) -> None:
        self.place_matcher = place_matcher or AdministrativePlaceMatcher()

    def parse(self, raw_text: str) -> ExtractedIdCard:
        lines = [self._clean_line(line) for line in raw_text.splitlines()]
        lines = [line for line in lines if line]
        joined = "\n".join(lines)

        qr = self._parse_qr_payload(raw_text)
        mrz = self._parse_mrz(lines)

        card = ExtractedIdCard(raw_text=raw_text)
        card.id_number = qr.id_number or self._find_id_number(joined) or mrz.id_number
        card.date_of_birth = (
            qr.date_of_birth
            or self._find_date_after_keywords(lines, ["sinh", "birth"])
            or self._find_first_date(joined)
            or mrz.date_of_birth
        )
        card.gender = qr.gender or self._find_gender(lines) or mrz.gender or self._gender_from_id_number(card.id_number)
        card.nationality = self._find_value_after_keywords(lines, ["quoc tich", "nationality"]) or self._find_nationality(joined) or mrz.nationality or "Việt Nam"
        card.full_name = qr.full_name or self._find_name(lines) or mrz.full_name
        card.permanent_address = qr.permanent_address or self._find_address(lines, ["thuong tru", "residence", "place of residence"])
        card.place_of_origin = self._find_address(lines, ["que quan", "origin", "ongin", "place of origin", "nguyen quan"])
        card.place_of_origin = self.place_matcher.normalize_address(card.place_of_origin)
        card.permanent_address = self.place_matcher.normalize_address(card.permanent_address)
        card.permanent_address = self._complete_residence_with_origin(card.permanent_address, card.place_of_origin)
        card.issue_date = qr.issue_date or self._find_date_after_keywords(lines, ["ngay cap", "date of issue", "date, month, year"])
        card.expiry_date = self._find_expiry(lines) or mrz.expiry_date
        card.unknown_lines = lines
        card.warnings = self._build_warnings(card, mrz)
        return card

    def _clean_line(self, line: str) -> str:
        return " ".join(line.replace("|", " ").replace(":", ": ").split())

    def _fold(self, value: str) -> str:
        value = value.replace(chr(273), "d").replace(chr(272), "D")
        normalized = unicodedata.normalize("NFKD", value)
        ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return ascii_text.lower()

    def _similarity(self, left: str, right: str) -> float:
        return SequenceMatcher(None, left, right).ratio()

    def _find_id_number(self, text: str) -> str:
        matches = re.findall(r"\b\d{9,12}\b", text)
        if not matches:
            return ""
        return max(matches, key=len)

    def _find_first_date(self, text: str) -> str:
        match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", text)
        return match.group(0) if match else ""

    def _find_date_after_keywords(self, lines: list[str], keywords: list[str]) -> str:
        folded_keywords = [self._fold(keyword) for keyword in keywords]
        for index, line in enumerate(lines):
            folded = self._fold(line)
            if any(keyword in folded for keyword in folded_keywords):
                date = self._find_first_date(line)
                if date:
                    return date
                if index + 1 < len(lines):
                    return self._find_first_date(lines[index + 1])
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
                address = self._dedupe_address_parts(parts)
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
        return self._dedupe_address_parts(parts)

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
            return self._has_fuzzy_marker(folded, ["que quan", "place of origin", "place of ongin", "qui quan", "placo"])
        if self._expects_residence_marker(folded_keywords):
            return self._has_fuzzy_marker(folded, ["noi thuong tru", "thuong tru", "uong uu", "place of residence", "place of residenc", "residenc"])
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
        residence_keywords = ["thuong tru", "residence", "place of residence"]
        origin_keywords = ["que quan", "origin", "ongin", "place of origin", "nguyen quan"]
        has_residence = any(marker in folded for marker in ["thuong tru", "residence"]) or self._is_noisy_address_marker(line, residence_keywords)
        has_origin = any(marker in folded for marker in ["que quan", "origin", "ongin"]) or self._is_noisy_address_marker(line, origin_keywords)
        if self._expects_residence_marker(folded_keywords):
            return has_origin
        if self._expects_origin_marker(folded_keywords):
            return has_residence
        return False

    def _expects_residence_marker(self, folded_keywords: list[str]) -> bool:
        return any(keyword in {"thuong tru", "residence", "place of residence"} for keyword in folded_keywords)

    def _expects_origin_marker(self, folded_keywords: list[str]) -> bool:
        return any(keyword in {"que quan", "origin", "ongin", "place of origin", "nguyen quan"} for keyword in folded_keywords)

    def _is_address_marker_only(self, line: str) -> bool:
        folded = self._fold(line).strip(" :")
        markers = {
            "noi",
            "thuong tru",
            "place of residence",
            "que quan",
            "place of origin",
        }
        return folded in markers

    def _address_tail_from_marker(self, line: str, folded_keywords: list[str]) -> str:
        if self._expects_residence_marker(folded_keywords):
            patterns = [
                r"place\s+of\s+residence",
                r"noi\s+thuong\s+tru",
                r"n[oơ]i\s+th[uư][oờ]ng\s+tr[uú]",
            ]
        else:
            patterns = [
                r"place\s+of\s+origin",
                r"place\s+o[ií]\s+on?gin",
                r"que\s+quan",
                r"qu[eê]\s+qu[aá]n",
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
            patterns = [r"place\s+of\s+origin", r"place\s+o[ií]\s+on?gin", r"que\s+quan", r"qu[eê]\s+qu[aá]n"]
        else:
            patterns = [r"place\s+of\s+residence", r"noi\s+thuong\s+tru", r"n[oơ]i\s+th[uư][oờ]ng\s+tr[uú]"]
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
            "residence",
            "que quan",
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

    def _parse_qr_payload(self, text: str) -> QrData:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if line.count("|") < 4:
                continue
            parts = [part.strip() for part in line.split("|")]
            if not parts or not re.fullmatch(r"\d{9,12}", parts[0]):
                continue
            return QrData(
                id_number=parts[0],
                full_name=parts[2].upper() if len(parts) > 2 else "",
                date_of_birth=self._format_compact_date(parts[3]) if len(parts) > 3 else "",
                gender=self._normalize_gender(parts[4]) if len(parts) > 4 else "",
                permanent_address=parts[5] if len(parts) > 5 else "",
                issue_date=self._format_compact_date(parts[6]) if len(parts) > 6 else "",
            )
        return QrData()

    def _parse_mrz(self, lines: list[str]) -> MrzData:
        mrz_lines = []
        for line in lines:
            compact = re.sub(r"\s+", "", line.upper())
            if "<<" in compact or compact.startswith("IDVNM"):
                compact = compact.replace("«", "<").replace(" ", "")
                mrz_lines.append(compact)

        for index, line in enumerate(mrz_lines):
            if not line.startswith("IDVNM") or index + 2 >= len(mrz_lines):
                continue
            line2 = mrz_lines[index + 1]
            line3 = mrz_lines[index + 2]
            return MrzData(
                id_number=self._mrz_id_number(line),
                date_of_birth=self._format_mrz_date(line2[0:6], is_birth=True),
                gender=self._normalize_gender(line2[7:8] if len(line2) > 7 else ""),
                expiry_date=self._format_mrz_date(line2[8:14], is_birth=False) if len(line2) >= 14 else "",
                nationality="Việt Nam" if "VNM" in line2 else "",
                full_name=self._parse_mrz_name(line3),
            )
        return MrzData()

    def _mrz_id_number(self, line: str) -> str:
        digits = re.sub(r"\D", "", line[5:])
        if len(digits) >= 12:
            return digits[:12]
        if len(digits) >= 9:
            return digits[:9]
        return ""

    def _parse_mrz_name(self, line: str) -> str:
        name = line.replace("<", " ").strip()
        return " ".join(name.split())

    def _format_mrz_date(self, value: str, *, is_birth: bool) -> str:
        if not re.fullmatch(r"\d{6}", value):
            return ""
        yy = int(value[0:2])
        mm = value[2:4]
        dd = value[4:6]
        current_yy = datetime.now().year % 100
        if is_birth:
            year = 2000 + yy if yy <= current_yy else 1900 + yy
        else:
            year = 2000 + yy
        return f"{dd}/{mm}/{year}"

    def _format_compact_date(self, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) != 8:
            return value
        return f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"

    def _normalize_gender(self, value: str) -> str:
        folded = self._fold(value).replace("ü", "u")
        if folded in {"f", "female", "nu", "nữ"}:
            return "Nữ"
        if folded in {"m", "male", "nam"}:
            return "Nam"
        return value

    def _build_warnings(self, card: ExtractedIdCard, mrz: MrzData) -> list[str]:
        warnings: list[str] = []
        if mrz.full_name and card.full_name and self._fold(mrz.full_name) not in self._fold(card.full_name):
            warnings.append(f"Tên mặt trước khác MRZ mặt sau: '{card.full_name}' và '{mrz.full_name}'.")
        if mrz.gender and card.gender and mrz.gender != card.gender:
            warnings.append(f"Giới tính mặt trước khác MRZ mặt sau: '{card.gender}' và '{mrz.gender}'.")
        if mrz.date_of_birth and card.date_of_birth and mrz.date_of_birth != card.date_of_birth:
            warnings.append(f"Ngày sinh mặt trước khác MRZ mặt sau: '{card.date_of_birth}' và '{mrz.date_of_birth}'.")
        return warnings
