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

import pytest
import json
from types import SimpleNamespace
from looker_deployer.commands import deploy_user_attributes
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli_command")


def test_get_filtered_user_attributes(mock_run_cli_command):
    user_attribute_list = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False},
        {"name": "Sauce", "id": "2", "label": "Cheese", "type": "string", "is_system": False}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(user_attribute_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    user_attributes = deploy_user_attributes.get_filtered_user_attributes(creds)

    assert [i.name for i in user_attributes] == ["Cheese", "Sauce"]
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "userattribute", "all_user_attributes"],
        creds=creds,
        capture_output=True,
        text=True,
        check=True
    )


def test_get_filtered_user_attributes_filter(mock_run_cli_command):
    user_attribute_list = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False},
        {"name": "Sauce", "id": "2", "label": "Cheese", "type": "string", "is_system": False}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(user_attribute_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    user_attributes = deploy_user_attributes.get_filtered_user_attributes(
        creds, "Cheese")

    assert len(user_attributes) == 1
    assert user_attributes[0].name == "Cheese"


def test_write_user_attributes_new(mock_run_cli_command, mocker):
    source_user_attributes = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False}
    ]
    target_user_attributes = []

    user_attribute_group_list = [
        {"id": "1", "group_id": "1", "user_attribute_id": "1", "value": "yummy"}
    ]
    group_1 = {"name": "Taco", "id": "1"}
    groups_list = [group_1]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds", {})
        if "all_user_attribute_group_values" in cmd:
            if creds == source_creds:
                return mocker.MagicMock(stdout=json.dumps(user_attribute_group_list))
            else:
                return mocker.MagicMock(stdout="[]")
        elif "all_user_attributes" in cmd:
            if creds == source_creds:
                return mocker.MagicMock(stdout=json.dumps(source_user_attributes))
            else:
                return mocker.MagicMock(stdout=json.dumps(target_user_attributes))
        elif "all_groups" in cmd:
            return mocker.MagicMock(stdout=json.dumps(groups_list))
        elif "create_user_attribute" in cmd:
            res = source_user_attributes[0].copy()
            res["id"] = "100"
            return mocker.MagicMock(stdout=json.dumps(res))
        elif "set_user_attribute_group_values" in cmd:
            return mocker.MagicMock(stdout="[]")
        raise ValueError(f"Unexpected run command call: {cmd}")

    mock_run_cli_command.side_effect = side_effect

    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    created_payload = {
        "name": "Cheese",
        "label": "Cheese",
        "type": "string",
        "default_value": None,
        "value_is_hidden": False,
        "user_can_view": False,
        "user_can_edit": False
    }

    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "userattribute", "create_user_attribute", "-"],
        creds=target_creds,
        capture_output=True,
        text=True,
        check=True,
        input=json.dumps(created_payload)
    )

    expected_group_values = [
        {"group_id": "1", "value": "yummy"}
    ]
    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "userattribute", "set_user_attribute_group_values", "100", "-"],
        creds=target_creds,
        capture_output=True,
        text=True,
        check=True,
        input=json.dumps(expected_group_values)
    )


