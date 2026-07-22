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
from looker_deployer.commands import deploy_groups
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_groups.run_cli_command")


def test_get_filtered_groups(mock_run_cli_command):
    group_list = [
        {"name": "Taco"},
        {"name": "Burrito"}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(group_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    groups = deploy_groups.get_filtered_groups(creds)
    assert [g.name for g in groups] == ["Taco", "Burrito"]
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "all_groups"],
        text=True,
        creds=creds
    )


def test_get_filtered_groups_filter(mock_run_cli_command):
    group_list = [
        {"name": "Taco"},
        {"name": "Burrito"}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(group_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    groups = deploy_groups.get_filtered_groups(creds, "Burrito")
    assert [g.name for g in groups] == ["Burrito"]
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "all_groups"],
        text=True,
        creds=creds
    )


def test_get_filtered_groups_single_object(mock_run_cli_command):
    group = {"name": "Taco"}
    mock_res = SimpleNamespace(stdout=json.dumps(group), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    groups = deploy_groups.get_filtered_groups(creds)
    assert [g.name for g in groups] == ["Taco"]
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "all_groups"],
        text=True,
        creds=creds
    )


def test_get_filtered_groups_empty(mock_run_cli_command):
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    groups = deploy_groups.get_filtered_groups(creds)
    assert groups == []
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "all_groups"],
        text=True,
        creds=creds
    )


def test_write_groups_new(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        input=json.dumps({"name": "Taco"}),
        text=True,
        creds=creds
    )


def test_write_groups_existing(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[SimpleNamespace(name="taco", id=1)])

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "update_group", "1", "-"],
        input=json.dumps({"name": "Taco"}),
        text=True,
        creds=creds
    )


def test_write_groups_multiple(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco"), SimpleNamespace(name="Burrito")]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds)
    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "group", "create_group", "-"], input=json.dumps({"name": "Taco"}), text=True, creds=creds),
        call(["looker-cli", "api", "group", "create_group", "-"], input=json.dumps({"name": "Burrito"}), text=True, creds=creds)
    ])


def test_write_groups_delete(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [SimpleNamespace(name="Taco", id=1), SimpleNamespace(name="Burrito", id=2)]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds, allow_delete=True)
    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "group", "delete_group", "2"], text=True, creds=creds)
    ])


def test_write_groups_redundant_update(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[SimpleNamespace(name="Taco", id=1)])

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds)
    mock_run_cli_command.assert_not_called()


def test_write_groups_externally_managed(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[SimpleNamespace(name="Taco", id=1, externally_managed=True)])

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds)
    mock_run_cli_command.assert_not_called()


def test_write_groups_case_insensitive_match(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[SimpleNamespace(name="TACO", id=1)])

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "update_group", "1", "-"],
        input=json.dumps({"name": "Taco"}),
        text=True,
        creds=creds
    )


def test_write_groups_duplicate_deletion(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [
        SimpleNamespace(name="Taco", id=1),
        SimpleNamespace(name="Taco", id=2)
    ]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds, allow_delete=True)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "delete_group", "2"],
        text=True,
        creds=creds
    )


def test_write_groups_api_list_failure(mock_run_cli_command):
    group_list = [SimpleNamespace(name="Taco")]
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "API Error")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_groups.write_groups(group_list, creds)


def test_write_groups_duplicate_source_groups(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco"), SimpleNamespace(name="Taco")]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds)

    assert mock_run_cli_command.call_count == 1
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        input=json.dumps({"name": "Taco"}),
        text=True,
        creds=creds
    )


def test_write_groups_missing_source_name(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(id=123)]
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds)
    mock_run_cli_command.assert_not_called()


def test_write_groups_missing_target_id(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [SimpleNamespace(name="Taco")]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        input=json.dumps({"name": "Taco"}),
        text=True,
        creds=creds
    )


def test_write_groups_case_mismatch_collisions(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [
        SimpleNamespace(name="taco", id=1),
        SimpleNamespace(name="TACO", id=2)
    ]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    creds = {"base_url": "test"}
    deploy_groups.write_groups(group_list, creds, allow_delete=True)

    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "group", "update_group", "1", "-"], input=json.dumps({"name": "Taco"}), text=True, creds=creds),
        call(["looker-cli", "api", "group", "delete_group", "2"], text=True, creds=creds)
    ])


def test_get_filtered_groups_command_not_found(mock_run_cli_command):
    mock_run_cli_command.side_effect = FileNotFoundError("[Errno 2] No such file or directory: 'looker-cli'")

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_groups.get_filtered_groups(creds)
    assert "looker-cli command not found" in str(exc_info.value)


def test_get_filtered_groups_malformed_json(mock_run_cli_command):
    mock_res = SimpleNamespace(stdout="invalid json", stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_groups.get_filtered_groups(creds)
    assert "Failed to parse JSON from looker-cli" in str(exc_info.value)
