from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mingo_assistant.app.container import AppContainer
from mingo_assistant.app.paths import AppPaths


class AppContainerTest(unittest.TestCase):
    def test_build_uses_explicit_runtime_paths_and_shared_services(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        with TemporaryDirectory() as temporary:
            runtime_root = Path(temporary)
            paths = AppPaths(
                bundle_root=project_root,
                user_data_root=runtime_root / "data",
                documents_root=runtime_root / "documents",
            )

            container = AppContainer.build(paths)

            services = container.registration_services
            self.assertEqual(container.case_repository.data_file, paths.cases_file)
            self.assertEqual(services.profile_repository.data_file, paths.personal_profiles_file)
            self.assertIs(services.address_parser.place_matcher, services.id_card_parser.place_matcher)
            self.assertIs(services.organization_document_service.address_parser, services.address_parser)
            self.assertEqual(len(container.authorized_person_repository.default_profiles()), 3)


if __name__ == "__main__":
    unittest.main()