def test_write_user_attributes_update_group_value(mock_run_cli_command, mocker):
    source_user_attributes = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False}
    ]
    target_user_attributes = [
        {"name": "Cheese", "id": "100", "label": "Cheese", "type": "string", "is_system": False}
    ]

    source_user_attribute_group_list = [
        {"id": "1", "group_id": "1", "user_attribute_id": "1", "value": "yummy"}
    ]
    target_user_attribute_group_list = [
        {"id": "10", "group_id": "1", "user_attribute_id": "100", "value": "yucky"},
        {"id": "20", "group_id": "2", "user_attribute_id": "100", "value": "stale"}
    ]

    group_1 = {"name": "Taco", "id": "1"}
    group_2 = {"name": "Burrito", "id": "2"}
    groups_list = [group_1, group_2]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds", {})
        if "all_user_attribute_group_values" in cmd:
            if creds == source_creds:
                return mocker.MagicMock(stdout=json.dumps(source_user_attribute_group_list))
            else:
                return mocker.MagicMock(stdout=json.dumps(target_user_attribute_group_list))
        elif "all_user_attributes" in cmd:
            if creds == source_creds:
                return mocker.MagicMock(stdout=json.dumps(source_user_attributes))
            else:
                return mocker.MagicMock(stdout=json.dumps(target_user_attributes))
        elif "all_groups" in cmd:
            return mocker.MagicMock(stdout=json.dumps(groups_list))
        elif "update_user_attribute" in cmd:
            res = target_user_attributes[0].copy()
            return mocker.MagicMock(stdout=json.dumps(res))
        elif "set_user_attribute_group_values" in cmd:
            return mocker.MagicMock(stdout="[]")
        raise ValueError(f"Unexpected run command call: {cmd}")

    mock_run_cli_command.side_effect = side_effect

    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    updated_payload = {
        "name": "Cheese",
        "label": "Cheese",
        "type": "string",
        "default_value": None,
        "value_is_hidden": False,
        "user_can_view": False,
        "user_can_edit": False
    }
    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "userattribute", "update_user_attribute", "100", "-"],
        creds=target_creds,
        capture_output=True,
        text=True,
        check=True,
        input=json.dumps(updated_payload)
    )

    # We expect setting group values for group 1 (Taco) to "yummy".
    # Group 2 (Burrito) is not in source_user_attribute_group_list, so it should be omitted (deleted by omission).
    expected_group_values = [
        {"group_id": "1", "value": "yummy"}
    ]
    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "userattribute", "set_user_attribute_group_values", "100", "-"],
        creds=target_creds,
        capture_output=True,
        text=True,
        check=True,
        input=json.dumps(expected_group_values)
    )


def test_run_cli_failure(mock_run_cli_command):
    mock_run_cli_command.side_effect = LookerCLIError(
        command="looker-cli api userattribute all_user_attributes",
        exit_code=1,
        stdout="stdout error",
        stderr="stderr error"
    )

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_user_attributes.run_cli(["api", "userattribute", "all_user_attributes"], creds)


def test_get_filtered_user_attributes_excludes_system(mock_run_cli_command):
    user_attribute_list = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False},
        {"name": "SystemAttr", "id": "2", "label": "System", "type": "string", "is_system": True}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(user_attribute_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    user_attributes = deploy_user_attributes.get_filtered_user_attributes(creds)

    assert [i.name for i in user_attributes] == ["Cheese"]


def test_write_user_attributes_delete_extra_target(mock_run_cli_command, mocker):
    source_user_attributes = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False}
    ]
    target_user_attributes = [
        {"name": "Cheese", "id": "100", "label": "Cheese", "type": "string", "is_system": False},
        {"name": "Sauce", "id": "200", "label": "Sauce", "type": "string", "is_system": False}
    ]

    groups_list = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds", {})
        if "all_user_attribute_group_values" in cmd:
            return mocker.MagicMock(stdout="[]")
        elif "all_user_attributes" in cmd:
            if creds == source_creds:
                return mocker.MagicMock(stdout=json.dumps(source_user_attributes))
            else:
                return mocker.MagicMock(stdout=json.dumps(target_user_attributes))
        elif "all_groups" in cmd:
            return mocker.MagicMock(stdout=json.dumps(groups_list))
        elif "update_user_attribute" in cmd:
            res = target_user_attributes[0].copy()
            return mocker.MagicMock(stdout=json.dumps(res))
        elif "set_user_attribute_group_values" in cmd:
            return mocker.MagicMock(stdout="[]")
        elif "delete_user_attribute" in cmd:
            return mocker.MagicMock(stdout="{}")
        raise ValueError(f"Unexpected run command call: {cmd}")

    mock_run_cli_command.side_effect = side_effect

    deploy_user_attributes.write_user_attributes(source_creds, target_creds, allow_delete=True)

    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "userattribute", "delete_user_attribute", "200"],
        creds=target_creds,
        capture_output=True,
        text=True,
        check=True
    )


