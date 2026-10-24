"""Opening legacy termination drafts must terminate and retain unused fields."""
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest


class LocationTerminationLegacyDraftTests(unittest.TestCase):
    def test_legacy_industry_fields_do_not_hang_or_change_other_dossiers(self):
        root = Path(__file__).resolve().parents[2]
        env = dict(os.environ, PYTHONPATH=str(root / "src"),
                   QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8")
        code = textwrap.dedent("""
            from pathlib import Path
            from tempfile import TemporaryDirectory
            from PySide6.QtCore import QCoreApplication, QEvent
            from PySide6.QtWidgets import QApplication
            from mingo_assistant.models.case import CaseSummary
            from mingo_assistant.repositories.case_repository import CaseRepository
            from mingo_assistant.ui.views.location_business_termination_workspace import (
                LocationBusinessTerminationWorkspace, LOCATION_TERMINATION_CASE_TYPE,
            )
            app = QApplication([])
            with TemporaryDirectory() as temporary:
                folder = Path(temporary)
                repository = CaseRepository(folder / 'cases.json')
                for index, legacy in enumerate(({}, {'business_line_1_name': ''},
                        {'business_line_1_name': 'Legacy industry', 'business_line_1_code': '6201',
                         'business_line_2_name': 'Second industry', 'business_line_2_code': '6202'})):
                    values = dict(legacy, parent_entity_name='COMPANY TEST',
                                  location_business_name='LOCATION TEST', termination_reason='Close location')
                    case = CaseSummary(id='legacy-'+str(index), company_name='LOCATION TEST',
                        case_type=LOCATION_TERMINATION_CASE_TYPE, owner='', updated_at='',
                        status='Draft', condition='', members=0, capital='', form_values=values)
                    repository.save_case(case)
                    other_before = {c.id: c.to_dict() for c in repository.list_cases() if c.id != case.id}
                    workspace = LocationBusinessTerminationWorkspace(
                        on_back=lambda: None, on_save=repository.save_case,
                        case=repository.get_case(case.id), bundle_root=Path.cwd(), default_export_root=folder)
                    workspace.show()
                    app.processEvents()
                    assert workspace._field_value('termination_reason') == 'Close location'
                    saved = workspace.build_case_summary()
                    for key, value in legacy.items():
                        assert saved.form_values[key] == value, key
                    repository.save_case(saved)
                    for other_id, before in other_before.items():
                        assert repository.get_case(other_id).to_dict() == before
                    workspace.hide()
                    workspace.close()
                    workspace.deleteLater()
                    app.processEvents()
                    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            print('legacy drafts opened without losing fields or changing other dossiers')
        """)
        result = subprocess.run([sys.executable, "-c", code], cwd=root, env=env,
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("legacy drafts opened", result.stdout)
