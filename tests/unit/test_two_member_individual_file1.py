from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from docx import Document

from mingo_assistant.services.documents.business_registration_variants import (
    TWO_MEMBER_INDIVIDUAL_FILE1,
    TWO_MEMBER_INDIVIDUAL_TEMPLATE_RELATIVE_DIR,
)
from mingo_assistant.services.documents.docx_generator import (
    TwoMemberIndividualFile1DocxTemplateGenerator,
)
from mingo_assistant.ui.views.business_registration.schema import FIELD_GROUPS


class TwoMemberIndividualFile1Test(unittest.TestCase):
    def setUp(self) -> None:
        self.project_root = Path(__file__).resolve().parents[2]
        self.template_dir = (
            self.project_root
            / "assets"
            / "templates"
            / "word"
            / "business_registration"
            / TWO_MEMBER_INDIVIDUAL_TEMPLATE_RELATIVE_DIR
        )

    def test_generator_uses_only_file1_and_preserves_source_template(self) -> None:
        source_template = self.template_dir / TWO_MEMBER_INDIVIDUAL_FILE1
        source_hash = hashlib.sha256(source_template.read_bytes()).hexdigest()
        values = {
            "company_name": "CÔNG TY TNHH MẪU HAI THÀNH VIÊN",
            "applicant_full_name": "NGUYỄN VĂN MẪU",
            "applicant_date_of_birth": "01/02/1990",
            "applicant_gender": "Nam",
            "applicant_id_number": "001090000001",
            "legal_representative_full_name": "NGUYỄN VĂN MẪU",
            "legal_representative_date_of_birth": "01/02/1990",
            "legal_representative_gender": "Nam",
            "legal_representative_id_number": "001090000001",
            "legal_representative_position": "Giám đốc",
            "document_place": "Hà Nội",
            "document_day": "14",
            "document_month": "09",
            "document_year": "2026",
            "business_registration_office": "Phòng Đăng ký kinh doanh Hà Nội",
            "legal_representative_nationality": "Việt Nam",
            "company_address_detail": "Số 1 phố Mẫu",
            "company_ward": "Phường Ba Đình",
            "company_province": "Thành phố Hà Nội",
            "charter_capital_number_vnd": "100.000.000 đồng",
            "charter_capital_text": "Một trăm triệu đồng",
            "capital_source_1_amount": "0",
            "capital_source_1_ratio": "0%",
            "capital_source_2_amount": "100.000.000",
            "capital_source_2_ratio": "100%",
            "capital_source_3_amount": "0",
            "capital_source_3_ratio": "0%",
            "capital_source_4_amount": "0",
            "capital_source_4_ratio": "0%",
            "capital_source_total_amount": "100.000.000",
            "capital_source_total_ratio": "100%",
            "director_full_name": "NGUYỄN VĂN MẪU",
            "director_date_of_birth": "01/02/1990",
            "director_id_number": "001090000001",
            "director_phone": "0999999999",
            "tax_labor_count": "2",
            "director_gender": "Nam",
            "company_phone": "0901000001",
            "company_fax": "0241234567",
            "company_email": "contact@example.vn",
            "company_website": "example.vn",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            result = TwoMemberIndividualFile1DocxTemplateGenerator(
                self.template_dir, Path(temp_dir)
            ).generate(values, "ho_so", Path(temp_dir))

            self.assertEqual([TWO_MEMBER_INDIVIDUAL_FILE1], [item.source_name for item in result.generated])
            output_path = result.generated[0].output_path
            self.assertTrue(output_path.is_file())
            generated_text = "\n".join(paragraph.text for paragraph in Document(output_path).paragraphs)
            self.assertIn("CÔNG TY TRÁCH NHIỆM HỮU HẠN HAI THÀNH VIÊN TRỞ LÊN", generated_text)
            self.assertIn("NGUYỄN VĂN MẪU", generated_text)

            generated_document = Document(output_path)
            all_text = "\n".join(
                paragraph.text
                for paragraph in TwoMemberIndividualFile1DocxTemplateGenerator(self.template_dir, Path(temp_dir))._iter_paragraphs(generated_document)
            )
            self.assertIn("Gi\u1edbi t\u00ednh: Nam", all_text)
            self.assertIn("\u0110i\u1ec7n tho\u1ea1i: 0901000001", all_text)
            self.assertIn("S\u1ed1 fax (n\u1ebfu c\u00f3): 0241234567", all_text)
            self.assertIn("Th\u01b0 \u0111i\u1ec7n t\u1eed (n\u1ebfu c\u00f3): contact@example.vn", all_text)
            self.assertGreaterEqual(all_text.count("\u0110i\u1ec7n tho\u1ea1i: 0901000001"), 2)
            self.assertGreaterEqual(all_text.count("S\u1ed1 fax (n\u1ebfu c\u00f3): 0241234567"), 2)
            self.assertGreaterEqual(all_text.count("Th\u01b0 \u0111i\u1ec7n t\u1eed (n\u1ebfu c\u00f3): contact@example.vn"), 2)
        self.assertEqual(source_hash, hashlib.sha256(source_template.read_bytes()).hexdigest())

    def test_applicant_identity_label_is_correct(self) -> None:
        applicant_group = next(fields for title, fields in FIELD_GROUPS if "người đăng ký" in title)
        labels = dict(applicant_group)
        self.assertEqual("Số định danh cá nhân", labels["applicant_id_number"])
