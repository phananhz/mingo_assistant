"""Static field schema for the business-registration workflow."""
from __future__ import annotations

PERSON_ROLES = [
    ("beneficial_owner", "Chủ sở hữu"),
    ("legal_representative", "Đại diện pháp luật/Giám đốc"),
    ("member", "Thành viên/chủ sở hữu góp vốn"),
    ("applicant", "Người đăng ký/nộp hồ sơ"),
    ("authorized_person", "Người được ủy quyền"),
]


FIELD_GROUPS = [
    ("Thông tin cơ quan tiếp nhận và thời gian ký", [("business_registration_office", "Phòng đăng ký kinh doanh"), ("document_place", "Nơi ký"), ("document_day", "Ngày ký"), ("document_month", "Tháng ký"), ("document_year", "Năm ký"), ("document_place_date", "Dòng địa điểm/ngày tháng")]),
    ("Thông tin người đăng ký/nộp hồ sơ", [("applicant_full_name", "Họ tên người đăng ký"), ("applicant_date_of_birth", "Ngày sinh"), ("applicant_gender", "Giới tính"), ("applicant_id_number", "Số CCCD"), ("applicant_address_detail", "Số nhà/đường/thôn"), ("applicant_ward", "Xã/Phường"), ("applicant_province", "Tỉnh/Thành phố"), ("applicant_phone", "Điện thoại"), ("applicant_email", "Thư điện tử (nếu có)")]),
    ("Thông tin doanh nghiệp", [("company_name", "Tên doanh nghiệp"), ("company_english_name", "Tên tiếng Anh (nếu có)"), ("company_short_name", "Tên viết tắt (nếu có)"), ("company_address", "Địa chỉ trụ sở đầy đủ"), ("company_address_detail", "Số nhà/đường/thôn"), ("company_ward", "Xã/Phường"), ("company_province", "Tỉnh/Thành phố"), ("company_phone", "Số điện thoại công ty"), ("company_email", "Email công ty (nếu có)"), ("company_fax", "Số fax (nếu có)"), ("company_website", "Website (nếu có)"), ("company_land_use_certificate", "Có giấy chứng nhận quyền sử dụng đất thuộc khu vực quốc phòng, an ninh")]),
    ("Ngành nghề kinh doanh", []),
    ("Thông tin chủ sở hữu", [
        ("beneficial_owner_full_name", "Họ tên chủ sở hữu"),
        ("beneficial_owner_date_of_birth", "Ngày sinh"),
        ("beneficial_owner_gender", "Giới tính"),
        ("beneficial_owner_ethnicity", "Dân tộc"),
        ("beneficial_owner_id_number", "Số CCCD"),
        ("beneficial_owner_issue_date", "Ngày cấp CCCD"),
        ("beneficial_owner_address", "Địa chỉ liên lạc"),
        ("organization_owner_name", "Tên tổ chức (ghi bằng chữ in hoa)"),
        ("organization_owner_registration_number", "Mã số doanh nghiệp/Số quyết định thành lập"),
        ("organization_owner_issue_date", "Ngày cấp"),
        ("organization_owner_issue_place", "Nơi cấp"),
        ("organization_owner_address_detail", "Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn"),
        ("organization_owner_ward", "Xã/Phường/Đặc khu"),
        ("organization_owner_province", "Tỉnh/Thành phố trực thuộc trung ương"),
        ("organization_owner_country", "Quốc gia"),
        ("organization_owner_phone", "Điện thoại (nếu có)"),
        ("organization_owner_fax", "Số fax (nếu có)"),
        ("organization_owner_email", "Thư điện tử (nếu có)"),
        ("organization_owner_website", "Website (nếu có)"),
    ]),
    ("Vốn điều lệ và vốn góp", [("charter_capital_number", "Vốn điều lệ bằng số"), ("charter_capital_text", "Vốn điều lệ bằng chữ"), ("charter_capital_full_text", "Vốn điều lệ đầy đủ"), ("cash_capital_text", "Vốn bằng tiền mặt"), ("asset_capital_text", "Vốn bằng tài sản"), ("member_capital_amount", "Vốn góp thành viên"), ("member_capital_ratio", "Tỷ lệ góp vốn"), ("capital_zero", "Giá trị 0 trong bảng vốn")]),
    ("Thông tin người đại diện pháp luật", [("legal_representative_full_name", "Họ tên"), ("legal_representative_id_number", "Số CCCD"), ("legal_representative_date_of_birth", "Ngày sinh"), ("legal_representative_gender", "Giới tính"), ("legal_representative_nationality", "Quốc tịch"), ("legal_representative_ethnicity", "Dân tộc"), ("legal_representative_permanent_address", "Địa chỉ thường trú đầy đủ"), ("legal_representative_address_detail", "Số nhà/đường/thôn"), ("legal_representative_ward", "Xã/Phường"), ("legal_representative_province", "Tỉnh/Thành phố"), ("legal_representative_contact_address", "Địa chỉ liên lạc"), ("legal_representative_issue_date", "Ngày cấp"), ("legal_representative_expiry_date", "Ngày hết hạn"), ("legal_representative_position", "Chức danh"), ("legal_representative_phone", "Điện thoại"), ("legal_representative_email", "Thư điện tử (nếu có)"), ("legal_representative_issue_place", "Nơi cấp CCCD")]),
    ("Thông tin giám đốc/Tổng giám đốc", [("director_full_name", "Họ tên giám đốc"), ("director_date_of_birth", "Ngày sinh"), ("director_gender", "Giới tính"), ("director_id_number", "Số CCCD"), ("director_phone", "Điện thoại"), ("director_position", "Chức danh")]),
    ("Thông tin đăng ký thuế và bảo hiểm xã hội", [("tax_accounting_method", "Hình thức hạch toán"), ("tax_consolidated_financial_statement", "Có báo cáo tài chính hợp nhất"), ("tax_fiscal_year_start", "Năm tài chính bắt đầu (ngày/tháng)"), ("tax_fiscal_year_end", "Năm tài chính kết thúc (ngày/tháng)"), ("tax_labor_count", "Tổng số lao động dự kiến"), ("tax_bot_project", "Hoạt động theo dự án BOT/BTO/BT/BOO, BLT, BTL, O&M"), ("tax_vat_method", "Phương pháp tính thuế GTGT"), ("tax_declaration_period", "Phương thức đóng bảo hiểm xã hội")]),
    ("Danh s\u00e1ch ch\u1ee7 s\u1edf h\u1eefu h\u01b0\u1edfng l\u1ee3i", [("beneficial_owner_list_capital_direct", "9. V\u1ed1n \u0111i\u1ec1u l\u1ec7 tr\u1ef1c ti\u1ebfp"), ("beneficial_owner_list_capital_indirect", "10. V\u1ed1n \u0111i\u1ec1u l\u1ec7 gi\u00e1n ti\u1ebfp"), ("beneficial_owner_list_capital_total", "11. T\u1ed5ng v\u1ed1n \u0111i\u1ec1u l\u1ec7"), ("beneficial_owner_list_voting_direct", "12. Bi\u1ec3u quy\u1ebft tr\u1ef1c ti\u1ebfp"), ("beneficial_owner_list_voting_indirect", "13. Bi\u1ec3u quy\u1ebft gi\u00e1n ti\u1ebfp"), ("beneficial_owner_list_voting_total", "14. T\u1ed5ng bi\u1ec3u quy\u1ebft"), ("beneficial_owner_list_general_partner", "15. Th\u00e0nh vi\u00ean h\u1ee3p danh"), ("beneficial_owner_list_related_group", "16. Nh\u00f3m c\u00e1 nh\u00e2n li\u00ean quan"), ("beneficial_owner_list_control", "17. Ki\u1ec3m so\u00e1t doanh nghi\u1ec7p"), ("beneficial_owner_list_manager", "18. Ng\u01b0\u1eddi qu\u1ea3n l\u00fd doanh nghi\u1ec7p")]),
    ("Thông tin người được ủy quyền", [("authorized_person_full_name", "Họ tên"), ("authorized_person_date_of_birth", "Ngày sinh"), ("authorized_person_gender", "Giới tính"), ("authorized_person_id_number", "Số CCCD"), ("authorized_person_issue_date", "Ngày cấp CCCD"), ("authorized_person_issue_place", "Nơi cấp CCCD"), ("authorized_person_contact_address", "Địa chỉ liên lạc"), ("authorized_person_phone", "Điện thoại"), ("authorized_person_email", "Email (nếu có)")]),
]

