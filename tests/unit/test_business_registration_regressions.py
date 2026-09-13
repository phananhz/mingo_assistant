import unittest
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from mingo_assistant.services.documents.docx_generator import DocxTemplateGenerator
from mingo_assistant.services.normalization.address_parser import AddressParser
from mingo_assistant.repositories.authorized_person_repository import AuthorizedPersonProfileRepository
from mingo_assistant.ui.main_window import MainWindow
from mingo_assistant.ui.views.business_registration_workspace import BusinessRegistrationWorkspace


class BusinessRegistrationRegressionTest(unittest.TestCase):
    def test_labeled_manual_company_address_is_split_even_when_confirmation_is_needed(self) -> None:
        result = AddressParser().parse("Số 1, Phường 2, Thành phố Đà Nẵng")

        self.assertEqual(result.normalization_status, "needs_confirmation")
        self.assertEqual(result.street_line, "Số 1")
        self.assertEqual(result.ward, "Phường 2")
        self.assertEqual(result.province, "Thành phố Đà Nẵng")

    def test_power_of_attorney_replaces_authorized_person_address(self) -> None:
        document = Document()
        document.add_paragraph("BÊN NHẬN ỦY QUYỀN (Bên B)")
        address_paragraph = document.add_paragraph("Địa chỉ: địa chỉ mẫu")
        document.add_paragraph("ĐIỀU 1. NỘI DUNG ỦY QUYỀN")

        generator = DocxTemplateGenerator.__new__(DocxTemplateGenerator)
        generator._apply_power_of_attorney_authorized_address(
            document,
            "4. Giấy ủy quyền.docx",
            {"authorized_person_contact_address": "Số 2, Phường 3, Thành phố Đà Nẵng"},
        )

        self.assertEqual(address_paragraph.text, "Địa chỉ: Số 2, Phường 3, Thành phố Đà Nẵng")

    def test_beneficial_owner_address_uses_required_font_style(self) -> None:
        document = Document()
        cell = document.add_table(rows=1, cols=1).cell(0, 0)
        cell.text = "Số 1, Phường 2, Thành phố Đà Nẵng"

        DocxTemplateGenerator._format_beneficial_owner_address_cell(cell, cell.text)

        run = cell.paragraphs[0].runs[0]
        self.assertFalse(run.italic)
        self.assertEqual(run.font.size, Pt(11.5))
        self.assertEqual(run.font.name, "Times New Roman")

    def test_beneficial_owner_place_date_uses_required_font_style(self) -> None:
        document = Document()
        paragraph = document.add_paragraph("Hà Nội, ngày 06 tháng 09 năm 2026")

        generator = DocxTemplateGenerator.__new__(DocxTemplateGenerator)
        generator._format_beneficial_owner_place_date(
            document,
            "3. danh sách chủ sở hữu hưởng lợi.docx",
            {
                "document_place": "Hà Nội",
                "document_day": "06",
                "document_month": "09",
                "document_year": "2026",
            },
        )

        run = paragraph.runs[0]
        self.assertTrue(run.italic)
        self.assertEqual(run.font.size, Pt(11.5))
        self.assertEqual(run.font.name, "Times New Roman")

    def test_builtin_authorized_profiles_are_not_overwritten_by_saved_data(self) -> None:
        window = MainWindow.__new__(MainWindow)
        project_root = Path(__file__).resolve().parents[2]
        window.authorized_person_repository = AuthorizedPersonProfileRepository(
            project_root / "data" / "temp" / "not-used.json",
            project_root / "assets" / "defaults" / "authorized_person_profiles.json",
        )
        expected = window.authorized_person_repository.default_profiles()[2]
        saved_profile = {
            "id": expected["id"],
            "authorized_person_full_name": "Tên bị sửa",
            "authorized_person_issue_place": "Nơi cấp bị sửa",
            "authorized_person_contact_address": "Địa chỉ bị chuẩn hóa",
        }

        payload = MainWindow._merge_authorized_person_profiles(
            window, expected["id"], [saved_profile]
        )
        profile = next(
            item for item in payload["profiles"] if item["id"] == expected["id"]
        )

        self.assertEqual(profile, expected)

    def test_builtin_authorized_profiles_keep_fixed_legacy_addresses(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        repository = AuthorizedPersonProfileRepository(
            project_root / "data" / "temp" / "not-used.json",
            project_root / "assets" / "defaults" / "authorized_person_profiles.json",
        )
        profiles = repository.default_profiles()

        self.assertEqual(len(profiles), 3)
        self.assertTrue(all(profile.get("authorized_person_contact_address") for profile in profiles))
        self.assertTrue(all(repository.is_default(profile["id"]) for profile in profiles))


    def test_cccd_sync_matches_only_the_same_identity_number(self) -> None:
        identities = {"012345678901"}

        self.assertTrue(BusinessRegistrationWorkspace._same_person_identity("012345678901", identities))
        self.assertTrue(BusinessRegistrationWorkspace._same_person_identity("CCCD 012345678901", identities))
        self.assertFalse(BusinessRegistrationWorkspace._same_person_identity("012345678902", identities))

    def test_saved_cccd_profile_is_preferred_over_stale_case_person_data(self) -> None:
        workspace = BusinessRegistrationWorkspace.__new__(BusinessRegistrationWorkspace)
        workspace.personal_profiles = [
            {
                "legal_representative_full_name": "NGUYEN VAN TEST",
                "legal_representative_id_number": "012345678901",
                "legal_representative_permanent_address": "\u0110\u1ecba ch\u1ec9 m\u1edbi",
                "legal_representative_contact_address": "Li\u00ean l\u1ea1c m\u1edbi",
            }
        ]
        person = type("Person", (), {"data": {
            "legal_representative_full_name": "NGUYEN VAN TEST",
            "legal_representative_id_number": "012345678901",
            "legal_representative_permanent_address": "\u0110\u1ecba ch\u1ec9 c\u0169",
        }})()

        data = workspace._person_data_for_fill(person)

        self.assertEqual(data["legal_representative_permanent_address"], "\u0110\u1ecba ch\u1ec9 m\u1edbi")
        self.assertEqual(data["legal_representative_contact_address"], "Li\u00ean l\u1ea1c m\u1edbi")

    def test_empty_company_email_replaces_template_sample_email(self) -> None:
        document = Document()
        paragraph = document.add_paragraph(
            "Th\u01b0 \u0111i\u1ec7n t\u1eed (n\u1ebfu c\u00f3): 4@gmail.com\tWebsite (n\u1ebfu c\u00f3): example.com"
        )
        generator = DocxTemplateGenerator.__new__(DocxTemplateGenerator)

        generator._apply_company_contact_fields(
            document,
            "1. Gi\u1ea5y \u0111\u1ec1 ngh\u1ecb.docx",
            {"company_email": "", "company_website": ""},
        )

        self.assertNotIn("4@gmail.com", paragraph.text)
        self.assertIn("..................", paragraph.text)
    def test_company_email_is_not_replaced_inside_its_new_value(self) -> None:
        document = Document()
        paragraph = document.add_paragraph(
            "Th\u01b0 \u0111i\u1ec7n t\u1eed (n\u1ebfu c\u00f3): 4@gmail.com\tWebsite (n\u1ebfu c\u00f3): example.com"
        )
        generator = DocxTemplateGenerator.__new__(DocxTemplateGenerator)

        generator._apply_company_contact_fields(
            document,
            "1. Gi\u1ea5y \u0111\u1ec1 ngh\u1ecb.docx",
            {"company_email": "234@gmail.com", "company_website": ""},
        )

        self.assertIn("234@gmail.com", paragraph.text)
        self.assertNotIn("23234@gmail.com", paragraph.text)

    def test_case_load_clears_authorized_contact_copied_to_different_applicant(self) -> None:
        values = {
            "applicant_full_name": "TRAN THI TEST",
            "applicant_id_number": "012345678902",
            "applicant_phone": "0900000000",
            "applicant_email": "test@example.invalid",
            "authorized_person_full_name": "NGUYEN VAN TEST",
            "authorized_person_id_number": "012345678901",
            "authorized_person_phone": "0900000000",
            "authorized_person_email": "test@example.invalid",
        }

        BusinessRegistrationWorkspace._clear_cross_person_authorized_contacts(values)

        self.assertEqual(values["applicant_phone"], "")
        self.assertEqual(values["applicant_email"], "")

    def test_case_load_keeps_contacts_when_applicant_is_authorized_person(self) -> None:
        values = {
            "applicant_id_number": "012345678901",
            "applicant_phone": "0900000000",
            "applicant_email": "test@example.invalid",
            "authorized_person_id_number": "012345678901",
            "authorized_person_phone": "0900000000",
            "authorized_person_email": "test@example.invalid",
        }

        BusinessRegistrationWorkspace._clear_cross_person_authorized_contacts(values)

        self.assertEqual(values["applicant_phone"], "0900000000")
        self.assertEqual(values["applicant_email"], "test@example.invalid")

    def test_document_generation_keeps_business_lines_beyond_ten(self) -> None:
        generator = DocxTemplateGenerator.__new__(DocxTemplateGenerator)
        values = {
            "business_line_1_name": "Ngành đầu tiên",
            "business_line_1_code": "1000",
            "business_line_11_name": "Ngành thứ mười một",
            "business_line_11_code": "8569",
        }

        lines = generator._business_lines(values)

        self.assertEqual([line["code"] for line in lines], ["1000", "8569"])
        self.assertEqual(lines[-1]["name"], "Ngành thứ mười một")

    def test_file1_business_line_stt_is_centered_and_does_not_wrap_after_nine(self) -> None:
        document = Document()
        table = document.add_table(rows=2, cols=4)
        table.rows[0].cells[0].text = "STT"
        table.rows[0].cells[1].text = "Ten nganh"
        table.rows[0].cells[2].text = "Ma nganh"
        table.rows[0].cells[3].text = "Nganh chinh"
        table.rows[1].cells[0].paragraphs[0].paragraph_format.left_indent = Pt(24)
        generator = DocxTemplateGenerator.__new__(DocxTemplateGenerator)
        values = {
            f"business_line_{index}_name": f"Nganh {index}"
            for index in range(1, 11)
        }
        values.update(
            {
                f"business_line_{index}_code": f"{index:04d}"
                for index in range(1, 11)
            }
        )

        generator._replace_business_lines_tables_v2(
            document,
            values,
            keep_file1_business_line_numbers_on_one_line=True,
        )

        stt_cell = table.rows[10].cells[0]
        paragraph = stt_cell.paragraphs[0]
        self.assertEqual(stt_cell.text, "10")
        self.assertEqual(len(paragraph.runs), 1)
        self.assertEqual(paragraph.alignment, WD_ALIGN_PARAGRAPH.CENTER)
        self.assertIsNone(paragraph.paragraph_format.left_indent)
        self.assertIn("w:noWrap", stt_cell._tc.xml)

    def test_legacy_province_address_is_converted_from_administrative_data(self) -> None:
        result = AddressParser().parse(
            "Th\u00f4n B\u1ed3n Th\u00f4n, Trung An, V\u0169 Th\u01b0, Th\u00e1i B\u00ecnh"
        )

        self.assertEqual(result.normalization_status, "converted")
        self.assertEqual(result.village, "Th\u00f4n B\u1ed3n Th\u00f4n")
        self.assertEqual(result.ward, "Ph\u01b0\u1eddng V\u0169 Ph\u00fac")
        self.assertEqual(result.province, "H\u01b0ng Y\u00ean")

    def test_power_of_attorney_place_date_uses_13_point_font(self) -> None:
        document = Document()
        paragraph = document.add_paragraph(
            "Th\u00e0nh ph\u1ed1 H\u1ed3 Ch\u00ed Minh, ng\u00e0y 06 th\u00e1ng 10 n\u0103m 2026"
        )
        generator = DocxTemplateGenerator.__new__(DocxTemplateGenerator)

        generator._ensure_power_of_attorney_place_date_font(
            document,
            "4. Gi\u1ea5y \u1ee7y quy\u1ec1n.docx",
            {
                "document_place": "Th\u00e0nh ph\u1ed1 H\u1ed3 Ch\u00ed Minh",
                "document_day": "06",
                "document_month": "10",
                "document_year": "2026",
            },
        )

        self.assertEqual(paragraph.runs[0].font.size, Pt(13))
    def test_beneficial_owner_template_never_exports_nationality(self) -> None:
        document = Document()
        table = document.add_table(rows=2, cols=18)
        table.rows[0].cells[0].text = "1"
        table.rows[0].cells[17].text = "18"
        generator = DocxTemplateGenerator.__new__(DocxTemplateGenerator)

        generator._apply_beneficial_owner_template_rules(
            document,
            "3. Danh s\u00e1ch ch\u1ee7 s\u1edf h\u1eefu h\u01b0\u1edfng l\u1ee3i.docx",
            {
                "beneficial_owner_list_number": "1",
                "beneficial_owner_list_full_name": "NGUYEN VAN A",
                "beneficial_owner_list_nationality": "Vi\u1ec7t Nam",
            },
        )

        self.assertEqual(table.rows[1].cells[5].text, "")
if __name__ == "__main__":
    unittest.main()
