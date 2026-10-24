from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mingo_assistant.application.profiles import AuthorizedPersonUseCases
from mingo_assistant.repositories.authorized_person_repository import AuthorizedPersonProfileRepository


class AuthorizedPersonUseCaseTests(unittest.TestCase):
    def test_empty_install_has_no_selected_or_sample_profile(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            use_cases = AuthorizedPersonUseCases(AuthorizedPersonProfileRepository(
                root / "profiles.json",
                Path(__file__).resolve().parents[2] / "assets/defaults/authorized_person_profiles.json",
            ))
            self.assertEqual({"__profiles": []}, use_cases.selected())

    def test_selected_profile_falls_back_to_first_fixed_profile(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            defaults = root / "defaults.json"
            defaults.write_text(
                '{"schema_version": 1, "profiles": [{"id": "fixed-1", '
                '"authorized_person_full_name": "NGUYỄN VĂN TEST"}]}',
                encoding="utf-8",
            )
            use_cases = AuthorizedPersonUseCases(
                AuthorizedPersonProfileRepository(root / "profiles.json", defaults)
            )

            selected = use_cases.selected()

            self.assertEqual(selected["id"], "fixed-1")
            self.assertEqual(len(selected["__profiles"]), 1)
            self.assertTrue(use_cases.is_default("fixed-1"))


if __name__ == "__main__":
    unittest.main()
