from __future__ import annotations

import unittest

from mingo_assistant.ui.routing import (
    DEFAULT_WORKSPACE_ROUTE,
    WORKSPACE_ROUTES,
    is_dependent_case_type,
    route_for_case_type,
    route_for_workspace_class,
)
from mingo_assistant.ui.views.business_amendment_workspace import (
    BUSINESS_AMENDMENT_CASE_TYPE,
    BusinessAmendmentWorkspace,
)
from mingo_assistant.ui.views.location_business_termination_workspace import (
    LOCATION_TERMINATION_CASE_TYPE,
)
from mingo_assistant.ui.views.location_business_update_workspace import (
    LOCATION_UPDATE_CASE_TYPE,
)
from mingo_assistant.ui.views.location_business_workspace import LOCATION_CASE_TYPE
from mingo_assistant.ui.views.household_business_workspace import (
    HOUSEHOLD_BUSINESS_CASE_TYPE,
    HouseholdBusinessWorkspace,
)


class WorkspaceRegistryTest(unittest.TestCase):
    def test_every_case_type_resolves_to_one_route(self) -> None:
        all_case_types = [
            case_type
            for route in WORKSPACE_ROUTES
            for case_type in route.case_types
        ]

        self.assertEqual(len(all_case_types), len(set(all_case_types)))
        for case_type in all_case_types:
            with self.subTest(case_type=case_type):
                route = route_for_case_type(case_type)
                self.assertIsNotNone(route)
                self.assertIs(
                    route,
                    route_for_workspace_class(route.workspace_class),
                )

    def test_dependent_routes_stay_separate_from_amendment(self) -> None:
        for case_type in (
            LOCATION_CASE_TYPE,
            LOCATION_UPDATE_CASE_TYPE,
            LOCATION_TERMINATION_CASE_TYPE,
        ):
            with self.subTest(case_type=case_type):
                route = route_for_case_type(case_type)
                self.assertTrue(route.dependent)
                self.assertEqual("dependent_units", route.return_target)

        amendment = route_for_case_type(BUSINESS_AMENDMENT_CASE_TYPE)
        self.assertIs(BusinessAmendmentWorkspace, amendment.workspace_class)
        self.assertFalse(amendment.dependent)
        self.assertEqual("business_amendment", amendment.return_target)
        self.assertFalse(is_dependent_case_type(BUSINESS_AMENDMENT_CASE_TYPE))

    def test_registration_aliases_and_unknown_case_types_have_safe_results(self) -> None:
        self.assertIs(
            DEFAULT_WORKSPACE_ROUTE,
            route_for_case_type("TNHH một thành viên"),
        )
        self.assertIsNone(route_for_case_type("Workflow tương lai"))
        self.assertFalse(is_dependent_case_type("Workflow tương lai"))

    def test_household_business_has_an_independent_route(self) -> None:
        route = route_for_case_type(HOUSEHOLD_BUSINESS_CASE_TYPE)
        self.assertIsNotNone(route)
        self.assertIs(HouseholdBusinessWorkspace, route.workspace_class)
        self.assertEqual("household_business", route.return_target)
        self.assertEqual("household_business", route.nav_key)
        self.assertFalse(route.dependent)


if __name__ == "__main__":
    unittest.main()
