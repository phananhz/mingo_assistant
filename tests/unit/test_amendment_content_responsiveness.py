"""Exercise B/C layout with a running event loop, bounded by a process timeout."""
from pathlib import Path
import os
import subprocess
import sys
import textwrap
import unittest


class AmendmentContentResponsivenessTests(unittest.TestCase):
    def test_visible_bc_forms_remain_responsive_after_wrapping_and_resizing(self):
        root = Path(__file__).resolve().parents[2]
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8")
        env["PYTHONPATH"] = os.pathsep.join((str(root / "src"), str(root / "tests/unit")))
        code = textwrap.dedent("""
            import os
            from PySide6.QtCore import QTimer
            from test_business_amendment import BusinessAmendmentWorkflowTests

            case = BusinessAmendmentWorkflowTests()
            case.setUpClass()
            case.setUp()
            window = case.window
            window.resize(1300, 850)
            window.show()
            window._open_business_amendment_modal()
            workspace = window.current_workspace
            workspace._select_form_section(3)
            calls = [0]
            sync = workspace._sync_form_stack_height
            def counted_sync():
                calls[0] += 1
                sync()
            workspace._sync_form_stack_height = counted_sync
            step = [0]
            content_keys = ('amendment_supplemental_content',
                            'amendment_certificate_content', 'amendment_filed_content')
            def tick():
                step[0] += 1
                if step[0] == 5:
                    assert calls[0] < 100, calls[0]
                    for key in content_keys:
                        field = workspace.fields[key]
                        assert field.height() > 140
                        assert field.toPlainText().endswith('last line')
                    window._close_requested = True
                    case.tearDown()
                    print('B/C event loop remained responsive', flush=True)
                    os._exit(0)
                for key in ('change_supplemental_selected', 'change_correction_selected'):
                    workspace.fields[key].setChecked(True)
                for key in content_keys:
                    workspace._set_field(key, ('wrapped content ' * 20 + '\\n') * step[0] * 6 + 'last line')
                window.resize(1050 + step[0] * 70, 800)
                QTimer.singleShot(250, tick)
            QTimer.singleShot(200, tick)
            case.app.exec()
        """)
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=root, env=env,
            capture_output=True, text=True, encoding="utf-8", timeout=25,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("B/C event loop remained responsive", result.stdout)
