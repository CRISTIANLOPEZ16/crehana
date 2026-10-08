import json
from pathlib import Path
from typing import cast

import pytest

from task_manager.infrastructure.http.api import create_app


def test_generated_routes_and_response_codes_match_contract() -> None:
    contract_path = (
        Path(__file__).parents[2]
        / "specs"
        / "001-manage-task-lists"
        / "contracts"
        / "openapi.json"
    )
    with contract_path.open(encoding="utf-8") as contract_file:
        contract = cast(dict[str, object], json.load(contract_file))
    contract_paths = cast(dict[str, dict[str, dict[str, object]]], contract["paths"])
    generated_paths = create_app().openapi()["paths"]

    for contract_path_name, contract_operations in contract_paths.items():
        generated_path_name = (
            contract_path_name
            if contract_path_name == "/health"
            else f"/api/v1{contract_path_name}"
        )
        assert generated_path_name in generated_paths
        for method_name, contract_operation in contract_operations.items():
            generated_operation = generated_paths[generated_path_name][method_name]
            expected_statuses = set(
                cast(dict[str, object], contract_operation["responses"])
            )
            actual_statuses = set(generated_operation["responses"])
            assert expected_statuses <= actual_statuses

    assert {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/me",
    } <= generated_paths.keys()


def test_collection_openapi_parameters_describe_runtime_contract() -> None:
    openapi_document = create_app().openapi()
    paths = openapi_document["paths"]
    component_schemas = cast(
        dict[str, dict[str, object]], openapi_document["components"]["schemas"]
    )
    collection_parameters: dict[str, dict[str, object]] = {
        "/api/v1/task-lists": paths["/api/v1/task-lists"]["get"],
        "/api/v1/task-lists/{list_id}/tasks": paths[
            "/api/v1/task-lists/{list_id}/tasks"
        ]["get"],
    }
    for path, operation in collection_parameters.items():
        parameters = cast(list[dict[str, object]], operation.get("parameters", []))
        by_name: dict[str, dict[str, object]] = {
            str(parameter["name"]): parameter
            for parameter in parameters
            if parameter.get("in") == "query"
        }
        assert {"limit", "offset"} <= by_name.keys(), path
        limit_schema = cast(dict[str, object], by_name["limit"]["schema"])
        offset_schema = cast(dict[str, object], by_name["offset"]["schema"])
        assert limit_schema["default"] == 20
        assert limit_schema["minimum"] == 1
        assert limit_schema["maximum"] == 100
        assert offset_schema["default"] == 0
        assert offset_schema["minimum"] == 0

    task_query = collection_parameters["/api/v1/task-lists/{list_id}/tasks"]
    task_parameters = cast(list[dict[str, object]], task_query.get("parameters", []))
    task_by_name: dict[str, dict[str, object]] = {
        str(parameter["name"]): parameter
        for parameter in task_parameters
        if parameter.get("in") == "query"
    }
    for name, values in {
        "status": ["pending", "in_progress", "completed"],
        "priority": ["low", "medium", "high"],
    }.items():
        parameter_schema = cast(dict[str, object], task_by_name[name]["schema"])
        enum_schema: dict[str, object] = parameter_schema
        any_of: object = parameter_schema.get("anyOf")
        if isinstance(any_of, list):
            enum_schema = cast(dict[str, object], any_of[0])
        if "$ref" in enum_schema:
            component_name = str(enum_schema["$ref"]).split("/")[-1]
            enum_schema = component_schemas[component_name]
        assert enum_schema["enum"] == values


def test_api_docs_are_configurable_and_declare_oauth2_password_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_API_DOCS", "true")
    openapi = create_app().openapi()
    scheme_map = cast(
        dict[str, dict[str, object]],
        openapi["components"]["securitySchemes"],
    )
    oauth_scheme = next(iter(scheme_map.values()))
    assert oauth_scheme["type"] == "oauth2"
    flows = cast(dict[str, dict[str, object]], oauth_scheme["flows"])
    assert flows["password"]["tokenUrl"] == "/api/v1/auth/login"
    assert "/docs" in {getattr(route, "path", "") for route in create_app().routes}

    monkeypatch.setenv("ENABLE_API_DOCS", "false")
    assert "/docs" not in {getattr(route, "path", "") for route in create_app().routes}


def test_access_and_invitation_openapi_contract_is_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_API_DOCS", "true")
    document = create_app().openapi()
    paths = document["paths"]
    protected_operations = {
        ("/api/v1/auth/me", "get"),
        ("/api/v1/task-lists/{list_id}/participants", "get"),
        ("/api/v1/task-lists/{list_id}/participants/{user_id}", "delete"),
        ("/api/v1/task-lists/{list_id}/invitations", "post"),
        ("/api/v1/task-lists/{list_id}/invitations", "get"),
        ("/api/v1/task-lists/{list_id}/invitations/{invitation_id}", "get"),
        ("/api/v1/invitations/accept", "post"),
        ("/api/v1/task-lists/{list_id}/invitations/{invitation_id}/revoke", "post"),
        ("/api/v1/task-lists/{list_id}/invitations/{invitation_id}/resend", "post"),
    }
    for path, method in protected_operations:
        operation = paths[path][method]
        assert operation["security"], (path, method)
        assert {"401", "422", "500"} <= set(operation["responses"])

    for path, method in [
        ("/api/v1/auth/register", "post"),
        ("/api/v1/auth/login", "post"),
        ("/health", "get"),
    ]:
        assert "security" not in paths[path][method]

    for path in [
        "/api/v1/task-lists/{list_id}/participants",
        "/api/v1/task-lists/{list_id}/invitations",
    ]:
        parameters = cast(list[dict[str, object]], paths[path]["get"]["parameters"])
        query = {
            str(item["name"]): item for item in parameters if item["in"] == "query"
        }
        assert set(query) == {"limit", "offset"}
        assert cast(dict[str, object], query["limit"]["schema"])["default"] == 20
        assert cast(dict[str, object], query["limit"]["schema"])["maximum"] == 100
        assert cast(dict[str, object], query["offset"]["schema"])["minimum"] == 0

    schemas = cast(dict[str, dict[str, object]], document["components"]["schemas"])
    assert "acceptance_token" in cast(
        dict[str, object], schemas["IssuedInvitationResponse"]["properties"]
    )
    assert "acceptance_token" not in cast(
        dict[str, object], schemas["InvitationResponse"]["properties"]
    )
    assert "password_hash" not in json.dumps(schemas)
    assert "token_hash" not in json.dumps(schemas)
    login_body = cast(
        dict[str, object], paths["/api/v1/auth/login"]["post"]["requestBody"]
    )
    assert "application/x-www-form-urlencoded" in cast(
        dict[str, object], login_body["content"]
    )
