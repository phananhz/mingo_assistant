from __future__ import annotations

from typing import Mapping


AUTHORIZED_PERSON_FULL_NAME = "authorized_person_full_name"


def uppercase_authorized_person_name(value: object) -> str:
    """Return the authorized person's name in the required document style."""
    return str(value or "").strip().upper()


def normalize_authorized_person_values(values: Mapping[str, object]) -> dict[str, str]:
    normalized = {str(key): str(value or "") for key, value in values.items()}
    if AUTHORIZED_PERSON_FULL_NAME in normalized:
        normalized[AUTHORIZED_PERSON_FULL_NAME] = uppercase_authorized_person_name(
            normalized[AUTHORIZED_PERSON_FULL_NAME]
        )
    return normalized
