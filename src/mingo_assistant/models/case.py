from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class CaseSummary:
    id: str
    company_name: str
    case_type: str
    owner: str
    updated_at: str
    status: str
    condition: str
    members: int
    capital: str
    warning: str | None = None
    export_dir: str = ""
    exported_at: str = ""
    generated_documents: list[str] = field(default_factory=list)
    is_deleted: bool = False
    deleted_at: str = ""
    form_values: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.company_name

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CaseSummary":
        return cls(
            id=str(data.get("id", "")),
            company_name=str(data.get("company_name", "")),
            case_type=str(data.get("case_type", "")),
            owner=str(data.get("owner", "")),
            updated_at=str(data.get("updated_at", "")),
            status=str(data.get("status", "")),
            condition=str(data.get("condition", "")),
            members=int(data.get("members", 0) or 0),
            capital=str(data.get("capital", "")),
            warning=str(data["warning"]) if data.get("warning") else None,
            export_dir=str(data.get("export_dir", "")),
            exported_at=str(data.get("exported_at", "")),
            generated_documents=[
                str(item) for item in data.get("generated_documents", []) if item
            ],
            is_deleted=bool(data.get("is_deleted", False)),
            deleted_at=str(data.get("deleted_at", "")),
            form_values={
                str(key): str(value)
                for key, value in (data.get("form_values", {}) or {}).items()
            },
        )
