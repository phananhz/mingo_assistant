from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from lxml import etree

from mingo_assistant.services.documents.tax_authorization_close_generator import (
    TaxAuthorizationCloseGenerator,
)
from mingo_assistant.services.documents.tax_authorization_restore_generator import (
    TaxAuthorizationRestoreGenerator,
)
from mingo_assistant.ui.views.tax_authorization_restore_workspace import (
    TaxAuthorizationRestoreWorkspace,
)
from tests.unit import test_tax_authorization_close as authorization_tests


class TaxAuthorizationRestoreTests(authorization_tests.TaxAuthorizationCloseTests):
    WORKSPACE_CLASS = TaxAuthorizationRestoreWorkspace
    GENERATOR_CLASS = TaxAuthorizationRestoreGenerator
    TEMPLATE_ID = "tax-authorization-restore"
    TEMPLATE_RELATIVE_DIR = "assets/templates/word/tax/authorization_restore"

    def test_restore_keeps_its_own_authorization_content_and_preserves_close_export(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            close_generator = TaxAuthorizationCloseGenerator(
                authorization_tests.ROOT / "assets/templates/word/tax/authorization_close", root / "close"
            )
            old = close_generator.generate(authorization_tests.VALUES, "Close").generated[0].output_path
            old_bytes = old.read_bytes()
            generator = self.GENERATOR_CLASS(
                authorization_tests.ROOT / self.TEMPLATE_RELATIVE_DIR, root / "restore"
            )
            new = generator.generate(authorization_tests.VALUES, "Restore").generated[0].output_path
            self.assertNotEqual(old, new)
            self.assertEqual(old_bytes, old.read_bytes())
            for path, expected, excluded in (
                (new, "thủ tục khôi phục mã số thuế", "thủ tục giải thể doanh nghiệp"),
                (old, "thủ tục giải thể doanh nghiệp", "thủ tục khôi phục mã số thuế"),
            ):
                with ZipFile(path) as package:
                    xml = etree.fromstring(package.read("word/document.xml"))
                    text = "".join(xml.xpath("//w:t/text()", namespaces=generator.NS))
                    self.assertIn(expected, text)
                    self.assertNotIn(excluded, text)
