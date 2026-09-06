import unittest

from docx import Document
from docx.shared import Pt

from mingo_assistant.services.documents.docx_generator import DocxTemplateGenerator
from mingo_assistant.services.normalization.address_parser import AddressParser
from mingo_assistant.ui.main_window import BUILT_IN_AUTHORIZED_PERSON_PROFILES, MainWindow
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
        saved_profile = {
            "id": "builtin-nguyen-thi-minh-ngoc",
            "authorized_person_full_name": "Tên bị sửa",
            "authorized_person_issue_place": "Nơi cấp bị sửa",
            "authorized_person_contact_address": "Địa chỉ bị chuẩn hóa",
        }

        payload = MainWindow._merge_authorized_person_profiles(
            window, "builtin-nguyen-thi-minh-ngoc", [saved_profile]
        )
        profile = next(
            item for item in payload["profiles"] if item["id"] == "builtin-nguyen-thi-minh-ngoc"
        )

        self.assertEqual(profile["authorized_person_full_name"], "Nguyễn Thị Minh Ngọc")
        self.assertEqual(profile["authorized_person_issue_place"], "Bộ Công an")
        self.assertEqual(
            profile["authorized_person_contact_address"],
            next(item for item in BUILT_IN_AUTHORIZED_PERSON_PROFILES if item["id"] == "builtin-duong-hong-ngoc")["authorized_person_contact_address"],
        )

    def test_builtin_authorized_profiles_keep_fixed_legacy_addresses(self) -> None:
        profiles = {profile["id"]: profile for profile in BUILT_IN_AUTHORIZED_PERSON_PROFILES}

        self.assertEqual(
            profiles["builtin-duong-hong-ngoc"]["authorized_person_contact_address"],
            "Số 43-45 Đường số 7, Khu Phố 1, Phường Hiệp Bình, Thành phố Hồ Chí Minh",
        )
        self.assertEqual(
            profiles["builtin-mai-xuan-luong"]["authorized_person_contact_address"],
            profiles["builtin-duong-hong-ngoc"]["authorized_person_contact_address"],
        )
        self.assertEqual(
            profiles["builtin-nguyen-thi-minh-ngoc"]["authorized_person_contact_address"],
            profiles["builtin-duong-hong-ngoc"]["authorized_person_contact_address"],
        )


    def test_cccd_sync_matches_only_the_same_identity_number(self) -> None:
        identities = {"030085001651"}

        self.assertTrue(BusinessRegistrationWorkspace._same_person_identity("030085001651", identities))
        self.assertTrue(BusinessRegistrationWorkspace._same_person_identity("CCCD 030085001651", identities))
        self.assertFalse(BusinessRegistrationWorkspace._same_person_identity("031199001726", identities))

    def test_saved_cccd_profile_is_preferred_over_stale_case_person_data(self) -> None:
        workspace = BusinessRegistrationWorkspace.__new__(BusinessRegistrationWorkspace)
        workspace.personal_profiles = [
            {
                "legal_representative_full_name": "PH\u1ea0M TH\u00c0NH LONG",
                "legal_representative_id_number": "030085001651",
                "legal_representative_permanent_address": "\u0110\u1ecba ch\u1ec9 m\u1edbi",
                "legal_representative_contact_address": "Li\u00ean l\u1ea1c m\u1edbi",
            }
        ]
        person = type("Person", (), {"data": {
            "legal_representative_full_name": "PH\u1ea0M TH\u00c0NH LONG",
            "legal_representative_id_number": "030085001651",
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
if __name__ == "__main__":
    unittest.main()
