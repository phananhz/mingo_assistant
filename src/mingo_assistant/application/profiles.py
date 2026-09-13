from __future__ import annotations

from typing import Protocol


class AuthorizedPersonRepositoryPort(Protocol):
    def load(self) -> dict[str, object]: ...

    def save(self, payload: dict[str, object]) -> None: ...

    def default_profiles(self) -> list[dict[str, str]]: ...

    def is_default(self, profile_id: str) -> bool: ...

    def merge(self, selected_profile_id: str, profiles: list[dict[str, str]]) -> dict[str, object]: ...


class AuthorizedPersonUseCases:
    """Application operations for fixed and machine-local authorized profiles."""

    def __init__(self, repository: AuthorizedPersonRepositoryPort) -> None:
        self.repository = repository

    def load(self) -> dict[str, object]:
        return self.repository.load()

    def save(self, payload: dict[str, object]) -> None:
        self.repository.save(payload)

    def defaults(self) -> list[dict[str, str]]:
        return self.repository.default_profiles()

    def is_default(self, profile_id: str) -> bool:
        return self.repository.is_default(profile_id)

    def merge(self, selected_profile_id: str, profiles: list[dict[str, str]]) -> dict[str, object]:
        return self.repository.merge(selected_profile_id, profiles)

    def selected(self) -> dict[str, object]:
        payload = self.load()
        profiles = payload.get("profiles", [])
        if not isinstance(profiles, list):
            profiles = []
        selected_id = str(payload.get("selected_profile_id", ""))
        selected = next(
            (
                profile
                for profile in profiles
                if isinstance(profile, dict) and str(profile.get("id", "")) == selected_id
            ),
            profiles[0] if profiles else {},
        )
        result = dict(selected) if isinstance(selected, dict) else {}
        result["__profiles"] = profiles
        return result

