from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import fitz

from mingo_assistant.services.normalization.address_parser import AddressParser


ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True)
class OrganizationDocumentResult:
    values: dict[str, str]
    raw_text: str
    extraction_method: str
    warnings: list[str] = field(default_factory=list)


class OrganizationDocumentService:
    """Extract organization-owner fields from common Vietnamese business PDFs."""

    def __init__(self) -> None:
        self.address_parser = AddressParser()

    def extract_pdf(self, path: str | Path, progress_callback: ProgressCallback | None = None) -> OrganizationDocumentResult:
        document_path = Path(path)
        if document_path.suffix.lower() != ".pdf":
            raise ValueError("Hiện chỉ hỗ trợ đọc tài liệu PDF doanh nghiệp.")
        if not document_path.exists():
            raise FileNotFoundError("Không tìm thấy tài liệu doanh nghiệp đã chọn.")

        self._progress(progress_callback, 5, "Đang mở tài liệu doanh nghiệp")
        with fitz.open(document_path) as document:
            direct_text = "\n".join(page.get_text("text") for page in document)
            result = self._extract_supported_document(direct_text, "text")
            if result is not None:
                self._progress(progress_callback, 100, "Đã đọc thông tin tổ chức")
                return result

            self._progress(progress_callback, 25, "Đang nhận diện chữ trong tài liệu")
            ocr_text = self._extract_with_ocr(document, progress_callback)

        result = self._extract_supported_document(ocr_text, "ocr")
        if result is not None:
            self._progress(progress_callback, 100, "Đã nhận diện thông tin tổ chức")
            return result

        raise ValueError(
            "Không nhận ra mẫu tài liệu doanh nghiệp. Hãy tải lên Giấy chứng nhận đăng ký doanh nghiệp "
            "hoặc hồ sơ có mục Thông tin về chủ sở hữu."
        )

    def _extract_supported_document(self, text: str, method: str) -> OrganizationDocumentResult | None:
        owner_section = self._owner_section(text)
        if self._is_usable_owner_section(owner_section):
            return self._build_owner_section_result(owner_section, text, method)
        if self._is_business_certificate(text):
            return self._build_certificate_result(text, text, method)
        return None

    def _extract_with_ocr(self, document: fitz.Document, progress_callback: ProgressCallback | None) -> str:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:  # pragma: no cover - protected by packaging configuration
            raise RuntimeError("Thiếu bộ OCR nội bộ. Hãy dùng bản ứng dụng đã đóng gói đầy đủ.") from exc

        engine = RapidOCR()
        pages: list[str] = []
        page_count = max(document.page_count, 1)
        for index, page in enumerate(document):
            percent = 25 + int((index / page_count) * 65)
            self._progress(progress_callback, percent, f"Đang nhận diện trang {index + 1}/{page_count}")
            image = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            result, _elapsed = engine(image.tobytes("png"))
            pages.append("\n".join(str(line[1]).strip() for line in result or [] if len(line) > 1))
        return "\n".join(pages)

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
        return ("tentochuc" in compact or "tentchuc" in compact) and "masodoanhnghiep" in compact

    def _is_business_certificate(self, text: str) -> bool:
        compact = self._compact(text)
        return "giaychungnhandangkydoanhnghiep" in compact and "masodoanhnghiep" in compact

    def _build_owner_section_result(
        self,
        section: str,
        raw_text: str,
        method: str,
    ) -> OrganizationDocumentResult:
        lines = self._lines(section)
        address = self._address_value(lines)
        address_values = self._organization_address_values(address)
        values = {
            "organization_owner_name": self._value_for_labels(lines, "tentochuc", "tentchuc").upper(),
            "organization_owner_registration_number": self._value_for_labels(lines, "masodoanhnghiep"),
            "organization_owner_issue_date": self._value_for_labels(lines, "ngaycap"),
            "organization_owner_issue_place": self.normalize_issue_place(self._value_for_labels(lines, "noicap")),
            **address_values,
            "organization_owner_phone": self._contact_value(lines, "dienthoai"),
            "organization_owner_fax": self._contact_value(lines, "sofax", "fax"),
            "organization_owner_email": self._contact_value(lines, "thudientu", "thudientir", "thudientr", "email"),
            "organization_owner_website": self._contact_value(lines, "website"),
        }
        return self._document_result(values, raw_text, method)

    def _build_certificate_result(
        self,
        certificate_text: str,
        raw_text: str,
        method: str,
    ) -> OrganizationDocumentResult:
        lines = self._lines(certificate_text)
        raw_address = self._certificate_address(lines)
        address_values = self._organization_address_values(raw_address)
        values = {
            "organization_owner_name": self._company_name(lines),
            "organization_owner_registration_number": self._value_for_labels(lines, "masodoanhnghiep"),
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
        return self._document_result(values, raw_text, method)

    def _organization_address_values(self, raw_address: str) -> dict[str, str]:
        country = self._country_from_address(raw_address)
        address_without_country = re.sub(
            r"(?i)[,;]?\s*(viet nam|vietnam|trung quoc|china)\s*$",
            "",
            raw_address,
        ).strip(" ,;")
        parsed = self.address_parser.parse(address_without_country) if address_without_country else None
        province = parsed.province if parsed else ""
        if not province:
            province = self._province_from_text(address_without_country)

        ward = parsed.ward if parsed else ""
        if ward:
            ward = self.address_parser.place_matcher.best_ward_name(ward, province) or ward
        if not ward:
            ward = self._known_ward_from_text(address_without_country)
        if not ward:
            ward = self.address_parser.place_matcher.best_ward_name(address_without_country, province)

        detail = parsed.street_line if parsed and parsed.street_line else address_without_country
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
    def _document_result(
        self,
        values: dict[str, str],
        raw_text: str,
        method: str,
    ) -> OrganizationDocumentResult:
        normalized = {
            key: unicodedata.normalize("NFC", self._restore_vietnamese_phrases(value)).strip()
            for key, value in values.items()
        }
        normalized['organization_owner_name'] = normalized.get('organization_owner_name', '').upper()
        warnings: list[str] = []
        if method == 'ocr':
            warnings.append('Vui lòng đối chiếu dấu tiếng Việt trong tên doanh nghiệp và địa chỉ với tài liệu gốc.')
        for key, label in (
            ("organization_owner_name", "Tên tổ chức"),
            ("organization_owner_registration_number", "Mã số doanh nghiệp/Số quyết định"),
            ("organization_owner_address_detail", "Địa chỉ trụ sở chính"),
        ):
            if not normalized[key]:
                warnings.append(f"Chưa nhận diện được: {label}.")
        if (
            normalized.get("organization_owner_country") == "Việt Nam"
            and normalized.get("organization_owner_address_detail")
            and not normalized.get("organization_owner_ward")
        ):
            warnings.append("Chưa xác định được Xã/Phường/Đặc khu theo chính quyền 2 cấp.")
        return OrganizationDocumentResult(
            values=normalized,
            raw_text=self._restore_vietnamese_phrases(raw_text),
            extraction_method=method,
            warnings=warnings,
        )

    def _company_name(self, lines: list[str]) -> str:
        labels = ('tencongtyvietbangtiengviet', 'tendoanhnghiepvietbangtiengviet', 'tenbangtiengviet')
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
            if not (
                "chi" in compact
                and "sochinh" in compact
            ):
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
            if all(marker not in compact for marker in ("diachitru", "diachitry", "djachitru", "djachitry")):
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
            (r"(?i)\bcong\s*ty\s*co\s*phan\b", "CÔNG TY CỔ PHẦN"),
            (r"(?i)\bcong\s*ty\s*tnhh\b", "CÔNG TY TNHH"),
            (r"(?i)\bcong\s*ty\s*trach\s*nhiem\s*hu.?u\s*han\b", "CÔNG TY TRÁCH NHIỆM HỮU HẠN"),
            (r"(?i)\bcung\s*ung\s*lao\s*dong\b", "CUNG ỨNG LAO ĐỘNG"),
            (r"(?i)\bgiai\s*phap\s*phan\s*mem\b", "GIẢI PHÁP PHẦN MỀM"),
            (r"(?i)\bvat\s*lieu\s*moi\b", "VẬT LIỆU MỚI"),
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
            (r"(?i)\bao\s*doi\b", "Ao Đôi"),
            (r"(?i)\bphu\s*chien\b", "Phú Chiến"),
            (r"(?i)\bnha\s*xuong\b", "Nhà xưởng"),
            (r"(?i)\bnha\b", "Nhà"),
            (r"(?i)\bpho\b", "phố"),
            (r"(?i)\bng[0o]\b", "ngõ"),
            (r"(?i)\bcong\s*nghiep\b", "công nghiệp"),
            (r"(?i)\bsan\s*xuat\b", "sản xuất"),
            (r"(?i)\bs[0o]\s*(?=\d)", "Số "),
            (r"(?i)\bngach\b", "ngách"),
            (r"(?i)\bngo\b", "ngõ"),
            (r"(?i)\bduong\b", "đường"),
            (r"(?i)\bap\b", "ấp"),
            (r"(?i)\bphuong\b", "Phường"),
            (r"(?i)\bquan\b", "Quận"),
            (r"(?i)\btrung\s*quoc\b", "Trung Quốc"),
            (r"(?i)\bviet\s*nam\b", "Việt Nam"),
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
