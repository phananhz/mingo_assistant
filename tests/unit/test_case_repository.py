from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from mingo_assistant.application.cases import CaseUseCases
from mingo_assistant.core.errors import CorruptDataError
from mingo_assistant.models.case import CaseSummary
from mingo_assistant.repositories.case_repository import CaseRepository


def _case(case_id: str = "case-test") -> CaseSummary:
    return CaseSummary(
        id=case_id,
        company_name="CONG TY TNHH TEST",
        case_type="TNHH mot thanh vien",
        owner="NGUYEN VAN TEST",
        updated_at="01/01/2026",
        status="Ban nhap",
        condition="Can kiem tra",
        members=1,
        capital="1000000",
    )


class CaseRepositoryTest(unittest.TestCase):
    def test_reads_legacy_list_and_writes_versioned_payload(self) -> None:
        with TemporaryDirectory() as temporary:
            data_file = Path(temporary) / "cases.json"
            data_file.write_text(json.dumps([_case().to_dict()]), encoding="utf-8")
            repository = CaseRepository(data_file)

            loaded = repository.list_cases()
            repository.save_case(loaded[0])
            stored = json.loads(data_file.read_text(encoding="utf-8"))

            self.assertEqual([case.id for case in loaded], ["case-test"])
            self.assertEqual(stored["schema_version"], CaseRepository.SCHEMA_VERSION)
            self.assertEqual(stored["cases"][0]["id"], "case-test")

    def test_rejects_unknown_shape_without_overwriting_it(self) -> None:
        with TemporaryDirectory() as temporary:
            data_file = Path(temporary) / "cases.json"
            original = '{"unexpected": true}'
            data_file.write_text(original, encoding="utf-8")
            repository = CaseRepository(data_file)

            with self.assertRaises(CorruptDataError) as raised:
                repository.list_cases()

            self.assertEqual(data_file.read_text(encoding="utf-8"), original)
            self.assertIsNotNone(raised.exception.backup_path)
            self.assertEqual(raised.exception.backup_path.read_text(encoding="utf-8"), original)

    def test_invalid_json_is_preserved_for_recovery(self) -> None:
        with TemporaryDirectory() as temporary:
            data_file = Path(temporary) / "cases.json"
            original = '{"cases": ['
            data_file.write_text(original, encoding="utf-8")

            with self.assertRaises(CorruptDataError) as raised:
                CaseRepository(data_file).list_cases()

            self.assertEqual(data_file.read_text(encoding="utf-8"), original)
            self.assertEqual(raised.exception.backup_path.read_text(encoding="utf-8"), original)

    def test_use_cases_delegate_case_lifecycle(self) -> None:
        with TemporaryDirectory() as temporary:
            repository = CaseRepository(Path(temporary) / "cases.json")
            use_cases = CaseUseCases(repository)
            use_cases.save(_case("case-lifecycle"))
            use_cases.move_to_trash("case-lifecycle")
            self.assertEqual([case.id for case in use_cases.list_deleted()], ["case-lifecycle"])

            use_cases.restore("case-lifecycle")

            self.assertEqual(use_cases.get("case-lifecycle").id, "case-lifecycle")


if __name__ == "__main__":
    unittest.main()
