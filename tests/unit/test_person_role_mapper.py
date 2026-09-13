from __future__ import annotations

import unittest

from mingo_assistant.application.people import (
    PersonIdentityRules,
    PersonProfileSynchronizer,
    PersonRoleMapper,
)


class _ParsedAddress:
    street_line = "1 Đường Test"
    village = ""
    ward = "Phường Test"
    province = "Tỉnh Test"


class _AddressParser:
    def parse(self, _address: str):
        return _ParsedAddress()


class PersonRoleMapperTests(unittest.TestCase):
    def test_maps_applicant_address_to_structured_fields(self) -> None:
        mapper = PersonRoleMapper(_AddressParser())
        values = {
            "legal_representative_full_name": "NGUYỄN VĂN TEST",
            "legal_representative_id_number": "012345678901",
            "legal_representative_permanent_address": "địa chỉ đầu vào",
        }

        mapped = mapper.map_fields(values, "applicant", 1)

        self.assertEqual(mapped["applicant_full_name"], "NGUYỄN VĂN TEST")
        self.assertEqual(mapped["applicant_address_detail"], "1 Đường Test")
        self.assertEqual(mapped["applicant_ward"], "Phường Test")
        self.assertEqual(mapped["applicant_province"], "Tỉnh Test")

    def test_authorized_person_uses_explicit_contact_fallback(self) -> None:
        mapper = PersonRoleMapper(_AddressParser())
        mapped = mapper.map_fields(
            {
                "legal_representative_full_name": "NGUYỄN VĂN TEST",
                "legal_representative_permanent_address": "Địa chỉ thường trú",
            },
            "authorized_person",
            1,
        )

        self.assertEqual(mapped["authorized_person_contact_address"], "Địa chỉ thường trú")

    def test_identity_rules_clear_only_contacts_copied_across_distinct_people(self) -> None:
        values = {
            "applicant_id_number": "012345678901",
            "authorized_person_id_number": "012345678902",
            "applicant_phone": "0900000000",
            "authorized_person_phone": "0900000000",
            "applicant_email": "test@example.invalid",
            "authorized_person_email": "TEST@example.invalid",
        }

        PersonIdentityRules.clear_cross_person_authorized_contacts(values)

        self.assertEqual(values["applicant_phone"], "")
        self.assertEqual(values["applicant_email"], "")

    def test_profile_synchronizer_updates_only_matching_people_and_roles(self) -> None:
        class Person:
            def __init__(self, identity: str) -> None:
                self.data = {"legal_representative_id_number": identity, "unchanged": "yes"}
                self.recognition_type = ""

        matching = Person("CCCD 012345678901")
        other = Person("012345678902")
        synchronizer = PersonProfileSynchronizer()
        card_values = {
            "legal_representative_id_number": "012345678903",
            "legal_representative_full_name": "NGUYỄN VĂN TEST",
        }
        identities = synchronizer.identity_numbers(card_values, "012345678901")

        count = synchronizer.update_people([matching, other], card_values, identities)
        roles = synchronizer.matching_roles(
            {
                "legal_representative_id_number": "012345678901",
                "applicant_id_number": "012345678902",
                "authorized_person_id_number": "012345678903",
            },
            identities,
        )

        self.assertEqual(count, 1)
        self.assertEqual(matching.data["legal_representative_id_number"], "012345678903")
        self.assertEqual(matching.data["unchanged"], "yes")
        self.assertEqual(other.data["legal_representative_id_number"], "012345678902")
        self.assertEqual(roles, ["legal_representative", "authorized_person"])


if __name__ == "__main__":
    unittest.main()
