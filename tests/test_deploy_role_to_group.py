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
import pytest
from types import SimpleNamespace
from unittest.mock import call

from looker_deployer.commands import deploy_role_to_group
from looker_deployer.commands import deploy_groups
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_role_to_group.run_cli_command")


def test_get_filtered_roles(mock_run_cli_command):
    role_list = [
        {"name": "Taco", "id": 1},
        {"name": "Burrito", "id": 2}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(role_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    roles = deploy_role_to_group.get_filtered_roles(creds)
    assert [r.name for r in roles] == ["Taco", "Burrito"]
    assert [r.id for r in roles] == [1, 2]
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "all_roles"],
        creds=creds,
        text=True
    )


def test_get_filtered_roles_filter(mock_run_cli_command):
    role_list = [
        {"name": "Taco", "id": 1},
        {"name": "Burrito", "id": 2}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(role_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    roles = deploy_role_to_group.get_filtered_roles(creds, "Burrito")
    assert [r.name for r in roles] == ["Burrito"]
    assert [r.id for r in roles] == [2]


def test_get_filtered_roles_command_not_found(mock_run_cli_command):
    mock_run_cli_command.side_effect = FileNotFoundError("No such file or directory")
    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_role_to_group.get_filtered_roles(creds)
    assert "looker-cli command not found" in str(exc_info.value)


def test_get_filtered_roles_exit_code_non_zero(mock_run_cli_command):
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "API Error")
    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_role_to_group.get_filtered_roles(creds)


def test_get_filtered_roles_malformed_json(mock_run_cli_command):
    mock_res = SimpleNamespace(stdout="not valid JSON", stderr="")
    mock_run_cli_command.return_value = mock_res
    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_role_to_group.get_filtered_roles(creds)
    assert "Failed to parse JSON" in str(exc_info.value)


def test_get_filtered_roles_unexpected_structure(mock_run_cli_command):
    mock_res = SimpleNamespace(stdout='"string instead of list/dict"', stderr="")
    mock_run_cli_command.return_value = mock_res
    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_role_to_group.get_filtered_roles(creds)
    assert "Unexpected JSON structure" in str(exc_info.value)


def test_write_role_to_group_new(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    source_roles = [SimpleNamespace(name="Explorer", id=1)]
    target_roles = [SimpleNamespace(name="Explorer", id=10)]

    target_groups = [
        SimpleNamespace(name="Taco", id=101),
        SimpleNamespace(name="Burrito", id=102)
    ]

    source_role_groups = [{"name": "Taco", "id": 1}]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    def sub_run_side_effect(cmd, **kwargs):
        if "role_groups" in cmd:
            return SimpleNamespace(stdout=json.dumps(source_role_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = sub_run_side_effect

    deploy_role_to_group.write_role_to_group(source_creds, target_creds)

    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "role", "role_groups", "1"], creds=source_creds, text=True),
        call(["looker-cli", "api", "role", "set_role_groups", "10", "-"], creds=target_creds, text=True, input="[101]")
    ])


def test_write_role_to_group_missing_role_name_or_id(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    source_roles = [
        SimpleNamespace(name="Explorer", id=1),
        SimpleNamespace(name=None, id=2),
        SimpleNamespace(name="Viewer", id=None)
    ]
    target_roles = [SimpleNamespace(name="Explorer", id=10)]
    target_groups = [SimpleNamespace(name="Taco", id=101)]
    source_role_groups = [{"name": "Taco", "id": 1}]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    def sub_run_side_effect(cmd, **kwargs):
        if "role_groups" in cmd:
            return SimpleNamespace(stdout=json.dumps(source_role_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = sub_run_side_effect

    deploy_role_to_group.write_role_to_group(source_creds, target_creds)

    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "role", "role_groups", "1"], creds=source_creds, text=True),
        call(["looker-cli", "api", "role", "set_role_groups", "10", "-"], creds=target_creds, text=True, input="[101]")
    ])


def test_write_role_to_group_role_not_on_target(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    source_roles = [SimpleNamespace(name="Explorer", id=1)]
    target_roles = []
    target_groups = [SimpleNamespace(name="Taco", id=101)]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    deploy_role_to_group.write_role_to_group(source_creds, target_creds)

    mock_run_cli_command.assert_not_called()


def test_write_role_to_group_get_role_groups_fails(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    source_roles = [
        SimpleNamespace(name="Explorer", id=1),
        SimpleNamespace(name="Viewer", id=2)
    ]
    target_roles = [
        SimpleNamespace(name="Explorer", id=10),
        SimpleNamespace(name="Viewer", id=20)
    ]
    target_groups = [SimpleNamespace(name="Taco", id=101)]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    def sub_run_side_effect(cmd, **kwargs):
        creds = kwargs.get("creds", {})
        if "role_groups" in cmd:
            role_id = cmd[-1]
            if role_id == "1":
                raise LookerCLIError("cmd", 1, "", "Fail to get groups")
            else:
                return SimpleNamespace(stdout=json.dumps([{"name": "Taco", "id": 1}]), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = sub_run_side_effect

    deploy_role_to_group.write_role_to_group(source_creds, target_creds)

    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "role", "role_groups", "1"], creds=source_creds, text=True),
        call(["looker-cli", "api", "role", "role_groups", "2"], creds=source_creds, text=True),
        call(["looker-cli", "api", "role", "set_role_groups", "20", "-"], creds=target_creds, text=True, input="[101]")
    ])
