from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mingo_assistant.repositories.authorized_person_repository import AuthorizedPersonProfileRepository


class AuthorizedPersonProfileRepositoryTest(unittest.TestCase):
    def test_defaults_are_immutable_and_saved_profiles_are_appended(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            defaults_file = root / "defaults.json"
            data_file = root / "authorized_person.json"
            defaults_file.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "profiles": [
                            {
                                "id": "fixed-test",
                                "authorized_person_full_name": "NGUYEN VAN TEST",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            repository = AuthorizedPersonProfileRepository(data_file, defaults_file)

            payload = repository.merge(
                "saved-test",
                [
                    {"id": "fixed-test", "authorized_person_full_name": "CHANGED"},
                    {"id": "saved-test", "authorized_person_full_name": "TRAN THI TEST"},
                ],
            )

            self.assertEqual(payload["selected_profile_id"], "saved-test")
            self.assertEqual(
                [profile["authorized_person_full_name"] for profile in payload["profiles"]],
                ["NGUYEN VAN TEST", "TRAN THI TEST"],
            )

    def test_save_adds_schema_version_and_loads_legacy_single_profile(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            defaults_file = root / "defaults.json"
            data_file = root / "authorized_person.json"
            defaults_file.write_text('{"profiles": []}', encoding="utf-8")
            data_file.write_text(
                json.dumps(
                    {
                        "authorized_person_full_name": "NGUYEN VAN TEST",
                        "authorized_person_id_number": "012345678901",
                    }
                ),
                encoding="utf-8",
            )
            repository = AuthorizedPersonProfileRepository(data_file, defaults_file)

            loaded = repository.load()
            repository.save(loaded)
            stored = json.loads(data_file.read_text(encoding="utf-8"))

            self.assertEqual(len(loaded["profiles"]), 1)
            self.assertEqual(stored["schema_version"], 1)
            self.assertEqual(stored["profiles"][0]["authorized_person_full_name"], "NGUYEN VAN TEST")

    def test_names_are_uppercased_for_defaults_saved_profiles_and_persistence(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            defaults_file = root / "defaults.json"
            data_file = root / "authorized_person.json"
            defaults_file.write_text(
                json.dumps({"profiles": [{"id": "fixed", "authorized_person_full_name": "Mai Xuân Lương"}]}),
                encoding="utf-8",
            )
            repository = AuthorizedPersonProfileRepository(data_file, defaults_file)

            payload = repository.merge(
                "saved",
                [{"id": "saved", "authorized_person_full_name": "Nguyễn Thị Minh Ngọc"}],
            )
            repository.save(payload)
            stored = json.loads(data_file.read_text(encoding="utf-8"))

            self.assertEqual(
                [profile["authorized_person_full_name"] for profile in payload["profiles"]],
                ["MAI XUÂN LƯƠNG", "NGUYỄN THỊ MINH NGỌC"],
            )
            self.assertEqual(
                stored["profiles"][1]["authorized_person_full_name"],
                "NGUYỄN THỊ MINH NGỌC",
            )

    def test_corrupt_local_profiles_keep_fixed_profiles_and_recovery_copy(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            defaults_file = root / "defaults.json"
            data_file = root / "authorized_person.json"
            defaults_file.write_text(
                '{"profiles": [{"id": "fixed-test", "authorized_person_full_name": "TEST"}]}',
                encoding="utf-8",
            )
            data_file.write_text('{"profiles": [', encoding="utf-8")
            repository = AuthorizedPersonProfileRepository(data_file, defaults_file)

            payload = repository.load()

            self.assertEqual(payload["profiles"][0]["id"], "fixed-test")
            self.assertIsNotNone(repository.last_recovery_error)
            self.assertTrue(repository.last_recovery_error.backup_path.exists())
            self.assertEqual(data_file.read_text(encoding="utf-8"), '{"profiles": [')


if __name__ == "__main__":
    unittest.main()
