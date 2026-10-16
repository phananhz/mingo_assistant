"""Case-specific fields and the reviewed yellow slots of company form 12."""
from __future__ import annotations

from dataclasses import dataclass
import re

from mingo_assistant.domains.business_amendment.models import (
    migrate_business_amendment_form_values,
)


@dataclass(frozen=True)
class YellowSlot:
    paragraph: int
    key: str
    selection: str = ""
    segment: int = 0
    # A second yellow line belongs to the same input, not a second value.
    continuation: bool = False


COMMON_FIELDS = (
    ("business_registration_office", "Cơ quan tiếp nhận hồ sơ"),
    ("document_place", "Nơi ký"),
    ("document_day", "Ngày ký"),
    ("document_month", "Tháng ký"),
    ("document_year", "Năm ký"),
    ("document_place_date", "Dòng địa điểm/ngày tháng"),
)
COMPANY_FIELDS = (
    ("parent_entity_name", "Tên doanh nghiệp hiện tại"),
    ("parent_entity_registration_number", "Mã số doanh nghiệp/Mã số thuế"),
)
REPRESENTATIVE_FIELDS = (
    ("legal_representative_full_name", "Họ tên người đại diện pháp luật/người ký"),
    ("legal_representative_position", "Chức danh"),
    ("legal_representative_date_of_birth", "Ngày sinh"),
    ("legal_representative_gender", "Giới tính"),
    ("legal_representative_nationality", "Quốc tịch"),
    ("legal_representative_id_number", "Số định danh/CMND (nếu có)"),
    ("legal_representative_passport_number", "Số hộ chiếu (nếu có)"),
    ("legal_representative_issue_date", "Ngày cấp giấy tờ (nếu có)"),
    ("legal_representative_issue_place", "Cơ quan cấp giấy tờ (nếu có)"),
    ("legal_representative_permanent_address", "Địa chỉ thường trú (nếu có)"),
    ("legal_representative_contact_address", "Địa chỉ liên lạc"),
)
AMENDMENT_FIELD_GROUPS = (
    ("Thông tin cơ quan tiếp nhận và thời gian ký", COMMON_FIELDS),
    ("Thông tin doanh nghiệp", COMPANY_FIELDS),
    ("Thông tin người đại diện pháp luật", REPRESENTATIVE_FIELDS),
    ("Nội dung thay đổi", ()),
)

NAME_FIELDS = (
    ("new_company_name", "Tên tiếng Việt sau khi thay đổi"),
    ("new_company_english_name", "Tên nước ngoài sau khi thay đổi (nếu có)"),
    ("new_company_short_name", "Tên viết tắt sau khi thay đổi (nếu có)"),
)
ADDRESS_FIELDS = (
    ("new_company_address_detail", "Số nhà/phòng, đường/phố, tổ/ấp/thôn mới"),
    ("new_company_ward", "Xã/Phường/Đặc khu mới"),
    ("new_company_province", "Tỉnh/Thành phố mới"),
    ("new_company_phone", "Điện thoại sau thay đổi"),
    ("new_company_email", "Email sau thay đổi (nếu có)"),
    ("new_company_fax", "Số fax sau thay đổi (nếu có)"),
    ("new_company_website", "Website sau thay đổi (nếu có)"),
)
CAPITAL_SOURCE_LABELS = ("Vốn ngân sách nhà nước", "Vốn tư nhân", "Vốn nước ngoài", "Vốn khác")
ASSET_LABELS = ("Đồng Việt Nam", "Ngoại tệ", "Vàng", "Quyền sử dụng đất", "Quyền sở hữu trí tuệ", "Tài sản khác")
SHARE_LABELS = ("Phổ thông", "Ưu đãi biểu quyết", "Ưu đãi cổ tức", "Ưu đãi hoàn lại", "Ưu đãi khác")
CAPITAL_FIELDS = (
    ("registered_capital", "Vốn điều lệ đã đăng ký (VNĐ)"),
    ("new_capital", "Vốn điều lệ sau thay đổi (VNĐ)"),
    ("capital_foreign_equivalent", "Giá trị tương đương và loại ngoại tệ (nếu có)"),
    ("capital_foreign_yes_checked", "Có"),
    ("capital_foreign_no_checked", "Không"),
    ("capital_change_date", "Thời điểm thay đổi vốn"),
    ("capital_change_method", "Hình thức tăng/giảm vốn"),
    ("amendment_source_2_amount", "Vốn tư nhân — số tiền VNĐ"),
    ("amendment_asset_1_amount", "Đồng Việt Nam — số tiền VNĐ"),
)
SHARE_FIELDS = (("new_share_par_value", "Mệnh giá cổ phần (VNĐ)"),) + tuple(
    (f"amendment_share_{i}_{suffix}", f"Cổ phần {label.lower()} — {unit}")
    for i, label in enumerate(SHARE_LABELS, 1)
    for suffix, unit in (("count", "số lượng"), ("amount", "giá trị VNĐ"), ("ratio", "tỷ lệ %"))
)
# These are template sample rows, never limits on user-entered industries.
LINE_CAPACITIES = {"add": 1, "remove": 1, "detail": 1}


