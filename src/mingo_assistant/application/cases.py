from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mingo_assistant.models.case import CaseSummary


class CaseRepositoryPort(Protocol):
    def list_cases(self) -> list[CaseSummary]: ...

    def list_deleted_cases(self) -> list[CaseSummary]: ...

    def get_case(self, case_id: str) -> CaseSummary | None: ...

    def save_case(self, case: CaseSummary) -> None: ...

    def soft_delete_case(self, case_id: str) -> None: ...

    def restore_case(self, case_id: str) -> None: ...

    def delete_case_permanently(self, case_id: str) -> None: ...

    def empty_trash(self) -> None: ...


@dataclass(frozen=True)
class CaseUseCases:
    repository: CaseRepositoryPort

    def list_active(self) -> list[CaseSummary]:
        return self.repository.list_cases()

    def list_deleted(self) -> list[CaseSummary]:
        return self.repository.list_deleted_cases()

    def get(self, case_id: str) -> CaseSummary | None:
        return self.repository.get_case(case_id)

    def save(self, case: CaseSummary) -> None:
        self.repository.save_case(case)

    def move_to_trash(self, case_id: str) -> None:
        self.repository.soft_delete_case(case_id)

    def restore(self, case_id: str) -> None:
        self.repository.restore_case(case_id)

    def delete_permanently(self, case_id: str) -> None:
        self.repository.delete_case_permanently(case_id)

    def empty_trash(self) -> None:
        self.repository.empty_trash()
