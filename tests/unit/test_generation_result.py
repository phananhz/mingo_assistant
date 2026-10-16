from pathlib import Path
import unittest

from mingo_assistant.services.documents.docx_generator import (
    GeneratedDocument as LegacyGeneratedDocument,
)
from mingo_assistant.services.documents.docx_generator import (
    GenerationResult as LegacyGenerationResult,
)
from mingo_assistant.services.documents.generation_result import GeneratedDocument, GenerationResult
from mingo_assistant.services.documents.docx_template_engine import DocxTemplateEngine
from mingo_assistant.services.documents.dependent_unit_generator import DependentUnitTemplateGenerator
from mingo_assistant.services.documents.two_member_individual_generator import (
    TwoMemberIndividualFile1DocxTemplateGenerator,
)


class GenerationResultTest(unittest.TestCase):
    def test_dependent_unit_generator_uses_shared_engine_without_registration_inheritance(self) -> None:
        from mingo_assistant.services.documents.business_registration_generator import DocxTemplateGenerator

        self.assertTrue(issubclass(DependentUnitTemplateGenerator, DocxTemplateEngine))
        self.assertNotIn(DocxTemplateGenerator, DependentUnitTemplateGenerator.__mro__)

    def test_legacy_docx_generator_exports_remain_compatible(self) -> None:
        self.assertIs(GeneratedDocument, LegacyGeneratedDocument)
        self.assertIs(GenerationResult, LegacyGenerationResult)

        from mingo_assistant.services.documents.business_registration_generator import (
            TwoMemberIndividualFile1DocxTemplateGenerator as LegacyTwoMemberGenerator,
        )
        from mingo_assistant.services.documents.docx_generator import (
            TwoMemberIndividualFile1DocxTemplateGenerator as FacadeTwoMemberGenerator,
        )

        self.assertIs(TwoMemberIndividualFile1DocxTemplateGenerator, LegacyTwoMemberGenerator)
        self.assertIs(TwoMemberIndividualFile1DocxTemplateGenerator, FacadeTwoMemberGenerator)

    def test_result_types_are_immutable_value_objects(self) -> None:
        document = GeneratedDocument("source.docx", Path("output.docx"))
        result = GenerationResult(Path("exports"), [document], [], {})

        self.assertEqual("source.docx", result.generated[0].source_name)
        with self.assertRaises(AttributeError):
            document.source_name = "changed.docx"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
