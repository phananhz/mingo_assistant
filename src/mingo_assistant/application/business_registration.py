"""Application-level composition for business-registration workflows."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mingo_assistant.services.business_lines.industry_lookup import IndustryCatalog
from mingo_assistant.services.normalization.address_parser import AddressParser
from mingo_assistant.services.ocr.id_card_parser import IdCardParser
from mingo_assistant.services.ocr.ocr_service import OcrService
from mingo_assistant.services.organization_documents import OrganizationDocumentService
from mingo_assistant.services.personal_profiles import PersonalProfileRepository
from mingo_assistant.services.registration_offices import RegistrationOfficeCatalog


@dataclass
class BusinessRegistrationServices:
    """Concrete dependencies required by the registration workspace."""

    ocr_service: OcrService
    id_card_parser: IdCardParser
    organization_document_service: OrganizationDocumentService
    profile_repository: PersonalProfileRepository
    address_parser: AddressParser
    industry_catalog: IndustryCatalog
    registration_office_catalog: RegistrationOfficeCatalog

    @classmethod
    def from_project(cls, bundle_root: Path) -> "BusinessRegistrationServices":
        return cls(
            ocr_service=OcrService(),
            id_card_parser=IdCardParser(),
            organization_document_service=OrganizationDocumentService(),
            profile_repository=PersonalProfileRepository(),
            address_parser=AddressParser(),
            industry_catalog=IndustryCatalog.load_from_project(bundle_root),
            registration_office_catalog=RegistrationOfficeCatalog.load_from_project(bundle_root),
        )
