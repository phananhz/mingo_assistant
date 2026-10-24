"""ERC extraction reserved for the general tax-closure commitment."""
from dataclasses import replace
from datetime import datetime
import json
import re
import unicodedata

from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d")) if not unicodedata.combining(c))


def registration_dates(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    found = []
    for index, line in enumerate(lines):
        normalized = fold(line)
        if not re.search(r"dang\s*ky.*(?:lan dau|thay doi)", normalized):
            continue
        segment = line
        for following in lines[index + 1:index + 3]:
            if "dang ky" in fold(following):
                break
            segment += " " + following
        match = re.search(r"ngay\s*(\d{1,2})\s*thang\s*(\d{1,2})\s*nam\s*(\d{4})", fold(segment))
        if not match:
            match = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", segment)
        if not match:
            continue
        try:
            date = datetime.strptime("/".join(match.groups()), "%d/%m/%Y").strftime("%d/%m/%Y")
        except ValueError:
            continue
        label = "Đăng ký lần đầu"
        if "thay doi" in normalized:
            prefix = re.split(r"ngay|\d{1,2}[/.-]\d{1,2}[/.-]", normalized)[0]
            ordinal = re.search(r"lan\s*(?:thu\s*)?[:：]?\s*(\d+)", prefix)
            words = {"1": "một", "2": "hai", "3": "ba", "4": "bốn", "5": "năm", "6": "sáu", "7": "bảy", "8": "tám", "9": "chín", "10": "mười"}
            label = "Đăng ký thay đổi"
            if ordinal:
                label += " lần " + words.get(ordinal[1], ordinal[1])
            else:
                original = re.split(r"[,;]|ngày", line, flags=re.I)[0].strip(" :")
                if original:
                    label = original
        item = {"label": label, "date": date, "source": line}
        if not any(old["label"] == label and old["date"] == date for old in found):
            found.append(item)
    return found


def legal_representatives(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    active = False
    names = []
    for index, line in enumerate(lines):
        normalized = fold(line)
        if "dai dien" in normalized and "phap luat" in normalized:
            active = True
        elif active and re.match(r"^\d+\.\s+(?:chu so huu|von dieu le|thanh vien|danh sach|nganh)", normalized):
            active = False
        if not active or not re.search(r"ho\s*,?\s*(?:va\s+ten|chu dem va ten)\s*(?:\([^)]*\))?\s*:", normalized):
            continue
        name = line.split(":", 1)[-1].strip()
        if not name and index + 1 < len(lines) and ":" not in lines[index + 1]:
            name = lines[index + 1]
        gender = re.search(r"\s+gioi tinh\s*:", fold(name))
        if gender:
            name = name[:gender.start()].strip()
        if name and name not in names:
            names.append(name)
    return names


class TaxCommitmentDocumentService(OrganizationDocumentService):
    def extract_pdf(self, path, progress_callback=None):
        result = super().extract_pdf(path, progress_callback)
        values = dict(result.values)
        dates = json.loads(values.get("tax_registration_dates", "[]"))
        warnings = list(result.warnings)
        if len(dates) > 1:
            values["organization_owner_issue_date"] = ""
            warnings.append("ERC có nhiều ngày đăng ký. Hãy chọn Đăng ký lần đầu hoặc lần đăng ký thay đổi trước khi lưu dữ liệu tổ chức.")
        if not values.get("tax_legal_representatives"):
            warnings.append("Chưa đọc được họ tên người đại diện pháp luật. Hãy đối chiếu ERC và nhập bổ sung.")
        return replace(result, values=values, warnings=list(dict.fromkeys(warnings)))

    def _build_certificate_result(self, certificate_text, raw_text, method, *, source=None):
        result = super()._build_certificate_result(certificate_text, raw_text, method, source=source)
        values = dict(result.values)
        dates = registration_dates(raw_text)
        names = legal_representatives(raw_text)
        values["tax_registration_dates"] = json.dumps(dates, ensure_ascii=False)
        values["tax_legal_representatives"] = "\n".join(names)
        values["organization_owner_address_full"] = ", ".join(values.get(key, "") for key in (
            "organization_owner_address_detail", "organization_owner_ward", "organization_owner_province", "organization_owner_country",
        ) if values.get(key))
        # Multiple dates require an explicit user choice, never a silent latest-date default.
        values["organization_owner_issue_date"] = dates[0]["date"] if len(dates) == 1 else ""
        warnings = list(result.warnings)
        if len(dates) > 1:
            warnings.append("ERC có nhiều ngày đăng ký. Hãy chọn Đăng ký lần đầu hoặc lần đăng ký thay đổi trước khi lưu dữ liệu tổ chức.")
        if not names:
            warnings.append("Chưa đọc được họ tên người đại diện pháp luật. Hãy đối chiếu ERC và nhập bổ sung.")
        return replace(result, values=values, warnings=warnings)

    @classmethod
    def _needs_ocr_fallback(cls, result):
        return super()._needs_ocr_fallback(result) or not result or not result.values.get("tax_legal_representatives")
