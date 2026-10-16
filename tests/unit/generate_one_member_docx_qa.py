"""Generate a representative one-member registration dossier for render QA."""

from __future__ import annotations

from pathlib import Path

from mingo_assistant.services.documents.business_registration_generator import DocxTemplateGenerator


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "tmp_one_member_engine_qa_20261015"
    values = {
        "owner_type": "Cá nhân",
        "company_name": "CÔNG TY TNHH TÍCH HỢP TEST",
        "company_english_name": "TEST INTEGRATION COMPANY LIMITED",
        "company_short_name": "TEST INTEGRATION",
        "company_address": "Số 1 Đường Test, Phường Bến Nghé, Thành phố Hồ Chí Minh",
        "company_address_detail": "Số 1 Đường Test",
        "company_ward": "Phường Bến Nghé",
        "company_province": "Thành phố Hồ Chí Minh",
        "company_phone": "0900000000",
        "company_email": "company@example.test",
        "charter_capital_number": "1.000.000.000",
        "charter_capital_words": "Một tỷ đồng",
        "capital_total_ratio": "100",
        "legal_representative_full_name": "NGUYỄN VĂN TEST",
        "legal_representative_position": "Giám đốc",
        "legal_representative_gender": "Nam",
        "legal_representative_date_of_birth": "01/01/1990",
        "legal_representative_id_number": "012345678901",
        "legal_representative_issue_date": "01/01/2025",
        "legal_representative_issue_place": "Bộ Công an",
        "legal_representative_permanent_address": (
            "Số 1 Đường Test, Phường Bến Nghé, Thành phố Hồ Chí Minh"
        ),
        "legal_representative_address_detail": "Số 1 Đường Test",
        "legal_representative_ward": "Phường Bến Nghé",
        "legal_representative_province": "Thành phố Hồ Chí Minh",
        "legal_representative_nationality": "Việt Nam",
        "beneficial_owner_full_name": "NGUYỄN VĂN TEST",
        "beneficial_owner_id_number": "012345678901",
        "beneficial_owner_address": "Số 1 Đường Test, Phường Bến Nghé, Thành phố Hồ Chí Minh",
        "applicant_full_name": "NGUYỄN VĂN TEST",
        "applicant_id_number": "012345678901",
        "applicant_address_detail": "Số 1 Đường Test",
        "applicant_ward": "Phường Bến Nghé",
        "applicant_province": "Thành phố Hồ Chí Minh",
        "authorized_person_full_name": "TRẦN THỊ TEST",
        "authorized_person_id_number": "001095000003",
        "authorized_person_contact_address": "Số 2 Đường Test, Thành phố Hồ Chí Minh",
        "authorized_person_phone": "0911111111",
        "authorized_person_email": "authorized@example.test",
        "business_registration_office": "Phòng Đăng ký kinh doanh Thành phố Hồ Chí Minh",
        "document_place": "Thành phố Hồ Chí Minh",
        "document_day": "15",
        "document_month": "10",
        "document_year": "2026",
        "business_line_1_name": "Lập trình máy vi tính",
        "business_line_1_detail": "Lập trình máy vi tính",
        "business_line_1_code": "6201",
        "business_line_1_is_main": "X",
        "business_line_2_name": "Tư vấn máy vi tính và quản trị hệ thống máy vi tính",
        "business_line_2_code": "6202",
    }
    result = DocxTemplateGenerator(
        project_root / "assets" / "templates" / "word" / "business_registration",
        output_dir,
    ).generate(values, values["company_name"], output_dir)
    print(f"Generated {len(result.generated)} documents in {result.output_dir}")
    print(f"Unresolved placeholders: {result.unresolved}")
    for document in result.generated:
        print(document.output_path)


if __name__ == "__main__":
    main()
