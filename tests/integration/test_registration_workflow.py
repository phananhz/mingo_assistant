from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

from mingo_assistant.application.cases import CaseUseCases
from mingo_assistant.application.registration import RegistrationViewModel
from mingo_assistant.domains.business_registration import RegistrationValidator
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.documents.docx_generator import DocxTemplateGenerator
from mingo_assistant.services.normalization.administrative_place_matcher import AdministrativePlaceMatcher
from mingo_assistant.services.ocr.id_card_parser import IdCardParser


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RegistrationWorkflowIntegrationTests(unittest.TestCase):
    def test_create_save_load_validate_and_export_real_docx_templates(self) -> None:
        values = {
            "owner_type": "Cá nhân",
            "beneficial_owner_full_name": "NGUYỄN VĂN TEST",
            "beneficial_owner_id_number": "012345678901",
            "beneficial_owner_address": "1 Đường Test, Phường Test, Thành phố Hồ Chí Minh",
            "company_name": "CÔNG TY TNHH TÍCH HỢP TEST",
            "company_address": "1 Đường Test, Phường Test, Thành phố Hồ Chí Minh",
            "company_phone": "0900000000",
            "charter_capital_number": "1.000.000.000",
            "legal_representative_full_name": "NGUYỄN VĂN TEST",
            "legal_representative_id_number": "012345678901",
            "legal_representative_permanent_address": "1 Đường Test, Phường Test, Thành phố Hồ Chí Minh",
            "legal_representative_issue_place": "Bộ Công an",
            "business_line_1_name": "Dịch vụ thử nghiệm",
            "business_line_1_code": "8299",
            "business_line_1_is_main": "X",
        }
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            use_cases = CaseUseCases(CaseRepository(root / "cases.json"))
            case = CaseSummary(
                id="integration-case",
                company_name=values["company_name"],
                case_type="TNHH một thành viên",
                owner=values["legal_representative_full_name"],
                updated_at="01/01/2026",
                status="Bản nháp",
                condition="Đủ dữ liệu",
                members=1,
                capital=values["charter_capital_number"],
                form_values=values,
            )

            use_cases.save(case)
            loaded = use_cases.get("integration-case")
            view_model = RegistrationViewModel(RegistrationValidator())
            view_model.replace(loaded.form_values)
            validation = view_model.validate()

            self.assertTrue(validation.is_valid, validation.errors)
            generator = DocxTemplateGenerator(
                PROJECT_ROOT / "assets" / "templates" / "word" / "business_registration",
                root / "exports",
            )
            result = generator.generate(
                view_model.snapshot(),
                loaded.company_name,
                root / "exports" / "integration-case" / "bản 1",
            )

            self.assertEqual(len(result.generated), 5)
            self.assertFalse(result.skipped)
            for generated in result.generated:
                self.assertTrue(generated.output_path.is_file())
                self.assertTrue(zipfile.is_zipfile(generated.output_path))

    def test_fake_qr_parse_and_administrative_normalization_pipeline(self) -> None:
        matcher = AdministrativePlaceMatcher(
            PROJECT_ROOT / "assets" / "administrative_places" / "vietnam_admin_2025.json"
        )
        parser = IdCardParser(matcher)

        card = parser.parse_qr(
            "012345678901|000000000|NGUYEN VAN TEST|01011990|Nam|"
            "1 Duong Test, Phuong Ben Nghe, Quan 1, TP Ho Chi Minh|01012025"
        )

        self.assertEqual(card.id_number, "012345678901")
        self.assertEqual(card.full_name, "NGUYEN VAN TEST")
        self.assertTrue(card.raw_permanent_address)
        self.assertTrue(card.permanent_address)


if __name__ == "__main__":
    unittest.main()
