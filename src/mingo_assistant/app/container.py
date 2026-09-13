from __future__ import annotations

from dataclasses import dataclass

from mingo_assistant.app.paths import AppPaths
from mingo_assistant.application.business_registration import BusinessRegistrationServices
from mingo_assistant.application.cases import CaseUseCases
from mingo_assistant.application.registration import RegistrationExportPlanner, RegistrationValueComposer
from mingo_assistant.application.profiles import AuthorizedPersonUseCases
from mingo_assistant.application.people import PersonProfileSynchronizer, PersonRoleMapper
from mingo_assistant.domains.business_registration import RegistrationValidator
from mingo_assistant.repositories.authorized_person_repository import AuthorizedPersonProfileRepository
from mingo_assistant.repositories.case_repository import CaseRepository
from mingo_assistant.services.business_lines.industry_lookup import IndustryCatalog
from mingo_assistant.services.normalization.address_parser import AddressParser
from mingo_assistant.services.normalization.administrative_place_matcher import AdministrativePlaceMatcher
from mingo_assistant.services.ocr.id_card_parser import IdCardParser
from mingo_assistant.services.qr import IdentityQrScanner
from mingo_assistant.services.organization_documents import OrganizationDocumentService
from mingo_assistant.services.personal_profiles import PersonalProfileRepository
from mingo_assistant.services.registration_offices import RegistrationOfficeCatalog


@dataclass(frozen=True)
class AppContainer:
    """Composition root for process-wide application dependencies."""

    paths: AppPaths
    case_repository: CaseRepository
    case_use_cases: CaseUseCases
    authorized_person_repository: AuthorizedPersonProfileRepository
    authorized_person_use_cases: AuthorizedPersonUseCases
    registration_services: BusinessRegistrationServices
    industry_catalog: IndustryCatalog

    @classmethod
    def build(cls, paths: AppPaths) -> "AppContainer":
        place_matcher = AdministrativePlaceMatcher(
            paths.bundle_root / "assets" / "administrative_places" / "vietnam_admin_2025.json"
        )
        address_parser = AddressParser(place_matcher)
        industry_catalog = IndustryCatalog.load_from_project(paths.bundle_root)
        registration_offices = RegistrationOfficeCatalog.load_from_project(paths.bundle_root)
        registration_services = BusinessRegistrationServices(
            ocr_service=IdentityQrScanner(paths.bundle_root),
            id_card_parser=IdCardParser(place_matcher),
            organization_document_service=OrganizationDocumentService(address_parser),
            profile_repository=PersonalProfileRepository(paths.personal_profiles_file),
            address_parser=address_parser,
            industry_catalog=industry_catalog,
            registration_office_catalog=registration_offices,
            registration_validator=RegistrationValidator(),
            export_planner=RegistrationExportPlanner(),
            value_composer=RegistrationValueComposer(address_parser, registration_offices),
            person_role_mapper=PersonRoleMapper(address_parser),
            person_profile_synchronizer=PersonProfileSynchronizer(),
        )
        case_repository = CaseRepository(paths.cases_file)
        authorized_person_repository = AuthorizedPersonProfileRepository(
            paths.authorized_person_file,
            paths.authorized_person_defaults_file,
        )
        return cls(
            paths=paths,
            case_repository=case_repository,
            case_use_cases=CaseUseCases(case_repository),
            authorized_person_repository=authorized_person_repository,
            authorized_person_use_cases=AuthorizedPersonUseCases(authorized_person_repository),
            registration_services=registration_services,
            industry_catalog=industry_catalog,
        )