def line_row_count(values: dict[str, str], kind: str) -> int:
    indices = [int(match.group(1)) for key, value in values.items()
               if str(value).strip() and (match := re.fullmatch(rf"amendment_line_{kind}_(\d+)_(?:name|detail|code|main|note)", key))]
    count = values.get(f"amendment_line_{kind}_row_count", "")
    return int(count) if str(count).isdigit() else max([0, *indices])


def migrate_legacy_line_rows(values: dict[str, str]) -> dict[str, str]:
    """Compatibility facade for the domain-owned v4 migration."""

    return migrate_business_amendment_form_values(values)


LINE_LABELS = {"add": "Bổ sung", "remove": "Bỏ ngành nghề", "detail": "Sửa chi tiết"}
LINE_FIELDS = tuple(
    (f"amendment_line_{kind}_{i}_{part}", f"{LINE_LABELS[kind]} — dòng {i}: {label}")
    for kind, capacity in LINE_CAPACITIES.items()
    for i in range(1, capacity + 1)
    for part, label in (("name", "tên ngành/nội dung chi tiết"), ("code", "mã ngành"),
                        ("main" if kind != "remove" else "note", "ngành chính (X)" if kind != "remove" else "ghi chú"))
)
TAX_FIELDS = tuple(
    (f"tax_{role}_{suffix}", f"{label} — {detail}")
    for role, label in (("director", "Giám đốc/Tổng giám đốc"), ("accountant", "Kế toán trưởng/Phụ trách kế toán"))
    for suffix, detail in (("full_name", "họ tên"), ("date_of_birth", "ngày sinh"), ("gender", "giới tính"),
                           ("id_number", "số định danh"), ("phone", "điện thoại"))
) + (
    ("tax_notification_address_detail", "Địa chỉ nhận thông báo thuế — số nhà/đường"),
    ("tax_notification_ward", "Địa chỉ nhận thông báo thuế — xã/phường"),
    ("tax_notification_province", "Địa chỉ nhận thông báo thuế — tỉnh/thành phố"),
    ("tax_notification_phone", "Điện thoại nhận thông báo thuế"),
    ("tax_notification_email", "Email nhận thông báo thuế"),
    ("tax_start_date", "Ngày bắt đầu hoạt động"),
    ("tax_financial_year_start", "Năm tài chính — từ ngày (dd/mm)"),
    ("tax_financial_year_end", "Năm tài chính — đến ngày (dd/mm)"),
    ("tax_labor_count", "Tổng số lao động"),
)
BENEFICIAL_NOTICE_FIELDS = (
    ("beneficial_notice_a_status", "Chủ sở hữu hưởng lợi — nội dung cuối mục a"),
    ("beneficial_notice_b_status", "Chủ sở hữu hưởng lợi — nội dung cuối mục b"),
)
CHANGE_GROUPS = (
    ("change_name_selected", "Đăng ký thay đổi tên doanh nghiệp", NAME_FIELDS),
    ("change_address_selected", "Đăng ký thay đổi địa chỉ trụ sở chính", ADDRESS_FIELDS),
    ("change_capital_selected", "Đăng ký thay đổi vốn điều lệ, phần vốn góp, tỷ lệ phần vốn góp", CAPITAL_FIELDS + SHARE_FIELDS),
    ("change_business_lines_selected", "Đăng ký thay đổi ngành, nghề kinh doanh", LINE_FIELDS),
    ("change_tax_selected", "Đăng ký thay đổi thông tin đăng ký thuế", TAX_FIELDS),
    ("change_beneficial_selected", "Đăng ký chủ sở hữu hưởng lợi", BENEFICIAL_NOTICE_FIELDS),
)
UNSUPPORTED_GROUPS = (
    ("change_members_selected", "Thay đổi thành viên/phần vốn góp: mẫu yêu cầu danh sách gửi kèm."),
    ("change_supplemental_selected", "Bổ sung, cập nhật (B): vùng nhập chưa bôi vàng."),
    ("change_correction_selected", "Hiệu đính (C): vùng nhập chưa bôi vàng."),
)

