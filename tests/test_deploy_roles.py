# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from types import SimpleNamespace
from unittest.mock import call
from looker_deployer.commands import deploy_roles
from looker_deployer.utils.exceptions import LookerCLIError
import pytest


@pytest.fixture
def mock_run_subprocess_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_roles.run_subprocess_command")


def test_get_filtered_roles(mock_run_subprocess_command):
    mock_run_subprocess_command.return_value.returncode = 0
    mock_run_subprocess_command.return_value.stdout = json.dumps([
        {"name": "Taco", "id": 1},
        {"name": "Burrito", "id": 2}
    ])
    mock_run_subprocess_command.return_value.stderr = ""

    creds = {"base_url": "test"}
    roles = deploy_roles.get_filtered_roles(creds)

    assert len(roles) == 2
    assert roles[0].name == "Taco"
    assert roles[1].name == "Burrito"

    mock_run_subprocess_command.assert_called_once_with(
        ["looker-cli", "api", "role", "all_roles"],
        creds=creds,
        text=True,
        input=None
    )


def test_get_filtered_roles_filter(mock_run_subprocess_command):
    mock_run_subprocess_command.return_value.returncode = 0
    mock_run_subprocess_command.return_value.stdout = json.dumps([
        {"name": "Taco", "id": 1},
        {"name": "Burrito", "id": 2}
    ])
    mock_run_subprocess_command.return_value.stderr = ""

    creds = {"base_url": "test"}
    roles = deploy_roles.get_filtered_roles(creds, "Burrito")

    assert len(roles) == 1
    assert roles[0].name == "Burrito"


def test_write_roles_new(mock_run_subprocess_command, mocker):
    permission_set = SimpleNamespace(name="P1", id=1)
    model_set = SimpleNamespace(name="M1", id=1)
    role_list = [SimpleNamespace(
        name="Taco",
        permission_set=permission_set,
        model_set=model_set
    )]

    def side_effect(cmd, **kwargs):
        class MockResult:
            returncode = 0
            stderr = ""
        res = MockResult()

        if "all_roles" in cmd:
            res.stdout = "[]"
        elif "all_permission_sets" in cmd:
            res.stdout = json.dumps([{"name": "P1", "id": 10}])
        elif "all_model_sets" in cmd:
            res.stdout = json.dumps([{"name": "M1", "id": 20}])
        elif "create_role" in cmd:
            res.stdout = json.dumps({"name": "Taco", "id": 5})
        else:
            res.stdout = ""
        return res

    mock_run_subprocess_command.side_effect = side_effect

    target_creds = {"base_url": "target"}
    deploy_roles.write_roles(role_list, target_creds)

    expected_body = {
        "name": "Taco",
        "permission_set_id": 10,
        "model_set_id": 20
    }

    mock_run_subprocess_command.assert_has_calls([
        call(["looker-cli", "api", "role", "all_roles"], creds=target_creds, text=True, input=None),
        call(["looker-cli", "api", "role", "all_permission_sets"], creds=target_creds, text=True, input=None),
        call(["looker-cli", "api", "role", "all_model_sets"], creds=target_creds, text=True, input=None),
        call(["looker-cli", "api", "role", "create_role", "-"], creds=target_creds, text=True, input=json.dumps(expected_body))
    ], any_order=False)


def test_write_roles_existing(mock_run_subprocess_command, mocker):
    permission_set = SimpleNamespace(name="P1", id=1)
    model_set = SimpleNamespace(name="M1", id=1)
    role_list = [SimpleNamespace(
        name="Taco",
        permission_set=permission_set,
        model_set=model_set
    )]

    def side_effect(cmd, **kwargs):
        class MockResult:
            returncode = 0
            stderr = ""
        res = MockResult()

        if "all_roles" in cmd:
            res.stdout = json.dumps([{"name": "Taco", "id": 5}])
        elif "all_permission_sets" in cmd:
            res.stdout = json.dumps([{"name": "P1", "id": 10}])
        elif "all_model_sets" in cmd:
            res.stdout = json.dumps([{"name": "M1", "id": 20}])
        elif "update_role" in cmd:
            res.stdout = json.dumps({"name": "Taco", "id": 5})
        else:
            res.stdout = ""
        return res

    mock_run_subprocess_command.side_effect = side_effect

    target_creds = {"base_url": "target"}
    deploy_roles.write_roles(role_list, target_creds)

    expected_body = {
        "name": "Taco",
        "permission_set_id": 10,
        "model_set_id": 20
    }

    mock_run_subprocess_command.assert_has_calls([
        call(["looker-cli", "api", "role", "all_roles"], creds=target_creds, text=True, input=None),
        call(["looker-cli", "api", "role", "all_permission_sets"], creds=target_creds, text=True, input=None),
        call(["looker-cli", "api", "role", "all_model_sets"], creds=target_creds, text=True, input=None),
        call(["looker-cli", "api", "role", "update_role", "5", "-"], creds=target_creds, text=True, input=json.dumps(expected_body))
    ], any_order=False)


