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
import pytest

from looker_deployer.commands import deploy_groups
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_groups.run_cli_command")


def test_target_malformed_json_raises_runtime_error(mock_run_cli_command):
    group_list = [SimpleNamespace(name="Taco")]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="Not a valid JSON", stderr="")

    target_creds = {"base_url": "target"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_groups.write_groups(group_list, target_creds, allow_delete=True)
    assert "Failed to parse JSON from looker-cli" in str(exc_info.value)

    for call_args in mock_run_cli_command.call_args_list:
        cmd = call_args[0][0]
        assert "create" not in cmd
        assert "update" not in cmd
        assert "delete" not in cmd


def test_target_fetch_failure_raises_runtime_error(mock_run_cli_command):
    group_list = [SimpleNamespace(name="Taco")]
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "API Error")

    target_creds = {"base_url": "target"}
    with pytest.raises(LookerCLIError):
        deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    for call_args in mock_run_cli_command.call_args_list:
        cmd = call_args[0][0]
        assert "create" not in cmd
        assert "update" not in cmd
        assert "delete" not in cmd


def test_source_group_non_string_name(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name=123)]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"name": "123"})
    )


def test_target_group_non_string_name(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [SimpleNamespace(name=123, id=1)]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"name": "Taco"})
    )


def test_empty_target_list_does_not_delete(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"name": "Taco"})
    )


def test_special_characters_in_names(mock_run_cli_command, mocker):
    special_name = "Taco's \"Special\" Group \\ 🌮"
    group_list = [SimpleNamespace(name=special_name)]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"name": special_name})
    )


def test_pattern_case_sensitivity_mismatch(mock_run_cli_command, mocker):
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def get_filtered_groups_side_effect(creds, pattern=None, exclude_managed=True):
        if creds == source_creds:
            return [SimpleNamespace(name="Taco")]
        elif creds == target_creds:
            return []
        return []

    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", side_effect=get_filtered_groups_side_effect)
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")

    deploy_groups.send_groups(source_creds, target_creds, pattern="Taco")

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"name": "Taco"})
    )


def test_get_filtered_groups_pattern_non_string_name(mock_run_cli_command):
    group_list = [
        {"name": 123},
        {"name": "Burrito"}
    ]
    mock_run_cli_command.return_value = SimpleNamespace(stdout=json.dumps(group_list), stderr="")

    creds = {"base_url": "test"}
    groups = deploy_groups.get_filtered_groups(creds, "123")
    assert [str(getattr(g, "name")) for g in groups] == ["123"]


def test_source_json_non_list_or_object_raises_runtime_error_null(mock_run_cli_command):
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds")
        if creds == source_creds:
            return SimpleNamespace(stdout="null", stderr="")
        elif creds == target_creds:
            target_groups = [
                {"name": "Taco", "id": 1},
                {"name": "Burrito", "id": 2}
            ]
            return SimpleNamespace(stdout=json.dumps(target_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    with pytest.raises(RuntimeError):
        deploy_groups.send_groups(source_creds, target_creds, allow_delete=True)


def test_source_json_non_list_or_object_raises_runtime_error_string(mock_run_cli_command):
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds")
        if creds == source_creds:
            return SimpleNamespace(stdout='"hello"', stderr="")
        elif creds == target_creds:
            target_groups = [
                {"name": "Taco", "id": 1}
            ]
            return SimpleNamespace(stdout=json.dumps(target_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    with pytest.raises(RuntimeError):
        deploy_groups.send_groups(source_creds, target_creds, allow_delete=True)


def test_target_group_name_boolean_false_matching_behavior(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="False")]
    target_groups = [
        SimpleNamespace(name=False, id=1)
    ]

    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    subprocess_calls = [c for c in mock_run_cli_command.call_args_list if "group" in c[0][0]]
    assert len(subprocess_calls) == 0


def test_target_group_name_zero_or_false_matching(mock_run_cli_command, mocker):
    group_list = [
        SimpleNamespace(name=0),
        SimpleNamespace(name=False)
    ]
    target_groups = [
        SimpleNamespace(name=0, id=1),
        SimpleNamespace(name=False, id=2)
    ]
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    subprocess_calls = [c for c in mock_run_cli_command.call_args_list if "group" in c[0][0]]
    assert len(subprocess_calls) == 0


def test_target_group_id_zero_update(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [SimpleNamespace(name="taco", id=0)]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)

    mock_run_cli_command.assert_called_once()
    assert "update_group" in mock_run_cli_command.call_args[0][0]
    assert "0" in mock_run_cli_command.call_args[0][0]


def test_target_group_id_zero_delete(mock_run_cli_command, mocker):
    group_list = []
    target_groups = [SimpleNamespace(name="taco", id=0)]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    mock_run_cli_command.assert_called_once()
    assert "delete_group" in mock_run_cli_command.call_args[0][0]
    assert "0" in mock_run_cli_command.call_args[0][0]


def test_source_bool_false_target_string_false_match(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name=False)]
    target_groups = [SimpleNamespace(name="False", id=1)]
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    subprocess_calls = [c for c in mock_run_cli_command.call_args_list if "group" in c[0][0]]
    assert len(subprocess_calls) == 0


def test_source_int_zero_target_string_zero_match(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name=0)]
    target_groups = [SimpleNamespace(name="0", id=1)]
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    subprocess_calls = [c for c in mock_run_cli_command.call_args_list if "group" in c[0][0]]
    assert len(subprocess_calls) == 0


def test_target_group_id_string_zero_update(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [SimpleNamespace(name="taco", id="0")]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)

    mock_run_cli_command.assert_called_once()
    assert "update_group" in mock_run_cli_command.call_args[0][0]
    assert "0" in mock_run_cli_command.call_args[0][0]


def test_target_group_id_string_zero_delete(mock_run_cli_command, mocker):
    group_list = []
    target_groups = [SimpleNamespace(name="taco", id="0")]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    mock_run_cli_command.assert_called_once()
    assert "delete_group" in mock_run_cli_command.call_args[0][0]
    assert "0" in mock_run_cli_command.call_args[0][0]


def test_create_source_group_name_zero(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name=0)]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"name": "0"})
    )


def test_create_source_group_name_false(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name=False)]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"name": "False"})
    )
