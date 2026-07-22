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
from looker_deployer.commands import deploy_group_in_group
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_group_in_group.run_cli_command")


# 1. Edge case: Empty group list (stdout empty)
def test_get_filtered_groups_empty_stdout(mock_run_cli_command):
    mock_run_cli_command.return_value = SimpleNamespace(
        stdout="",
        stderr=""
    )

    creds = {"base_url": "test"}
    groups = deploy_group_in_group.get_filtered_groups(creds)
    assert groups == []


# 2. Edge case: Invalid JSON in group list stdout
def test_get_filtered_groups_invalid_json(mock_run_cli_command):
    mock_run_cli_command.return_value = SimpleNamespace(
        stdout="not a valid json",
        stderr=""
    )

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_group_in_group.get_filtered_groups(creds)

    assert "Failed to parse JSON from looker-cli" in str(exc_info.value)


# 3. Robustness: Subprocess failing with non-zero exit code for group list
def test_get_filtered_groups_non_zero_exit(mock_run_cli_command):
    mock_run_cli_command.side_effect = LookerCLIError(
        command="looker-cli group list",
        exit_code=1,
        stdout="",
        stderr="Some looker-cli error"
    )

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_group_in_group.get_filtered_groups(creds)


# 4. Robustness: looker-cli command not found
def test_get_filtered_groups_command_not_found(mock_run_cli_command):
    mock_run_cli_command.side_effect = FileNotFoundError("No such file or directory")

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_group_in_group.get_filtered_groups(creds)

    assert "looker-cli command not found" in str(exc_info.value)


# 5. Edge case: Missing name attribute on group
def test_write_groups_in_group_missing_name_attribute(mock_run_cli_command, mocker):
    source_groups = [
        {"id": 1, "externally_managed": False}  # missing name
    ]
    target_groups = [
        {"name": "Taco", "id": 1, "externally_managed": False}
    ]

    def side_effect(args, **kwargs):
        creds = kwargs.get("creds", {})
        if args == ["looker-cli", "api", "group", "all_groups"]:
            if creds == {"base_url": "source"}:
                return SimpleNamespace(stdout=json.dumps(source_groups), stderr="")
            else:
                return SimpleNamespace(stdout=json.dumps(target_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    # Expect AttributeError because match_by_key tries to do getattr(group, "name") which doesn't exist
    with pytest.raises(AttributeError):
        deploy_group_in_group.write_groups_in_group(source_creds, target_creds)


# 6. Edge case: Missing id attribute on group
def test_write_groups_in_group_missing_id_attribute(mock_run_cli_command, mocker):
    source_groups = [
        {"name": "Taco", "externally_managed": False}
    ]
    target_groups = [
        {"name": "Taco", "id": 2, "externally_managed": False}
    ]

    def side_effect(args, **kwargs):
        creds = kwargs.get("creds", {})
        if args == ["looker-cli", "api", "group", "all_groups"]:
            if creds == {"base_url": "source"}:
                return SimpleNamespace(stdout=json.dumps(source_groups), stderr="")
            else:
                return SimpleNamespace(stdout=json.dumps(target_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    # Expect AttributeError because it does str(group.id)
    with pytest.raises(AttributeError):
        deploy_group_in_group.write_groups_in_group(source_creds, target_creds)


# 7. Edge case: Subgroup list returns invalid JSON
def test_write_groups_in_group_subgroup_invalid_json(mock_run_cli_command, mocker):
    group_list = [
        {"name": "Taco", "id": 1, "externally_managed": False}
    ]

    def side_effect(args, **kwargs):
        if args == ["looker-cli", "api", "group", "all_groups"]:
            return SimpleNamespace(stdout=json.dumps(group_list), stderr="")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "1"]:
            return SimpleNamespace(stdout="invalid json here", stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    with pytest.raises(json.JSONDecodeError):
        deploy_group_in_group.write_groups_in_group(source_creds, target_creds)


# 8. Robustness: Subgroup list command fails
def test_write_groups_in_group_subgroup_command_fail(mock_run_cli_command, mocker):
    group_list = [
        {"name": "Taco", "id": 1, "externally_managed": False}
    ]

    def side_effect(args, **kwargs):
        if args == ["looker-cli", "api", "group", "all_groups"]:
            return SimpleNamespace(stdout=json.dumps(group_list), stderr="")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "1"]:
            raise LookerCLIError("looker-cli api group all_group_groups 1", 1, "", "Error listing subgroups")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    with pytest.raises(LookerCLIError):
        deploy_group_in_group.write_groups_in_group(source_creds, target_creds)


# 9. Robustness: add/remove subgroup commands fail
def test_write_groups_in_group_add_remove_command_fail(mock_run_cli_command, mocker):
    group_list = [
        {"name": "Taco", "id": 1, "externally_managed": False},
        {"name": "Taco Supreme", "id": 2, "externally_managed": False}
    ]

    def side_effect(args, **kwargs):
        creds = kwargs.get("creds", {})
        if args == ["looker-cli", "api", "group", "all_groups"]:
            return SimpleNamespace(stdout=json.dumps(group_list), stderr="")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "1"]:
            return SimpleNamespace(stdout="[]", stderr="")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "2"]:
            if creds == {"base_url": "source"}:
                return SimpleNamespace(stdout=json.dumps([{"name": "Taco", "id": 1, "externally_managed": False}]), stderr="")
            else:
                return SimpleNamespace(stdout="[]", stderr="")
        elif args[:4] == ["looker-cli", "api", "group", "add_group_group"]:
            raise LookerCLIError("add", 1, "", "Adding failed")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    with pytest.raises(LookerCLIError):
        deploy_group_in_group.write_groups_in_group(source_creds, target_creds)


# 10. Command validation: Validate that precise shell argument lists are checked
def test_write_groups_in_group_command_arguments_validation(mock_run_cli_command, mocker):
    group_list = [
        {"name": "Taco", "id": 10, "externally_managed": False},
        {"name": "Taco Supreme", "id": 20, "externally_managed": False}
    ]

    def side_effect(args, **kwargs):
        creds = kwargs.get("creds", {})
        if args == ["looker-cli", "api", "group", "all_groups"]:
            return SimpleNamespace(stdout=json.dumps(group_list), stderr="")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "10"]:
            return SimpleNamespace(stdout="[]", stderr="")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "20"]:
            if creds == {"base_url": "source"}:
                return SimpleNamespace(stdout=json.dumps([{"name": "Taco", "id": 10, "externally_managed": False}]), stderr="")
            else:
                return SimpleNamespace(stdout="[]", stderr="")
        elif args[:5] == ["looker-cli", "api", "group", "add_group_group"]:
            return SimpleNamespace(stdout="", stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_group_in_group.write_groups_in_group(source_creds, target_creds)

    # Check that looker-cli group subgroup list calls are made with expected string args
    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "group", "all_group_groups", "10"],
        text=True,
        creds=source_creds
    )
    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "group", "all_group_groups", "10"],
        text=True,
        creds=target_creds
    )
    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "group", "all_group_groups", "20"],
        text=True,
        creds=source_creds
    )
    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "group", "all_group_groups", "20"],
        text=True,
        creds=target_creds
    )

    # Check that the add command was called exactly with:
    # ["looker-cli", "api", "group", "add_group_group", "20", "-"] with input
    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "group", "add_group_group", "20", "-"],
        text=True,
        creds=target_creds,
        input=json.dumps({"group_id": "10"})
    )