def test_main(mocker):
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_user_attributes.build_creds")
    mock_write = mocker.patch("looker_deployer.commands.deploy_user_attributes.write_user_attributes")

    mock_build_creds.side_effect = lambda ini, name: {"creds_name": name}

    args = SimpleNamespace(
        debug=True,
        ini="looker.ini",
        source="dev",
        target=["prod", "staging"],
        pattern="test_*",
        delete=True
    )

    deploy_user_attributes.main(args)

    assert mock_build_creds.call_count == 3
    mock_build_creds.assert_has_calls([
        mocker.call("looker.ini", "dev"),
        mocker.call("looker.ini", "prod"),
        mocker.call("looker.ini", "staging")
    ])

    mock_write.assert_has_calls([
        mocker.call({"creds_name": "dev"}, {"creds_name": "prod"}, "test_*", True),
        mocker.call({"creds_name": "dev"}, {"creds_name": "staging"}, "test_*", True)
    ])


def test_cli_parsing(mocker):
    from looker_deployer import cli

    mock_main = mocker.patch("looker_deployer.commands.deploy_user_attributes.main")

    mocker.patch("sys.argv", [
        "looker-deployer", "user_attributes",
        "--source", "dev",
        "--target", "prod", "staging",
        "--pattern", "test_*",
        "--delete",
        "--debug"
    ])

    cli.main()

    mock_main.assert_called_once()
    parsed_args = mock_main.call_args[0][0]
    assert parsed_args.source == "dev"
    assert parsed_args.target == ["prod", "staging"]
    assert parsed_args.pattern == "test_*"
    assert parsed_args.delete is True
    assert parsed_args.debug is True


def test_write_user_attributes_delete_behavior(mock_run_cli_command, mocker):
    source_user_attributes = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False}
    ]
    target_user_attributes = [
        {"name": "Cheese", "id": "100", "label": "Cheese", "type": "string", "is_system": False},
        {"name": "Sauce", "id": "200", "label": "Sauce", "type": "string", "is_system": False}
    ]
    groups_list = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def side_effect(cmd, **kwargs):
        creds = kwargs.get("creds", {})
        if "all_user_attribute_group_values" in cmd:
            return mocker.MagicMock(stdout="[]")
        elif "all_user_attributes" in cmd:
            if creds == source_creds:
                return mocker.MagicMock(stdout=json.dumps(source_user_attributes))
            else:
                return mocker.MagicMock(stdout=json.dumps(target_user_attributes))
        elif "all_groups" in cmd:
            return mocker.MagicMock(stdout=json.dumps(groups_list))
        elif "update_user_attribute" in cmd:
            res = target_user_attributes[0].copy()
            return mocker.MagicMock(stdout=json.dumps(res))
        elif "set_user_attribute_group_values" in cmd:
            return mocker.MagicMock(stdout="[]")
        elif "delete_user_attribute" in cmd:
            return mocker.MagicMock(stdout="{}")
        raise ValueError(f"Unexpected run command call: {cmd}")

    mock_run_cli_command.side_effect = side_effect

    # 1. allow_delete = True
    deploy_user_attributes.write_user_attributes(source_creds, target_creds, allow_delete=True)
    mock_run_cli_command.assert_any_call(
        ["looker-cli", "api", "userattribute", "delete_user_attribute", "200"],
        creds=target_creds,
        capture_output=True,
        text=True,
        check=True
    )

    mock_run_cli_command.reset_mock()

    # 2. allow_delete = False
    deploy_user_attributes.write_user_attributes(source_creds, target_creds, allow_delete=False)
    for call in mock_run_cli_command.call_args_list:
        cmd = call[0][0]
        assert not ("delete_user_attribute" in cmd), f"Delete command was called: {cmd}"