def test_write_roles_delete(mock_run_subprocess_command, mocker):
    role_list = []

    def side_effect(cmd, **kwargs):
        class MockResult:
            returncode = 0
            stderr = ""
        res = MockResult()

        if "all_roles" in cmd:
            res.stdout = json.dumps([{"name": "Burrito", "id": 6}])
        elif "all_permission_sets" in cmd:
            res.stdout = "[]"
        elif "all_model_sets" in cmd:
            res.stdout = "[]"
        else:
            res.stdout = ""
        return res

    mock_run_subprocess_command.side_effect = side_effect

    target_creds = {"base_url": "target"}
    deploy_roles.write_roles(role_list, target_creds, allow_delete=True)

    mock_run_subprocess_command.assert_has_calls([
        call(["looker-cli", "api", "role", "all_roles"], creds=target_creds, text=True, input=None),
        call(["looker-cli", "api", "role", "all_permission_sets"], creds=target_creds, text=True, input=None),
        call(["looker-cli", "api", "role", "all_model_sets"], creds=target_creds, text=True, input=None),
        call(["looker-cli", "api", "role", "delete_role", "6"], creds=target_creds, text=True, input=None)
    ], any_order=False)


def test_send_roles(mocker):
    mock_get = mocker.patch("looker_deployer.commands.deploy_roles.get_filtered_roles")
    mock_write = mocker.patch("looker_deployer.commands.deploy_roles.write_roles")

    mock_get.return_value = ["mock_role"]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_roles.send_roles(source_creds, target_creds, "pattern", True)

    mock_get.assert_called_once_with(source_creds, "pattern")
    mock_write.assert_called_once_with(["mock_role"], target_creds, "pattern", True)


def test_main(mocker):
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_roles.build_creds")
    mock_send = mocker.patch("looker_deployer.commands.deploy_roles.send_roles")

    mock_build_creds.side_effect = lambda ini, name: {f"{name}_creds": "true"}

    args = SimpleNamespace(
        debug=True,
        ini="test.ini",
        source="source_env",
        target=["target_env1", "target_env2"],
        pattern="pattern",
        delete=True
    )

    deploy_roles.main(args)

    assert mock_build_creds.call_count == 3
    mock_build_creds.assert_has_calls([
        call("test.ini", "source_env"),
        call("test.ini", "target_env1"),
        call("test.ini", "target_env2")
    ], any_order=True)

    assert mock_send.call_count == 2
    mock_send.assert_has_calls([
        call({"source_env_creds": "true"}, {"target_env1_creds": "true"}, "pattern", True),
        call({"source_env_creds": "true"}, {"target_env2_creds": "true"}, "pattern", True)
    ], any_order=True)


# --- Stress / Robustness Tests ---

def test_run_cli_command_failure(mock_run_subprocess_command):
    mock_run_subprocess_command.side_effect = LookerCLIError(
        command="looker-cli role search",
        exit_code=1,
        stdout="",
        stderr="Error: server unavailable"
    )

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_roles.run_cli_command(creds, ["role", "search"])


def test_run_cli_command_invalid_json(mock_run_subprocess_command):
    mock_run_subprocess_command.return_value.returncode = 0
    mock_run_subprocess_command.return_value.stdout = "Invalid JSON string"
    mock_run_subprocess_command.return_value.stderr = ""

    creds = {"base_url": "test"}
    with pytest.raises(Exception) as exc_info:
        deploy_roles.run_cli_command(creds, ["role", "search"])
    assert "Failed to parse CLI output as JSON" in str(exc_info.value)


