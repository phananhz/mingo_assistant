"""Backward-compatible imports for the former DOCX generator module.

New code should import business-registration generators from
``business_registration_generator`` and result types from
``generation_result``. This facade remains while callers migrate.
"""

from mingo_assistant.services.documents.business_registration_generator import (
    DocxTemplateGenerator,
)
from mingo_assistant.services.documents.generation_result import GeneratedDocument, GenerationResult
from mingo_assistant.services.documents.two_member_individual_generator import (
    TwoMemberIndividualFile1DocxTemplateGenerator,
)

__all__ = [
    "DocxTemplateGenerator",
    "GeneratedDocument",
    "GenerationResult",
    "TwoMemberIndividualFile1DocxTemplateGenerator",
]
