import json
from pathlib import Path
from typing import cast

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
            assert actual_statuses == expected_statuses

    assert len(contract_paths) == len(generated_paths)
