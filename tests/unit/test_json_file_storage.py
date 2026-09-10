from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mingo_assistant.infrastructure.storage import read_json, write_json_atomic


class JsonFileStorageTests(unittest.TestCase):
    def test_write_replaces_existing_document_and_preserves_unicode(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "data.json"
            path.write_text('{"old": true}', encoding="utf-8")

            write_json_atomic(path, {"company_name": "C?ng ty Minh Gia"})

            self.assertEqual(read_json(path), {"company_name": "C?ng ty Minh Gia"})
            self.assertFalse(list(path.parent.glob(".data.json.*.tmp")))

    def test_failed_serialization_keeps_the_previous_document(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "data.json"
            path.write_text(json.dumps({"version": 1}), encoding="utf-8")

            with self.assertRaises(TypeError):
                write_json_atomic(path, {"unsupported": {"set"}})

            self.assertEqual(read_json(path), {"version": 1})
            self.assertFalse(list(path.parent.glob(".data.json.*.tmp")))
