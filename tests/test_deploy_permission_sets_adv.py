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
from looker_deployer.commands import deploy_permission_sets


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_permission_sets.run_cli_command")


def test_adv_get_filtered_permission_sets_invalid_regex(mock_run_cli_command):
    permission_set_list = [{"name": "Taco", "built_in": False}]
    mock_run_cli_command.return_value = SimpleNamespace(stdout=json.dumps(permission_set_list), stderr="")

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_permission_sets.get_filtered_permission_sets(creds, pattern="[")
    assert "Invalid regular expression pattern" in str(exc_info.value)


def test_adv_write_permission_sets_target_missing_name(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name="Taco", permissions=["see_look"])]
    target_permission_sets = [SimpleNamespace(id=1)]  # missing name attribute

    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=target_permission_sets)
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")

    target_creds = {"base_url": "target"}
    deploy_permission_sets.write_permission_sets(permission_set_list, target_creds)
    mock_run_cli_command.assert_called_once()
    assert "create_permission_set" in mock_run_cli_command.call_args[0][0]


def test_adv_write_permission_sets_source_missing_name(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(permissions=["see_look"])]  # missing name attribute
    target_permission_sets = [SimpleNamespace(name="Taco", id=1)]

    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=target_permission_sets)

    target_creds = {"base_url": "target"}
    deploy_permission_sets.write_permission_sets(permission_set_list, target_creds)
    mock_run_cli_command.assert_not_called()


def test_adv_write_permission_sets_no_target_delete(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name="Taco", permissions=["see_look"])]
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[])
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")

    target_creds = {"base_url": "target"}
    deploy_permission_sets.write_permission_sets(permission_set_list, target_creds, allow_delete=True)

    assert mock_run_cli_command.call_count == 1
    assert "create_permission_set" in mock_run_cli_command.call_args[0][0]


def test_adv_write_permission_sets_non_serializable_name(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name=SimpleNamespace(x=1), permissions=["see_look"])]
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_permission_sets.write_permission_sets(permission_set_list, target_creds)
    mock_run_cli_command.assert_not_called()


def test_adv_write_permission_sets_non_serializable_permissions(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name="Taco", permissions=SimpleNamespace(x=1))]
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_permission_sets.write_permission_sets(permission_set_list, target_creds)
    mock_run_cli_command.assert_not_called()


def test_adv_write_permission_sets_duplicate_source_names(mock_run_cli_command, mocker):
    permission_set_list = [
        SimpleNamespace(name="Taco", permissions=["see_look"]),
        SimpleNamespace(name="Taco", permissions=["see_user"])
    ]
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[])

    target_creds = {"base_url": "target"}
    deploy_permission_sets.write_permission_sets(permission_set_list, target_creds)

    assert mock_run_cli_command.call_count == 1
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "create_permission_set", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"name": "Taco", "permissions": ["see_user"]})
    )


def test_adv_write_permission_sets_multiple_duplicate_targets_delete(mock_run_cli_command, mocker):
    source_permission_sets = [
        SimpleNamespace(name="Taco", permissions=["see_looks"])
    ]
    target_permission_sets = [
        SimpleNamespace(name="Taco", id=1),
        SimpleNamespace(name="Taco", id=2),
        SimpleNamespace(name="Taco", id=3)
    ]

    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=target_permission_sets)
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")

    target_creds = {"base_url": "target"}
    deploy_permission_sets.write_permission_sets(source_permission_sets, target_creds, allow_delete=True)

    call_args_list = [c[0][0] for c in mock_run_cli_command.call_args_list]
    delete_calls = [args for args in call_args_list if "delete_permission_set" in args]

    assert len(delete_calls) == 2
    deleted_ids = {args[-1] for args in delete_calls}
    assert deleted_ids == {"2", "3"}
