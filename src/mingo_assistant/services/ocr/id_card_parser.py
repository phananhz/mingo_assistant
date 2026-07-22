from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime


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
    def parse(self, raw_text: str) -> ExtractedIdCard:
        lines = [self._clean_line(line) for line in raw_text.splitlines()]
        lines = [line for line in lines if line]
        joined = "\n".join(lines)

        qr = self._parse_qr_payload(joined)
        mrz = self._parse_mrz(lines)

        card = ExtractedIdCard(raw_text=raw_text)
        card.id_number = qr.id_number or self._find_id_number(joined) or mrz.id_number
        card.date_of_birth = (
            qr.date_of_birth
            or self._find_date_after_keywords(lines, ["sinh", "birth"])
            or self._find_first_date(joined)
            or mrz.date_of_birth
        )
        card.gender = qr.gender or self._find_gender(lines) or mrz.gender
        card.nationality = self._find_value_after_keywords(lines, ["quoc tich", "nationality"]) or self._find_nationality(joined) or mrz.nationality
        card.full_name = qr.full_name or self._find_name(lines) or mrz.full_name
        card.permanent_address = qr.permanent_address or self._find_address(lines, ["thuong tru", "residence", "place of residence"])
        card.place_of_origin = self._find_address(lines, ["que quan", "origin", "place of origin", "nguyen quan"])
        card.issue_date = qr.issue_date or self._find_date_after_keywords(lines, ["ngay cap", "date of issue", "date, month, year"])
        card.expiry_date = self._find_expiry(lines) or mrz.expiry_date
        card.unknown_lines = lines
        card.warnings = self._build_warnings(card, mrz)
        return card

    def _clean_line(self, line: str) -> str:
        return " ".join(line.replace("|", " ").replace(":", ": ").split())

    def _fold(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return ascii_text.lower()

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
            if "gia tri" in folded or "expiry" in folded:
                date = self._find_first_date(line)
                if date:
                    return date
                nearby = " ".join(lines[index : index + 3])
                return self._find_first_date(nearby)
        return ""

    def _find_gender(self, lines: list[str]) -> str:
        for line in lines:
            folded = self._fold(line).replace("ü", "u")
            if "sex" not in folded and "gioi tinh" not in folded:
                continue
            if re.search(r"\b(nu|female|f)\b", folded):
                return "Nữ"
            if re.search(r"\b(nam|male|m)\b", folded):
                return "Nam"

        folded_text = self._fold("\n".join(lines)).replace("viet nam", "").replace("ü", "u")
        if re.search(r"\b(nu|female)\b", folded_text):
            return "Nữ"
        if re.search(r"\b(nam|male)\b", folded_text):
            return "Nam"
        return ""

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
                if ":" in line:
                    value = line.split(":", 1)[1].strip()
                    if value:
                        return value
                if index + 1 < len(lines):
                    return lines[index + 1].strip()
        return ""

    def _find_name(self, lines: list[str]) -> str:
        for index, line in enumerate(lines):
            folded = self._fold(line)
            if "ho va ten" in folded or "full name" in folded:
                if ":" in line:
                    value = line.split(":", 1)[1].strip()
                    if value:
                        return value.upper()
                if index + 1 < len(lines):
                    return lines[index + 1].strip().upper()

        candidates = [
            line
            for line in lines
            if len(line.split()) >= 2
            and not re.search(r"\d", line)
            and not any(word in self._fold(line) for word in ["can cuoc", "identity", "quoc tich", "ngay sinh", "republic"])
        ]
        return candidates[0].upper() if candidates else ""

    def _find_address(self, lines: list[str], keywords: list[str]) -> str:
        folded_keywords = [self._fold(keyword) for keyword in keywords]
        for index, line in enumerate(lines):
            folded = self._fold(" ".join(lines[index : index + 3]))
            if any(keyword in folded for keyword in folded_keywords):
                parts: list[str] = []
                if ":" in line:
                    value = line.split(":", 1)[1].strip()
                    if value:
                        parts.append(value)
                marker_block = " ".join(lines[index : index + 3])
                tail = self._address_tail_from_marker(marker_block)
                if tail:
                    parts.append(tail)
                for next_line in lines[index + 1 : index + 6]:
                    if self._is_new_field(next_line):
                        break
                    if self._is_address_marker_only(next_line):
                        continue
                    parts.append(next_line)
                return ", ".join(parts).strip(" ,")
        return ""

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

    def _address_tail_from_marker(self, line: str) -> str:
        folded = self._fold(line)
        markers = ["place of residence", "place of origin", "noi thuong tru", "que quan"]
        for marker in markers:
            index = folded.find(marker)
            if index == -1:
                continue
            original_tail_start = min(len(line), index + len(marker))
            tail = line[original_tail_start:].strip(" .:-I|/")
            if tail:
                return tail
        return ""

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
            "expiry",
        ]
        return any(marker in folded for marker in markers)

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
