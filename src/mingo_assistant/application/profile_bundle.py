"""Prepare explicitly authorized personal-release data outside tracked assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from uuid import uuid4

from mingo_assistant.infrastructure.storage import read_json, write_json_atomic
from mingo_assistant.repositories.authorized_person_repository import AuthorizedPersonProfileRepository


SEED_FILENAME = "authorized_person_seed.json"
REQUIRED_PROFILE_FIELDS = (
    "authorized_person_full_name", "authorized_person_id_number", "authorized_person_issue_date",
    "authorized_person_issue_place", "authorized_person_contact_address", "authorized_person_phone",
)


def prepare_profile_bundle(source: Path, defaults: Path, output: Path) -> dict[str, object]:
    if output.name != SEED_FILENAME:
        raise ValueError(f"Private release resource must be named {SEED_FILENAME}.")
    if source.resolve() == output.resolve() or defaults.resolve() == output.resolve():
        raise ValueError("Release resource must not overwrite the source profiles or tracked defaults.")
    raw = read_json(source)
    if not isinstance(raw, dict):
        raise ValueError("Authorized profiles must be a JSON object.")
    if isinstance(raw.get("profiles"), list):
        profiles = raw["profiles"]
        selected = str(raw.get("selected_profile_id", ""))
    elif any(str(key).startswith("authorized_person_") for key in raw):
        profile = dict(raw)
        profile.setdefault("id", str(uuid4()))
        profiles, selected = [profile], str(profile["id"])
    else:
        raise ValueError("No authorized-person profiles found in the selected source.")
    source_ids = [str(profile.get("id", "")).strip()
                  for profile in AuthorizedPersonProfileRepository._profile_list(profiles)]
    if any(not identifier for identifier in source_ids) or len(set(source_ids)) != len(source_ids):
        raise ValueError("Source profiles have missing or duplicate profile IDs.")
    repository = AuthorizedPersonProfileRepository(source, defaults)
    payload = repository.merge(selected, profiles)
    prepared = payload["profiles"]
    if not isinstance(prepared, list) or not prepared:
        raise ValueError("No real authorized-person profiles are available; sample-only releases are rejected.")
    identifiers = set()
    for index, profile in enumerate(prepared, 1):
        identifier = str(profile.get("id", "")).strip()
        if not identifier or identifier in identifiers:
            raise ValueError(f"Profile {index} has a missing or duplicate ID.")
        identifiers.add(identifier)
        missing = [key for key in REQUIRED_PROFILE_FIELDS if not str(profile.get(key, "") or "").strip()]
        if missing:
            raise ValueError(f"Profile {index} is incomplete: {', '.join(missing)}")
        digits = re.sub(r"\D", "", str(profile["authorized_person_id_number"]))
        if not digits or not digits.replace("0", ""):
            raise ValueError(f"Profile {index} has a placeholder identity number.")
    write_json_atomic(output, {"schema_version": 1, **payload})
    return {"profiles": len(prepared), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--defaults", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    # No names, identity numbers, contacts, or profile values in build logs.
    print(json.dumps(prepare_profile_bundle(args.source, args.defaults, args.output)))


if __name__ == "__main__":
    main()