SLOTS = [
    YellowSlot(1, "parent_entity_name"), YellowSlot(11, "parent_entity_name"),
    YellowSlot(12, "parent_entity_registration_number"),
    YellowSlot(4, "document_place", segment=0), YellowSlot(4, "document_day", segment=1),
    YellowSlot(4, "document_month", segment=2), YellowSlot(4, "document_year", segment=3),
    YellowSlot(10, "business_registration_office"), YellowSlot(271, "legal_representative_full_name"),
    YellowSlot(26, "new_company_name", "change_name_selected"),
    YellowSlot(27, "new_company_name", "change_name_selected", continuation=True),
    YellowSlot(28, "new_company_english_name", "change_name_selected"),
    YellowSlot(29, "new_company_english_name", "change_name_selected", continuation=True),
    YellowSlot(31, "new_company_short_name", "change_name_selected"),
    *[YellowSlot(p, key, "change_address_selected") for p, (key, _) in zip((34, 35, 36, 37, 38), ADDRESS_FIELDS)],
    *[YellowSlot(p, key, "change_capital_selected") for p, key in (
        (55, "registered_capital_text"), (56, "new_capital_text"), (57, "capital_foreign_equivalent"),
        (59, "capital_change_date"), (60, "capital_change_method"))],
    YellowSlot(58, "capital_yes_symbol", "change_capital_selected"),
    *[YellowSlot(p, f"amendment_source_{i}_{suffix}", "change_capital_selected")
      for i, pair in enumerate(((66, 67), (69, 70), (72, 73), (75, 76)), 1)
      for p, suffix in zip(pair, ("amount", "ratio"))],
    YellowSlot(78, "amendment_source_total_amount", "change_capital_selected"),
    YellowSlot(79, "amendment_source_total_ratio", "change_capital_selected"),
    *[YellowSlot(p, f"amendment_asset_{i}_{suffix}", "change_capital_selected")
      for i, pair in enumerate(((87, 88), (91, 92), (95, 96), (99, 100), (103, 104), (107, 108)), 1)
      for p, suffix in zip(pair, ("amount", "ratio"))],
    YellowSlot(110, "amendment_asset_total_amount", "change_capital_selected"),
    YellowSlot(111, "amendment_asset_total_ratio", "change_capital_selected"),
    YellowSlot(113, "new_share_par_value", "change_capital_selected"),
    *[YellowSlot(121 + (i - 1) * 5 + offset, f"amendment_share_{i}_{suffix}", "change_capital_selected")
      for i in range(1, 6) for offset, suffix in enumerate(("count", "amount", "ratio"))],
    *[YellowSlot(145 + offset, f"amendment_share_total_{suffix}", "change_capital_selected")
      for offset, suffix in enumerate(("count", "amount", "ratio"))],
    *[YellowSlot(start + (i - 1) * 4 + offset, f"amendment_line_{kind}_{i}_{suffix}", "change_business_lines_selected")
      for kind, start in (("add", 158), ("remove", 167), ("detail", 176))
      for i in range(1, LINE_CAPACITIES[kind] + 1)
      for offset, suffix in enumerate(("number", "name", "code", "main" if kind != "remove" else "note"))],
    *[YellowSlot(p, key, "change_tax_selected") for p, (key, _) in zip(
        (191, 192, 193, 194, 195, 198, 199, 200, 201, 202, 205, 206, 207, 208, 209, 211), TAX_FIELDS[:16])],
    YellowSlot(225, "tax_financial_year_start", "change_tax_selected", segment=0),
    YellowSlot(225, "tax_financial_year_end", "change_tax_selected", segment=1),
    YellowSlot(228, "tax_labor_count", "change_tax_selected"),
    YellowSlot(247, "beneficial_notice_a_text", "change_beneficial_selected"),
    YellowSlot(248, "beneficial_notice_b_text", "change_beneficial_selected"),
]

ORGANIZATION_MAPPING = {
    "parent_entity_name": "organization_owner_name",
    "parent_entity_registration_number": "organization_owner_registration_number",
    "company_english_name": "organization_english_name", "company_short_name": "organization_short_name",
    "company_first_registration_date": "organization_first_registration_date",
    "company_latest_registration_date": "organization_owner_issue_date",
    "company_issue_place": "organization_owner_issue_place",
    "company_original_address": "organization_original_address",
    "company_address_detail": "organization_owner_address_detail", "company_ward": "organization_owner_ward",
    "company_province": "organization_owner_province", "company_country": "organization_owner_country",
    "company_phone": "organization_owner_phone", "company_fax": "organization_owner_fax",
    "company_email": "organization_owner_email", "company_website": "organization_owner_website",
    "registered_capital": "organization_capital",
    "company_share_par_value": "organization_share_par_value", "company_share_count": "organization_share_count",
}
