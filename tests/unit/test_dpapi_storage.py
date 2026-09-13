from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mingo_assistant.infrastructure.security import DpapiJsonStorage, WindowsDpapiProtector


@unittest.skipUnless(os.name == "nt", "Windows DPAPI test")
class DpapiStorageTests(unittest.TestCase):
    def test_round_trip_uses_current_windows_user_without_hardcoded_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "secure.json"
            storage = DpapiJsonStorage(path, WindowsDpapiProtector())
            payload = {
                "authorized_person_full_name": "NGUYỄN VĂN TEST",
                "authorized_person_id_number": "012345678901",
            }

            storage.write(payload)

            self.assertEqual(storage.read(), payload)
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(DpapiJsonStorage.HEADER))
            self.assertNotIn("NGUYỄN VĂN TEST".encode("utf-8"), raw)


if __name__ == "__main__":
    unittest.main()