BUSINESS_LINE_FIELD_DEFINITIONS = [
    (f"business_line_{index}_name", f"Ngành {index}") for index in range(1, 11)
] + [
    (f"business_line_{index}_code", f"Mã ngành {index}") for index in range(1, 11)
] + [
    (f"business_line_{index}_is_main", f"Ngành chính {index}") for index in range(1, 11)
] + [
    (f"business_line_{index}_detail", f"Mô tả chi tiết ngành {index}") for index in range(1, 11)
]

HIDDEN_FIELD_DEFINITIONS = [
    ("business_lines", "Ghi chú ngành nghề"),
    ("signature_initial_note", "Ghi chú ký"),
]

FIELD_DEFINITIONS = [field for _, fields in FIELD_GROUPS for field in fields] + BUSINESS_LINE_FIELD_DEFINITIONS + HIDDEN_FIELD_DEFINITIONS


MULTILINE_FIELDS = {
    "company_address",
    "business_lines",
    "legal_representative_permanent_address",
    "legal_representative_contact_address",
    "beneficial_owner_address",
    "authorized_person_contact_address",
}

INDIVIDUAL_OWNER_FIELD_KEYS = (
    "beneficial_owner_full_name",
    "beneficial_owner_date_of_birth",
    "beneficial_owner_gender",
    "beneficial_owner_id_number",
    "beneficial_owner_issue_date",
    "beneficial_owner_address",
)

