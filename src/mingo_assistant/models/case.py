from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field

from mingo_assistant.models.form_values import LEGACY_FORM_SCHEMA_VERSION, normalize_form_values


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
    export_versions: list[dict[str, object]] = field(default_factory=list)
    is_deleted: bool = False
    deleted_at: str = ""
    form_values: dict[str, str] = field(default_factory=dict)
    form_schema_version: int = LEGACY_FORM_SCHEMA_VERSION

    @property
    def name(self) -> str:
        return self.company_name

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "CaseSummary":
        raw_documents = data.get("generated_documents", [])
        generated_documents = raw_documents if isinstance(raw_documents, list) else []
        raw_versions = data.get("export_versions", [])
        export_versions = raw_versions if isinstance(raw_versions, list) else []
        raw_form_values = data.get("form_values", {})
        form_values = raw_form_values if isinstance(raw_form_values, Mapping) else {}
        try:
            form_schema_version = int(
                str(data.get("form_schema_version", LEGACY_FORM_SCHEMA_VERSION)
                or LEGACY_FORM_SCHEMA_VERSION
                )
            )
        except (TypeError, ValueError):
            form_schema_version = LEGACY_FORM_SCHEMA_VERSION
        return cls(
            id=str(data.get("id", "")),
            company_name=str(data.get("company_name", "")),
            case_type=str(data.get("case_type", "")),
            owner=str(data.get("owner", "")),
            updated_at=str(data.get("updated_at", "")),
            status=str(data.get("status", "")),
            condition=str(data.get("condition", "")),
            members=int(str(data.get("members", 0) or 0)),
            capital=str(data.get("capital", "")),
            warning=str(data["warning"]) if data.get("warning") else None,
            export_dir=str(data.get("export_dir", "")),
            exported_at=str(data.get("exported_at", "")),
            generated_documents=[
                str(item) for item in generated_documents if item
            ],
            export_versions=[
                dict(item)
                for item in export_versions
                if isinstance(item, dict)
            ],
            is_deleted=bool(data.get("is_deleted", False)),
            deleted_at=str(data.get("deleted_at", "")),
            form_schema_version=form_schema_version,
            form_values=normalize_form_values(form_values),
        )