def test_write_groups_in_group_add_file_not_found(mock_run_cli_command):
    """Test write_groups_in_group raises FileNotFoundError directly if add command is missing (inconsistent with list commands)."""
    source_groups = [
        {"name": "Taco", "id": 10, "externally_managed": False},
        {"name": "Burrito", "id": 20, "externally_managed": False}
    ]
    target_groups = [
        {"name": "Taco", "id": 10, "externally_managed": False},
        {"name": "Burrito", "id": 20, "externally_managed": False}
    ]

    def side_effect(args, **kwargs):
        creds = kwargs.get("creds", {})
        if args == ["looker-cli", "api", "group", "all_groups"]:
            if creds == {"base_url": "source"}:
                return SimpleNamespace(stdout=json.dumps(source_groups), stderr="")
            else:
                return SimpleNamespace(stdout=json.dumps(target_groups), stderr="")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "10"]:
            return SimpleNamespace(stdout="[]", stderr="")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "20"]:
            if creds == {"base_url": "source"}:
                return SimpleNamespace(stdout=json.dumps([{"name": "Taco", "id": 10, "externally_managed": False}]), stderr="")
            else:
                return SimpleNamespace(stdout="[]", stderr="")
        elif args[:4] == ["looker-cli", "api", "group", "add_group_group"]:
            raise FileNotFoundError("looker-cli command not found")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    # FileNotFoundError is propagated directly
    with pytest.raises(FileNotFoundError):
        deploy_group_in_group.write_groups_in_group(source_creds, target_creds)


def test_write_groups_in_group_remove_file_not_found(mock_run_cli_command):
    """Test write_groups_in_group raises FileNotFoundError directly if remove command is missing."""
    source_groups = [
        {"name": "Taco", "id": 10, "externally_managed": False},
        {"name": "Burrito", "id": 20, "externally_managed": False}
    ]
    target_groups = [
        {"name": "Taco", "id": 10, "externally_managed": False},
        {"name": "Burrito", "id": 20, "externally_managed": False}
    ]

    def side_effect(args, **kwargs):
        creds = kwargs.get("creds", {})
        if args == ["looker-cli", "api", "group", "all_groups"]:
            if creds == {"base_url": "source"}:
                return SimpleNamespace(stdout=json.dumps(source_groups), stderr="")
            else:
                return SimpleNamespace(stdout=json.dumps(target_groups), stderr="")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "10"]:
            return SimpleNamespace(stdout="[]", stderr="")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "20"]:
            if creds == {"base_url": "source"}:
                return SimpleNamespace(stdout="[]", stderr="")
            else:
                return SimpleNamespace(stdout=json.dumps([{"name": "Taco", "id": 10, "externally_managed": False}]), stderr="")
        elif args[:4] == ["looker-cli", "api", "group", "delete_group_from_group"]:
            raise FileNotFoundError("looker-cli command not found")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = side_effect

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    # FileNotFoundError is propagated directly
    with pytest.raises(FileNotFoundError):
        deploy_group_in_group.write_groups_in_group(source_creds, target_creds)