ORGANIZATION_OWNER_FIELD_KEYS = (
    "organization_owner_name",
    "organization_owner_registration_number",
    "organization_owner_issue_date",
    "organization_owner_issue_place",
    "organization_owner_address_detail",
    "organization_owner_ward",
    "organization_owner_province",
    "organization_owner_country",
    "organization_owner_phone",
    "organization_owner_fax",
    "organization_owner_email",
    "organization_owner_website",
)

ORGANIZATION_OWNER_REPRESENTATIVE_FIELD_KEYS = (
    "organization_owner_representative_number",
    "organization_owner_representative_full_name",
    "organization_owner_representative_date_of_birth",
    "organization_owner_representative_gender",
    "organization_owner_representative_identity",
    "organization_owner_representative_nationality",
    "organization_owner_representative_ethnicity",
    "organization_owner_representative_contact_address",
    "organization_owner_representative_authorized_capital_value",
    "organization_owner_representative_authorized_capital_ratio",
    "organization_owner_representative_authorized_capital_date",
    "organization_owner_representative_signature",
    "organization_owner_representative_notes",
)


CAPITAL_SOURCE_LABELS = (
    "Vốn ngân sách nhà nước",
    "Vốn tư nhân",
    "Vốn nước ngoài",
    "Vốn khác",
)
ASSET_CONTRIBUTION_LABELS = (
    "Đồng Việt Nam",
    "Ngoại tệ tự do chuyển đổi",
    "Vàng",
    "Quyền sử dụng đất",
    "Quyền sở hữu trí tuệ",
    "Các tài sản khác",
)
POSITION_OPTIONS = ("Giám đốc", "Tổng giám đốc")
