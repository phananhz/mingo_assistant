from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mingo_assistant.application.registration import (
    RegistrationExportPlanner,
    RegistrationValueComposer,
    RegistrationViewModel,
)
from mingo_assistant.domains.business_registration import RegistrationValidator, VietnameseMoneyFormatter


class RegistrationApplicationTests(unittest.TestCase):
    class _Address:
        street_line = "12 Đường Mới"
        village = ""
        ward = "Phường Trung Tâm"
        province = "Tỉnh Mẫu"

    class _AddressParser:
        def parse(self, _address: str):
            return RegistrationApplicationTests._Address()

    class _RegistrationOffices:
        def province_for_office(self, office_name: str) -> str:
            return "Tỉnh Mẫu" if office_name else ""

    def test_view_model_copies_state_and_exposes_domain_projection(self) -> None:
        values = {
            "company_name": "CÔNG TY TNHH TEST",
            "charter_capital_number": "1.000.000",
        }
        view_model = RegistrationViewModel(RegistrationValidator())

        view_model.replace(values)
        values["company_name"] = "CHANGED OUTSIDE"

        self.assertEqual(view_model.snapshot()["company_name"], "CÔNG TY TNHH TEST")
        self.assertEqual(view_model.domain_case().charter_capital_vnd, 1_000_000)

    def test_export_planner_preserves_legacy_and_new_version_shape(self) -> None:
        planner = RegistrationExportPlanner()
        versions = planner.append_version(
            [],
            legacy_export_dir="D:/Exports/legacy",
            legacy_exported_at="01/01/2026",
            legacy_documents=["old.docx"],
            case_export_dir="D:/Exports/company",
            version_export_dir="D:/Exports/company/bản 2",
            exported_at="02/01/2026",
            documents=["new.docx"],
            version_name="bản 2",
        )

        self.assertEqual(versions[0]["name"], "bản 1")
        self.assertNotIn("case_export_dir", versions[0])
        self.assertEqual(versions[1]["case_export_dir"], "D:/Exports/company")

    def test_export_planner_reads_existing_sparse_version_directories(self) -> None:
        planner = RegistrationExportPlanner()
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "bản 4").mkdir()
            (root / "not-a-version").mkdir()

            self.assertEqual(planner.next_version_number(root, []), 5)

    def test_money_formatter_preserves_existing_vietnamese_output(self) -> None:
        formatter = VietnameseMoneyFormatter()

        self.assertEqual(formatter.digits("3.000.000.000 đồng"), "3000000000")
        self.assertEqual(formatter.format_digits("3000000000"), "3.000.000.000")
        self.assertEqual(formatter.to_words(1_005), "một nghìn không trăm lẻ năm")

    def test_value_composer_builds_export_defaults_without_mutating_source(self) -> None:
        source = {
            "business_registration_office": "Phòng đăng ký kinh doanh mẫu",
            "document_day": "12",
            "document_month": "9",
            "document_year": "2026",
            "company_address_detail": "1 Đường A",
            "company_ward": "Phường B",
            "legal_representative_full_name": "NGUYỄN VĂN MẪU",
            "legal_representative_phone": "0900000000",
            "charter_capital_number": "1.000.000",
            "business_line_1_name": "Bán buôn  Chi tiết: hàng mẫu",
            "business_line_1_code": "4690",
            "business_line_1_is_main": "X",
            "capital_source_2_amount": "1.000.000",
            "asset_contribution_1_amount": "1.000.000",
        }
        composer = RegistrationValueComposer(self._AddressParser(), self._RegistrationOffices())

        result = composer.compose(source)

        self.assertNotIn("document_place", source)
        self.assertEqual(result["document_place"], "Mẫu")
        self.assertEqual(result["document_place_date"], "Mẫu, ngày 12 tháng 9 năm 2026")
        self.assertEqual(result["company_address"], "1 Đường A, Phường B")
        self.assertEqual(result["director_full_name"], "NGUYỄN VĂN MẪU")
        self.assertEqual(result["member_capital_ratio"], "100%")
        self.assertEqual(result["capital_source_total_ratio"], "100")
        self.assertEqual(result["business_lines"], "Bán buôn\nChi tiết: hàng mẫu [4690] - ngành nghề chính")


if __name__ == "__main__":
    unittest.main()
