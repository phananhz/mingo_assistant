"""Declarative routes for dossier workspaces and their return destinations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from PySide6.QtWidgets import QWidget

from mingo_assistant.ui.views.business_amendment_workspace import (
    BUSINESS_AMENDMENT_CASE_TYPE,
    BusinessAmendmentWorkspace,
)
from mingo_assistant.ui.views.business_registration_workspace import (
    BusinessRegistrationWorkspace,
)
from mingo_assistant.ui.views.household_business_workspace import (
    HOUSEHOLD_BUSINESS_CASE_TYPE,
    HouseholdBusinessWorkspace,
)
from mingo_assistant.ui.views.location_business_termination_workspace import (
    LOCATION_TERMINATION_CASE_TYPE,
    LocationBusinessTerminationWorkspace,
)
from mingo_assistant.ui.views.location_business_update_workspace import (
    LOCATION_UPDATE_CASE_TYPE,
    LocationBusinessUpdateWorkspace,
)
from mingo_assistant.ui.views.location_business_workspace import (
    LOCATION_CASE_TYPE,
    LocationBusinessWorkspace,
)


WorkspaceClass: TypeAlias = type[QWidget]


@dataclass(frozen=True)
class WorkspaceRoute:
    key: str
    case_types: frozenset[str]
    workspace_class: WorkspaceClass
    return_target: str
    nav_key: str
    dependent: bool = False


DEFAULT_WORKSPACE_ROUTE = WorkspaceRoute(
    key="business_registration",
    case_types=frozenset({
        "TNHH một thành viên",
        "TNHH hai thành viên (Cá nhân)",
        "TNHH hai thành viên trở lên",
        "TNHH hai thành viên trở lên (thành viên là cá nhân)",
    }),
    workspace_class=BusinessRegistrationWorkspace,
    return_target="business_registration",
    nav_key="business_registration",
)

WORKSPACE_ROUTES = (
    DEFAULT_WORKSPACE_ROUTE,
    WorkspaceRoute(
        key="business_amendment",
        case_types=frozenset({BUSINESS_AMENDMENT_CASE_TYPE}),
        workspace_class=BusinessAmendmentWorkspace,
        return_target="business_amendment",
        nav_key="business_amendment",
    ),
    WorkspaceRoute(
        key="household_business",
        case_types=frozenset({HOUSEHOLD_BUSINESS_CASE_TYPE}),
        workspace_class=HouseholdBusinessWorkspace,
        return_target="household_business",
        nav_key="household_business",
    ),
    WorkspaceRoute(
        key="dependent_unit_create",
        case_types=frozenset({LOCATION_CASE_TYPE}),
        workspace_class=LocationBusinessWorkspace,
        return_target="dependent_units",
        nav_key="dependent_units",
        dependent=True,
    ),
    WorkspaceRoute(
        key="dependent_unit_update",
        case_types=frozenset({LOCATION_UPDATE_CASE_TYPE}),
        workspace_class=LocationBusinessUpdateWorkspace,
        return_target="dependent_units",
        nav_key="dependent_units",
        dependent=True,
    ),
    WorkspaceRoute(
        key="dependent_unit_termination",
        case_types=frozenset({LOCATION_TERMINATION_CASE_TYPE}),
        workspace_class=LocationBusinessTerminationWorkspace,
        return_target="dependent_units",
        nav_key="dependent_units",
        dependent=True,
    ),
)

_ROUTE_BY_CASE_TYPE = {
    case_type: route
    for route in WORKSPACE_ROUTES
    for case_type in route.case_types
}
_ROUTE_BY_WORKSPACE_CLASS = {
    route.workspace_class: route
    for route in WORKSPACE_ROUTES
}


def route_for_case_type(case_type: str) -> WorkspaceRoute | None:
    return _ROUTE_BY_CASE_TYPE.get(case_type)


def route_for_workspace_class(workspace_class: WorkspaceClass) -> WorkspaceRoute | None:
    return _ROUTE_BY_WORKSPACE_CLASS.get(workspace_class)


def is_dependent_case_type(case_type: str) -> bool:
    route = route_for_case_type(case_type)
    return bool(route and route.dependent)
