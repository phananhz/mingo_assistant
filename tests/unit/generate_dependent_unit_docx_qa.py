"""Generate a representative dependent-unit dossier for manual render QA."""

from __future__ import annotations

from pathlib import Path

from mingo_assistant.services.documents.dependent_unit_generator import DependentUnitTemplateGenerator


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "tmp_dependent_engine_qa_20261015"
    values = {
        "business_registration_office": "Phòng Đăng ký kinh doanh Hà Nội",
        "parent_entity_name": "CÔNG TY TNHH MINGO",
        "parent_entity_registration_number": "0101234567",
        "parent_entity_name_prefix": "CÔNG TY TNHH",
        "parent_entity_name_suffix": "MINGO",
        "location_business_name": "ĐỊA ĐIỂM KINH DOANH MINGO",
        "location_address_detail": "Số 1 Phố Mẫu",
        "location_ward": "Phường Mẫu",
        "location_province": "Thành phố Hà Nội",
        "location_manager_full_name": "NGUYỄN VĂN A",
        "location_manager_date_of_birth": "01/01/1990",
        "location_manager_gender": "Nam",
        "location_manager_id_number": "001090000001",
        "location_manager_address_detail": "Số 2 Phố Mẫu",
        "location_manager_ward": "Phường Mẫu",
        "location_manager_province": "Thành phố Hà Nội",
        "location_manager_nationality": "Việt Nam",
        "legal_representative_full_name": "NGUYỄN VĂN B",
        "legal_representative_id_number": "001080000002",
        "legal_representative_position": "Giám đốc",
        "company_name": "CÔNG TY TNHH MINGO",
        "company_address": "Số 3 Phố Mẫu, Phường Mẫu, Hà Nội",
        "authorized_person_full_name": "TRẦN THỊ C",
        "authorized_person_id_number": "001095000003",
        "authorized_person_contact_address": "Số 4 Phố Mẫu, Hà Nội",
        "authorized_person_phone": "0900000000",
        "authorized_person_email": "qa@example.test",
        "legal_representative_issue_date": "01/01/2020",
        "legal_representative_issue_place": "Hà Nội",
        "document_place": "Hà Nội",
        "document_day": "15",
        "document_month": "10",
        "document_year": "2026",
        "business_line_1_number": "1",
        "business_line_1_name": "Lập trình máy vi tính",
        "business_line_1_detail": "Lập trình máy vi tính",
        "business_line_1_code": "6201",
        "business_line_1_is_main": "X",
        "business_line_2_number": "2",
        "business_line_2_name": "Tư vấn máy vi tính và quản trị hệ thống máy vi tính",
        "business_line_2_code": "6202",
        "tax_accounting_dependent_x": "X",
        "tax_labor_count": "3",
    }
    result = DependentUnitTemplateGenerator(
        project_root / "assets" / "templates" / "word" / "dependent_units" / "ddkd_create",
        output_dir,
    ).generate(values, "Địa điểm kinh doanh Mingo", output_dir)
    print(f"Generated {len(result.generated)} documents in {result.output_dir}")
    print(f"Unresolved placeholders: {result.unresolved}")
    for document in result.generated:
        print(document.output_path)


if __name__ == "__main__":
    main()
