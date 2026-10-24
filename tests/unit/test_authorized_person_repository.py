from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mingo_assistant.repositories.authorized_person_repository import AuthorizedPersonProfileRepository


class AuthorizedPersonProfileRepositoryTest(unittest.TestCase):
    def test_personal_release_seed_initializes_editable_profiles_once(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            defaults = root / "defaults.json"
            defaults.write_text('{"profiles": []}', encoding="utf-8")
            seed = root / "authorized_person_seed.json"
            seed.write_text(json.dumps({"selected_profile_id": "seed-2", "profiles": [
                {"id": "seed-1", "authorized_person_full_name": "NGƯỜI KIỂM THỬ MỘT"},
                {"id": "seed-2", "authorized_person_full_name": "NGƯỜI KIỂM THỬ HAI"},
            ]}), encoding="utf-8")
            original_seed = seed.read_bytes()
            repository = AuthorizedPersonProfileRepository(root / "local/profiles.json", defaults, seed)
            loaded = repository.load()
            self.assertEqual(2, len(loaded["profiles"]))
            self.assertEqual("seed-2", loaded["selected_profile_id"])
            self.assertFalse(repository.is_default("seed-2"))
            loaded["profiles"][1]["authorized_person_phone"] = "0900000002"
            repository.save(loaded)
            self.assertEqual("0900000002", repository.load()["profiles"][1]["authorized_person_phone"])
            repository.save({"profiles": [], "selected_profile_id": ""})
            self.assertEqual([], repository.load()["profiles"])
            self.assertEqual(original_seed, seed.read_bytes())

    def test_seed_never_overwrites_existing_local_profiles(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed = root / "authorized_person_seed.json"
            seed.write_text('{"profiles": [{"id": "seed", "authorized_person_full_name": "BUNDLED"}]}', encoding="utf-8")
            data = root / "profiles.json"
            data.write_text('{"profiles": [{"id": "local", "authorized_person_full_name": "LOCAL"}]}', encoding="utf-8")
            original = data.read_bytes()
            repository = AuthorizedPersonProfileRepository(data, root / "defaults.json", seed)
            self.assertEqual("LOCAL", repository.load()["profiles"][0]["authorized_person_full_name"])
            self.assertEqual(original, data.read_bytes())

    def test_legacy_samples_are_hidden_without_rewriting_local_profiles(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            samples = [
                {"id": f"builtin-authorized-person-{i}",
                 "authorized_person_full_name": f"NGƯỜI ỦY QUYỀN MẪU {i}",
                 "authorized_person_id_number": "000000000000"}
                for i in range(1, 4)
            ]
            real = {"id": "saved-real", "authorized_person_full_name": "NGƯỜI DÙNG THẬT",
                    "authorized_person_phone": "0900000001"}
            defaults = root / "defaults.json"
            defaults.write_text(json.dumps({"profiles": samples}), encoding="utf-8")
            data = root / "profiles.json"
            data.write_text(json.dumps({"selected_profile_id": samples[0]["id"], "profiles": samples + [real]}), encoding="utf-8")
            original = data.read_bytes()
            repository = AuthorizedPersonProfileRepository(data, defaults)

            loaded = repository.load()

            self.assertEqual([], repository.default_profiles())
            self.assertEqual([real], loaded["profiles"])
            self.assertEqual("saved-real", loaded["selected_profile_id"])
            self.assertEqual(original, data.read_bytes())
            self.assertEqual([real], repository.merge("saved-real", samples + [real])["profiles"])

    def test_filter_does_not_hide_real_people_reusing_a_builtin_id_or_sample_name(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = AuthorizedPersonProfileRepository(root / "data.json", root / "no-defaults.json")
            real = [
                {"id": "builtin-authorized-person-1", "authorized_person_full_name": "NGƯỜI DÙNG THẬT"},
                {"id": "builtin-authorized-person-2", "authorized_person_full_name": "NGƯỜI ỦY QUYỀN MẪU 2",
                 "authorized_person_id_number": "012345678901"},
            ]
            self.assertEqual(real, repository.merge(real[0]["id"], real)["profiles"])

    def test_samples_only_produce_empty_selection(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = AuthorizedPersonProfileRepository(root / "data.json", root / "no-defaults.json")
            sample = {"id": "builtin-authorized-person-1", "authorized_person_full_name": "NGƯỜI ỦY QUYỀN MẪU 1",
                      "authorized_person_id_number": "000000000000"}
            self.assertEqual({"selected_profile_id": "", "profiles": []}, repository.merge(sample["id"], [sample]))

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
