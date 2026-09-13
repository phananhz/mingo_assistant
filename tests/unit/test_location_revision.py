import unittest
import tempfile
from pathlib import Path
from docx import Document
from mingo_assistant.services.organization_documents.organization_document_service import OrganizationDocumentService
from mingo_assistant.services.documents.dependent_unit_generator import DependentUnitTemplateGenerator


class LocationRevisionTest(unittest.TestCase):
    def test_person_modes_keep_draft_values_and_validate_passport(self):
        from PySide6.QtWidgets import QApplication
        from mingo_assistant.ui.views.location_business_workspace import LocationBusinessWorkspace
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as temporary:
            workspace = LocationBusinessWorkspace(on_back=lambda: None, on_save=lambda case: None,
                bundle_root=Path(__file__).resolve().parents[2], default_export_root=Path(temporary))
            try:
                workspace._set_field('legal_representative_person_type', 'Người nước ngoài')
                self.assertTrue(workspace.fields['legal_representative_id_number'].isEnabled())
                self.assertTrue(workspace.fields['legal_representative_passport_number'].isEnabled())
                workspace._set_field('legal_representative_id_number', 'FOREIGN-ID-001')
                workspace._set_field('legal_representative_passport_number', 'P123456')
                workspace._set_field('legal_representative_passport_issue_date', '12/02/2018')
                workspace._set_field('legal_representative_passport_issue_place', 'Cục quản lý xuất nhập cảnh Trung Quốc')
                workspace._set_field('legal_representative_person_type', 'Người Việt Nam')
                workspace._set_field('legal_representative_person_type', 'Người nước ngoài')
                self.assertEqual('FOREIGN-ID-001', workspace.form_values(False)['legal_representative_id_number'])
                self.assertEqual('P123456', workspace.form_values(False)['legal_representative_passport_number'])
                self.assertEqual('12/02/2018', workspace.form_values(False)['legal_representative_passport_issue_date'])
                self.assertEqual('Cục quản lý xuất nhập cảnh Trung Quốc', workspace.form_values(False)['legal_representative_passport_issue_place'])
                self.assertNotIn('Số hộ chiếu người đại diện pháp luật', workspace._missing_required_fields(workspace.form_values()))
                workspace._set_field('location_manager_id_number', '012345678901')
                workspace._set_field('location_manager_person_type', 'Người nước ngoài')
                self.assertEqual('', workspace.form_values()['location_manager_id_number'])
                workspace._set_field('location_manager_person_type', 'Người Việt Nam')
                self.assertEqual('012345678901', workspace.form_values()['location_manager_id_number'])
            finally:
                workspace.deleteLater()

    def test_inline_certificate_address(self):
        service = OrganizationDocumentService()
        self.assertEqual('Số 270/114 Phan Đình Phùng Phường Cầu Kiệu', service._certificate_address([
            '2. Địa chỉ trụ sở chính: Số 270/114 Phan Đình Phùng',
            'Phường Cầu Kiệu', 'Điện thoại: 0123456789']))

    def test_certificate_ignores_registration_number_in_owner_section_four(self):
        service = OrganizationDocumentService()
        certificate = "\n".join((
            "GIAY CHUNG NHAN DANG KY DOANH NGHIEP",
            "Ma so doanh nghiep: 3703192163",
            "1. Ten cong ty",
            "Ten cong ty viet bang tieng Viet: CONG TY TNHH VAT LIEU MOI LUYI VIET NAM",
            "2. Dia chi tru so chinh: 1 TEST STREET, VIET NAM",
            "3. Von dieu le: 14929895453 dong",
            "4. Thong tin ve chu so huu",
            "Ten to chuc: CONG TY KHAC",
            "Ma so doanh nghiep: 3306552",
        ))

        result = service._extract_supported_document(certificate, "ocr")

        self.assertIsNotNone(result)
        self.assertEqual("3703192163", result.values["organization_owner_registration_number"])
    def test_output_names_and_foreign_signer(self):
        templates = Path(__file__).resolve().parents[2] / 'assets/templates/word/dependent_units/ddkd_create'
        with tempfile.TemporaryDirectory() as temporary:
            generator = DependentUnitTemplateGenerator(templates, Path(temporary))
            result = generator.generate({
                'parent_entity_name': 'CÔNG TY TNHH AN NHIÊN SPA VIỆT NAM',
                'legal_representative_full_name': 'NGUYỄN VĂN TEST',
                'legal_representative_person_type': 'Người nước ngoài',
                'legal_representative_id_number': 'MUST-NOT-EXPORT',
                'legal_representative_passport_number': 'P123456',
                'legal_representative_passport_issue_date': '12/02/2018',
                'legal_representative_passport_issue_place': 'Cục quản lý xuất nhập cảnh Trung Quốc',
                'authorized_person_full_name': 'TRẦN THỊ TEST',
                'authorized_person_id_number': '012345678901',
                'authorized_person_issue_date': '01/01/2025',
                'authorized_person_issue_place': 'Bộ Công an',
                'authorized_person_phone': '0900000000',
                'authorized_person_email': 'test@example.invalid',
            }, 'Test')
            self.assertEqual({
                'Thong bao lap dia diem_AnNhienSpaVietNam.docx',
                'Giay uy quyen_AnNhienSpaVietNam.docx',
                'Huong dan ky_AnNhienSpaVietNam.docx',
            }, {item.output_path.name for item in result.generated})
            for item in result.generated:
                document = Document(item.output_path)
                paragraphs = list(generator._iter_paragraphs(document))
                text = '\n'.join(p.text for p in paragraphs)
                if item.output_path.name.startswith('Giay'):
                    self.assertEqual(
                        DependentUnitTemplateGenerator.FOREIGN_AUTHORIZATION_TEMPLATE,
                        item.source_name,
                    )
                    self.assertIn('Hộ chiếu số: P123456', text)
                    for expected in (
                        '12/02/2018',
                        'Cục quản lý xuất nhập cảnh Trung Quốc',
                        'TRẦN THỊ TEST',
                        '012345678901',
                        '01/01/2025',
                        'Bộ Công an',
                        '0900000000',
                        'test@example.invalid',
                    ):
                        self.assertIn(expected, text)
                    self.assertNotIn('MUST-NOT-EXPORT', text)
                if item.output_path.name.startswith('Huong'):
                    self.assertEqual(2, text.count('Nguyễn Văn Test'))
                if item.output_path.name.startswith('Thong'):
                    matched = [p for p in paragraphs if '6. Thông tin đăng ký thuế' in p.text or 'cá nhân dưới đây' in p.text]
                    self.assertEqual(2, len(matched))
                    self.assertTrue(all(r.font.size.pt == 13 for p in matched for r in p.runs))
