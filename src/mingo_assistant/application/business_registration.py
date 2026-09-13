"""Application-level composition for business-registration workflows."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mingo_assistant.domains.business_registration import RegistrationValidator
from mingo_assistant.application.registration import RegistrationExportPlanner, RegistrationValueComposer
from mingo_assistant.application.people import PersonProfileSynchronizer, PersonRoleMapper
from mingo_assistant.services.business_lines.industry_lookup import IndustryCatalog
from mingo_assistant.services.normalization.address_parser import AddressParser
from mingo_assistant.services.ocr.id_card_parser import IdCardParser
from mingo_assistant.services.qr import IdentityQrScanner
from mingo_assistant.services.organization_documents import OrganizationDocumentService
from mingo_assistant.services.personal_profiles import PersonalProfileRepository
from mingo_assistant.services.registration_offices import RegistrationOfficeCatalog


@dataclass
class BusinessRegistrationServices:
    """Concrete dependencies required by the registration workspace."""

    ocr_service: IdentityQrScanner
    id_card_parser: IdCardParser
    organization_document_service: OrganizationDocumentService
    profile_repository: PersonalProfileRepository
    address_parser: AddressParser
    industry_catalog: IndustryCatalog
    registration_office_catalog: RegistrationOfficeCatalog
    registration_validator: RegistrationValidator
    export_planner: RegistrationExportPlanner
    value_composer: RegistrationValueComposer
    person_role_mapper: PersonRoleMapper
    person_profile_synchronizer: PersonProfileSynchronizer

    @classmethod
    def from_project(cls, bundle_root: Path) -> "BusinessRegistrationServices":
        address_parser = AddressParser()
        registration_offices = RegistrationOfficeCatalog.load_from_project(bundle_root)
        return cls(
            ocr_service=IdentityQrScanner(bundle_root),
            id_card_parser=IdCardParser(),
            organization_document_service=OrganizationDocumentService(),
            profile_repository=PersonalProfileRepository(),
            address_parser=address_parser,
            industry_catalog=IndustryCatalog.load_from_project(bundle_root),
            registration_office_catalog=registration_offices,
            registration_validator=RegistrationValidator(),
            export_planner=RegistrationExportPlanner(),
            value_composer=RegistrationValueComposer(address_parser, registration_offices),
            person_role_mapper=PersonRoleMapper(address_parser),
            person_profile_synchronizer=PersonProfileSynchronizer(),
        )