def test_run_cli_command_empty_output_lists(mock_run_subprocess_command):
    mock_run_subprocess_command.return_value.returncode = 0
    mock_run_subprocess_command.return_value.stdout = ""
    mock_run_subprocess_command.return_value.stderr = ""

    creds = {"base_url": "test"}
    # Should return empty list if command is search/list/all_permission_sets/all_model_sets
    res = deploy_roles.run_cli_command(creds, ["role", "search"])
    assert res == []

    # Should return None if command is something else (e.g. role delete)
    res = deploy_roles.run_cli_command(creds, ["role", "delete", "1"])
    assert res is None


def test_get_filtered_roles_admin_exclusion(mock_run_subprocess_command):
    mock_run_subprocess_command.return_value.returncode = 0
    mock_run_subprocess_command.return_value.stdout = json.dumps([
        {"name": "Admin", "id": 1},
        {"name": "Developer", "id": 2},
        {"name": "User", "id": 3}
    ])
    mock_run_subprocess_command.return_value.stderr = ""

    creds = {"base_url": "test"}
    roles = deploy_roles.get_filtered_roles(creds)
    assert len(roles) == 2
    assert all(r.name != "Admin" for r in roles)
    assert any(r.name == "Developer" for r in roles)
    assert any(r.name == "User" for r in roles)


def test_write_roles_delete_missing_id(mock_run_subprocess_command, mocker):
    role_list = []

    def side_effect(cmd, **kwargs):
        class MockResult:
            returncode = 0
            stdout = ""
            stderr = ""
        res = MockResult()

        if "all_roles" in cmd:
            res.stdout = json.dumps([{"name": "Burrito"}])  # Role has no "id" field!
        elif "all_permission_sets" in cmd:
            res.stdout = "[]"
        elif "all_model_sets" in cmd:
            res.stdout = "[]"
        return res

    mock_run_subprocess_command.side_effect = side_effect

    target_creds = {"base_url": "target"}
    with pytest.raises(AttributeError):
        deploy_roles.write_roles(role_list, target_creds, allow_delete=True)


def test_write_roles_update_missing_id(mock_run_subprocess_command, mocker):
    permission_set = SimpleNamespace(name="P1", id=1)
    model_set = SimpleNamespace(name="M1", id=1)
    role_list = [SimpleNamespace(
        name="Taco",
        permission_set=permission_set,
        model_set=model_set
    )]

    def side_effect(cmd, **kwargs):
        class MockResult:
            returncode = 0
            stderr = ""
        res = MockResult()

        if "role" in cmd and "search" in cmd:
            res.stdout = json.dumps([{"name": "Taco"}])  # Existing role has no "id"!
        elif "all_permission_sets" in cmd:
            res.stdout = json.dumps([{"name": "P1", "id": 10}])
        elif "all_model_sets" in cmd:
            res.stdout = json.dumps([{"name": "M1", "id": 20}])
        return res

    mock_run_subprocess_command.side_effect = side_effect

    target_creds = {"base_url": "target"}
    with pytest.raises(AttributeError):
        deploy_roles.write_roles(role_list, target_creds)


def test_write_roles_delete_failure(mock_run_subprocess_command, mocker):
    role_list = []

    def side_effect(cmd, **kwargs):
        class MockResult:
            returncode = 0
            stderr = ""
            stdout = ""
        res = MockResult()

        if "all_roles" in cmd:
            res.stdout = json.dumps([{"name": "Burrito", "id": 6}])
        elif "all_permission_sets" in cmd or "all_model_sets" in cmd:
            res.stdout = "[]"
        elif "delete_role" in cmd:
            raise LookerCLIError(
                command="looker-cli api role delete_role 6",
                exit_code=1,
                stdout="",
                stderr="Role 6 is currently assigned to users and cannot be deleted"
            )
        return res

    mock_run_subprocess_command.side_effect = side_effect

    target_creds = {"base_url": "target"}
    with pytest.raises(LookerCLIError):
        deploy_roles.write_roles(role_list, target_creds, allow_delete=True)


def test_write_roles_source_missing_name(mock_run_subprocess_command, mocker):
    role_list = [SimpleNamespace()]

    def side_effect(cmd, **kwargs):
        class MockResult:
            returncode = 0
            stderr = ""
            stdout = ""
        res = MockResult()

        if "all_roles" in cmd:
            res.stdout = json.dumps([{"name": "Taco", "id": 1}])
        elif "all_permission_sets" in cmd or "all_model_sets" in cmd:
            res.stdout = "[]"
        return res

    mock_run_subprocess_command.side_effect = side_effect

    target_creds = {"base_url": "target"}
    with pytest.raises(AttributeError):
        deploy_roles.write_roles(role_list, target_creds)
