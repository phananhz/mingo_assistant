import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from mingo_assistant.application.profile_bundle import prepare_profile_bundle, SEED_FILENAME


def real_profile(index=1):
    return {"id": f"test-profile-{index}", "authorized_person_full_name": f"Người kiểm thử {index}",
            "authorized_person_id_number": f"01234567890{index}", "authorized_person_issue_date": "01/01/2025",
            "authorized_person_issue_place": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
            "authorized_person_contact_address": "Địa chỉ kiểm thử", "authorized_person_phone": "0900000001",
            "authorized_person_email": "qa@example.invalid", "authorized_person_gender": "Nữ"}


class AuthorizedProfileBundleTests(TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "local-profiles.json"
        self.defaults = self.root / "defaults.json"
        self.defaults.write_text('{"profiles": []}', encoding="utf-8")
        self.output = self.root / "private" / SEED_FILENAME

    def tearDown(self):
        self.temporary.cleanup()

    def write_profiles(self, profiles):
        self.source.write_text(json.dumps({"profiles": profiles, "selected_profile_id": "test-profile-2"}), encoding="utf-8")

    def test_complete_profiles_are_packaged_without_changing_source_or_public_defaults(self):
        self.write_profiles([real_profile(i) for i in (1, 2, 3)])
        original_source, original_defaults = self.source.read_bytes(), self.defaults.read_bytes()
        summary = prepare_profile_bundle(self.source, self.defaults, self.output)
        bundled = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(3, summary["profiles"])
        self.assertEqual(hashlib.sha256(self.output.read_bytes()).hexdigest(), summary["sha256"])
        self.assertEqual("test-profile-2", bundled["selected_profile_id"])
        self.assertEqual("NGƯỜI KIỂM THỬ 1", bundled["profiles"][0]["authorized_person_full_name"])
        self.assertEqual("qa@example.invalid", bundled["profiles"][0]["authorized_person_email"])
        self.assertEqual(original_source, self.source.read_bytes())
        self.assertEqual(original_defaults, self.defaults.read_bytes())

    def test_samples_are_excluded_and_sample_only_builds_fail(self):
        sample = {"id": "builtin-authorized-person-1", "authorized_person_full_name": "NGƯỜI ỦY QUYỀN MẪU 1",
                  "authorized_person_id_number": "000000000000"}
        self.write_profiles([sample])
        with self.assertRaises(ValueError):
            prepare_profile_bundle(self.source, self.defaults, self.output)
        self.assertFalse(self.output.exists())
        self.write_profiles([sample, real_profile()])
        self.assertEqual(1, prepare_profile_bundle(self.source, self.defaults, self.output)["profiles"])

    def test_incomplete_or_duplicate_profiles_abort_before_writing_bundle(self):
        incomplete = real_profile()
        incomplete["authorized_person_issue_place"] = ""
        for profiles in ([incomplete], [real_profile(), real_profile()]):
            self.write_profiles(profiles)
            with self.assertRaises(ValueError):
                prepare_profile_bundle(self.source, self.defaults, self.output)
            self.assertFalse(self.output.exists())

    def test_legacy_single_profile_can_be_bundled(self):
        profile = real_profile()
        profile.pop("id")
        self.source.write_text(json.dumps(profile), encoding="utf-8")
        self.assertEqual(1, prepare_profile_bundle(self.source, self.defaults, self.output)["profiles"])

    def test_seed_cannot_overwrite_its_source(self):
        self.source = self.root / SEED_FILENAME
        self.write_profiles([real_profile()])
        before = self.source.read_bytes()
        with self.assertRaises(ValueError):
            prepare_profile_bundle(self.source, self.defaults, self.source)
        self.assertEqual(before, self.source.read_bytes())

    def test_packaged_resource_autofills_on_a_clean_machine(self):
        from mingo_assistant.app.portable_self_test import _verify_authorized_profiles
        self.write_profiles([real_profile()])
        prepare_profile_bundle(self.source, self.defaults, self.output)
        project = Path(__file__).resolve().parents[2]
        with patch.dict(os.environ, {"APPDATA": str(self.root / "appdata"), "QT_QPA_PLATFORM": "offscreen"}):
            result = _verify_authorized_profiles(project, self.root / "working", self.output)
        self.assertEqual(1, result["profiles"])
        self.assertEqual(3, result["autofill_checks"])
        self.assertTrue(result["autofill_verified"])
        self.assertTrue(result["fresh_install"])

    def test_portable_verification_rejects_missing_or_sample_resource(self):
        from mingo_assistant.app.portable_self_test import _verify_authorized_profiles
        with self.assertRaises(RuntimeError):
            _verify_authorized_profiles(self.root, self.root / "working", self.output)
        self.output.parent.mkdir()
        self.output.write_text('{"profiles": []}', encoding="utf-8")
        with self.assertRaises(RuntimeError):
            _verify_authorized_profiles(self.root, self.root / "working", self.output)
