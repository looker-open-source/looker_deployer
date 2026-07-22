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


def test_source_fetch_failure_deletes_all_target_groups(mock_run_cli_command):
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds")
        if creds == source_creds:
            raise LookerCLIError("cmd", 1, "", "API Error")
        elif creds == target_creds:
            target_groups = [
                {"name": "Taco", "id": 1},
                {"name": "Burrito", "id": 2}
            ]
            return SimpleNamespace(stdout=json.dumps(target_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    with pytest.raises(LookerCLIError):
        deploy_groups.send_groups(source_creds, target_creds, allow_delete=True)


def test_duplicate_source_groups_creates_twice(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco"), SimpleNamespace(name="Taco")]

    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)

    assert mock_run_cli_command.call_count == 1
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"name": "Taco"})
    )


def test_duplicate_source_groups_case_mismatch(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco"), SimpleNamespace(name="taco")]

    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)

    assert mock_run_cli_command.call_count == 1
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "group", "create_group", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"name": "Taco"})
    )


def test_target_group_missing_id_raises_attribute_error(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [SimpleNamespace(name="Taco")]  # missing id

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


def test_source_group_missing_name_raises_attribute_error(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(id=1)]  # missing name

    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)
    mock_run_cli_command.assert_not_called()


def test_externally_managed_case_insensitive_collision(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [SimpleNamespace(name="taco", id=1, externally_managed=True)]

    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds)

    subprocess_calls = [c for c in mock_run_cli_command.call_args_list if "group" in c[0][0]]
    assert len(subprocess_calls) == 0


def test_delete_target_group_missing_id(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [
        SimpleNamespace(name="Taco", id=1),
        SimpleNamespace(name="Burrito")  # missing id, should be deleted but skipped
    ]

    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    subprocess_calls = [c for c in mock_run_cli_command.call_args_list if "group" in c[0][0]]
    assert len(subprocess_calls) == 0


def test_source_malformed_json_raises_runtime_error(mock_run_cli_command):
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds")
        if creds == source_creds:
            return SimpleNamespace(stdout="Not a valid JSON", stderr="")
        elif creds == target_creds:
            target_groups = [
                {"name": "Taco", "id": 1},
                {"name": "Burrito", "id": 2}
            ]
            return SimpleNamespace(stdout=json.dumps(target_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    with pytest.raises(RuntimeError) as exc_info:
        deploy_groups.send_groups(source_creds, target_creds, allow_delete=True)
    assert "Failed to parse JSON from looker-cli" in str(exc_info.value)

    for call_args in mock_run_cli_command.call_args_list:
        assert "delete" not in call_args[0][0]


def test_target_group_missing_id_matching_behavior(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [
        SimpleNamespace(name="Taco"),  # No id
        SimpleNamespace(name="Taco", id=2)
    ]

    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    subprocess_calls = [c for c in mock_run_cli_command.call_args_list if "group" in c[0][0]]
    assert len(subprocess_calls) == 0


def test_target_group_name_is_none_handled_safely(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [
        SimpleNamespace(name=None, id=1)
    ]

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


def test_target_group_empty_string_id_matching_behavior(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [
        SimpleNamespace(name="Taco", id=""),  # empty string id
        SimpleNamespace(name="Taco", id=2)
    ]

    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    for call_args in mock_run_cli_command.call_args_list:
        assert "delete" not in call_args[0][0]


def test_externally_managed_and_writeable_collision_externally_managed_first(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [
        SimpleNamespace(name="Taco", id=1, externally_managed=True),
        SimpleNamespace(name="Taco", id=2)
    ]

    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    for call_args in mock_run_cli_command.call_args_list:
        assert "delete" not in call_args[0][0]


def test_externally_managed_and_writeable_collision_writeable_first(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name="Taco")]
    target_groups = [
        SimpleNamespace(name="Taco", id=2),
        SimpleNamespace(name="Taco", id=1, externally_managed=True)
    ]

    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    for call_args in mock_run_cli_command.call_args_list:
        assert "delete" not in call_args[0][0]


def test_non_string_group_names_handled_safely(mock_run_cli_command, mocker):
    group_list = [SimpleNamespace(name=123)]
    target_groups = [
        SimpleNamespace(name="123", id=2)
    ]

    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups", return_value=target_groups)

    target_creds = {"base_url": "target"}
    deploy_groups.write_groups(group_list, target_creds, allow_delete=True)

    for call_args in mock_run_cli_command.call_args_list:
        assert "update" not in call_args[0][0]
        assert "create" not in call_args[0][0]
        assert "delete" not in call_args[0][0]


def test_source_json_list_of_primitives_raises_runtime_error(mock_run_cli_command):
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds")
        if creds == source_creds:
            return SimpleNamespace(stdout='["group1", "group2"]', stderr="")
        elif creds == target_creds:
            target_groups = [
                {"name": "Taco", "id": 1}
            ]
            return SimpleNamespace(stdout=json.dumps(target_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    with pytest.raises(RuntimeError) as exc_info:
        deploy_groups.send_groups(source_creds, target_creds, allow_delete=True)
    assert "Unexpected JSON structure" in str(exc_info.value)

    for call_args in mock_run_cli_command.call_args_list:
        cmd = call_args[0][0]
        assert "create" not in cmd
        assert "update" not in cmd
        assert "delete" not in cmd


def test_target_json_list_of_primitives_raises_runtime_error(mock_run_cli_command):
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds")
        if creds == source_creds:
            source_groups = [
                {"name": "Taco"}
            ]
            return SimpleNamespace(stdout=json.dumps(source_groups), stderr="")
        elif creds == target_creds:
            return SimpleNamespace(stdout='["group1", "group2"]', stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    with pytest.raises(RuntimeError) as exc_info:
        deploy_groups.send_groups(source_creds, target_creds, allow_delete=True)
    assert "Unexpected JSON structure" in str(exc_info.value)

    for call_args in mock_run_cli_command.call_args_list:
        cmd = call_args[0][0]
        assert "create" not in cmd
        assert "update" not in cmd
        assert "delete" not in cmd


def test_mixed_json_elements_raises_runtime_error(mock_run_cli_command):
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds")
        if creds == source_creds:
            return SimpleNamespace(stdout='[{"name": "Taco"}, "Burrito"]', stderr="")
        elif creds == target_creds:
            target_groups = [
                {"name": "Taco", "id": 1}
            ]
            return SimpleNamespace(stdout=json.dumps(target_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    with pytest.raises(RuntimeError) as exc_info:
        deploy_groups.send_groups(source_creds, target_creds, allow_delete=True)
    assert "Unexpected JSON structure" in str(exc_info.value)

    for call_args in mock_run_cli_command.call_args_list:
        cmd = call_args[0][0]
        assert "create" not in cmd
        assert "update" not in cmd
        assert "delete" not in cmd
