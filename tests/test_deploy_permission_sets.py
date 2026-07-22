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
from looker_deployer.commands import deploy_permission_sets
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_permission_sets.run_cli_command")


def test_get_filtered_permission_sets(mock_run_cli_command):
    permission_set_list = [
        {"name": "Taco", "built_in": False},
        {"name": "Burrito", "built_in": False}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(permission_set_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    permission_sets = deploy_permission_sets.get_filtered_permission_sets(creds)
    assert [p.name for p in permission_sets] == ["Taco", "Burrito"]
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "all_permission_sets"],
        text=True,
        creds=creds
    )


def test_get_filtered_permission_sets_filter(mock_run_cli_command):
    permission_set_list = [
        {"name": "Taco", "built_in": False},
        {"name": "Burrito", "built_in": False}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(permission_set_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    permission_sets = deploy_permission_sets.get_filtered_permission_sets(creds, "Burrito")
    assert [p.name for p in permission_sets] == ["Burrito"]


def test_write_permission_sets_new(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name="Taco", permissions=["see_look"])]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[])

    creds = {"base_url": "test"}
    deploy_permission_sets.write_permission_sets(permission_set_list, creds)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "create_permission_set", "-"],
        input=json.dumps({"name": "Taco", "permissions": ["see_look"]}),
        text=True,
        creds=creds
    )


def test_write_permission_sets_existing(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name="Taco", permissions=["see_look"])]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[SimpleNamespace(name="Taco", id=1)])

    creds = {"base_url": "test"}
    deploy_permission_sets.write_permission_sets(permission_set_list, creds)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "update_permission_set", "1", "-"],
        input=json.dumps({"name": "Taco", "permissions": ["see_look"]}),
        text=True,
        creds=creds
    )


def test_write_permission_sets_delete(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name="Taco", permissions=["see_look"])]
    target_permission_sets = [SimpleNamespace(name="Taco", id=1), SimpleNamespace(name="Burrito", id=2)]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=target_permission_sets)

    creds = {"base_url": "test"}
    deploy_permission_sets.write_permission_sets(permission_set_list, creds, allow_delete=True)
    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "role", "delete_permission_set", "2"], text=True, creds=creds)
    ])


def test_get_filtered_permission_sets_command_not_found(mock_run_cli_command):
    mock_run_cli_command.side_effect = FileNotFoundError("[Errno 2] No such file or directory: 'looker-cli'")

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_permission_sets.get_filtered_permission_sets(creds)
    assert "looker-cli command not found" in str(exc_info.value)


def test_get_filtered_permission_sets_malformed_json(mock_run_cli_command):
    mock_res = SimpleNamespace(stdout="invalid json", stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_permission_sets.get_filtered_permission_sets(creds)
    assert "Failed to parse JSON from looker-cli" in str(exc_info.value)


def test_get_filtered_permission_sets_unexpected_structure(mock_run_cli_command):
    mock_res = SimpleNamespace(stdout=json.dumps("some_string"), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_permission_sets.get_filtered_permission_sets(creds)
    assert "Unexpected JSON structure returned from looker-cli" in str(exc_info.value)


def test_send_permission_sets(mocker):
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets")
    mocker.patch("looker_deployer.commands.deploy_permission_sets.write_permission_sets")

    source_permission_sets = [SimpleNamespace(name="Taco")]
    deploy_permission_sets.get_filtered_permission_sets.return_value = source_permission_sets

    deploy_permission_sets.send_permission_sets(
        "source_creds", "target_creds",
        pattern="pattern", allow_delete=True
    )

    deploy_permission_sets.get_filtered_permission_sets.assert_called_once_with(
        "source_creds", "pattern"
    )
    deploy_permission_sets.write_permission_sets.assert_called_once_with(
        source_permission_sets, "target_creds", "pattern", True
    )


def test_main(mocker):
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_permission_sets.build_creds")
    mocker.patch("looker_deployer.commands.deploy_permission_sets.send_permission_sets")

    mock_build_creds.side_effect = lambda ini, name: {f"{name}_creds": "true"}

    class MockArgs:
        ini = "looker.ini"
        source = "source_env"
        target = ["target_env_1", "target_env_2"]
        pattern = "some_pattern"
        delete = True
        debug = False

    args = MockArgs()
    deploy_permission_sets.main(args)

    assert mock_build_creds.call_count == 3
    mock_build_creds.assert_has_calls([
        call("looker.ini", "source_env"),
        call("looker.ini", "target_env_1"),
        call("looker.ini", "target_env_2")
    ])

    deploy_permission_sets.send_permission_sets.assert_has_calls([
        call({"source_env_creds": "true"}, {"target_env_1_creds": "true"}, "some_pattern", True),
        call({"source_env_creds": "true"}, {"target_env_2_creds": "true"}, "some_pattern", True)
    ])


def test_get_filtered_permission_sets_single_item(mock_run_cli_command):
    permission_set = {"name": "Taco", "built_in": False}
    mock_res = SimpleNamespace(stdout=json.dumps(permission_set), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    permission_sets = deploy_permission_sets.get_filtered_permission_sets(creds)
    assert [p.name for p in permission_sets] == ["Taco"]


def test_get_filtered_permission_sets_empty_stdout(mock_run_cli_command):
    mock_res = SimpleNamespace(stdout="   ", stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    permission_sets = deploy_permission_sets.get_filtered_permission_sets(creds)
    assert permission_sets == []


def test_get_filtered_permission_sets_subprocess_failure(mock_run_cli_command):
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "Some error")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_permission_sets.get_filtered_permission_sets(creds)


def test_write_permission_sets_create_failure(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name="Taco", permissions=["see_look"])]
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "Create failed")
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[])

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_permission_sets.write_permission_sets(permission_set_list, creds)


def test_write_permission_sets_update_failure(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name="Taco", permissions=["see_look"])]
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "Update failed")
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[SimpleNamespace(name="Taco", id=1)])

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_permission_sets.write_permission_sets(permission_set_list, creds)


def test_write_permission_sets_delete_failure(mock_run_cli_command, mocker):
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "Delete failed")
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[SimpleNamespace(name="Burrito", id=2)])

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_permission_sets.write_permission_sets([], creds, allow_delete=True)


def test_write_permission_sets_update_missing_id(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name="Taco", permissions=["see_look"])]
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[SimpleNamespace(name="Taco")])
    mock_logger = mocker.patch.object(deploy_permission_sets.logger, "error")

    creds = {"base_url": "test"}
    deploy_permission_sets.write_permission_sets(permission_set_list, creds)

    mock_logger.assert_called_once_with("Target permission set 'Taco' is missing an 'id'. Skipping update.")
    mock_run_cli_command.assert_not_called()


def test_write_permission_sets_delete_missing_id(mock_run_cli_command, mocker):
    permission_set_list = [SimpleNamespace(name="Taco", permissions=["see_look"])]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[SimpleNamespace(name="Taco", id=1), SimpleNamespace(name="Burrito")])
    mock_logger = mocker.patch.object(deploy_permission_sets.logger, "error")

    creds = {"base_url": "test"}
    deploy_permission_sets.write_permission_sets(permission_set_list, creds, allow_delete=True)

    mock_logger.assert_called_once_with("Target permission set 'Burrito' is missing an 'id'. Skipping delete.")
    for call_args in mock_run_cli_command.call_args_list:
        assert "delete" not in call_args[0][0]


def test_main_debug(mocker):
    mocker.patch("looker_deployer.commands.deploy_permission_sets.build_creds")
    mocker.patch("looker_deployer.commands.deploy_permission_sets.send_permission_sets")
    mock_logger = mocker.patch.object(deploy_permission_sets.logger, "setLevel")

    class MockArgs:
        ini = "looker.ini"
        source = "source_env"
        target = ["target_env_1"]
        pattern = "some_pattern"
        delete = True
        debug = True

    args = MockArgs()
    deploy_permission_sets.main(args)
    mock_logger.assert_called_once_with(10)


def test_write_permission_sets_invalid_name_type(mock_run_cli_command, mocker):
    permission_set_list = [
        SimpleNamespace(name={"invalid": "dict"}, permissions=["see_look"]),
        SimpleNamespace(name=["invalid", "list"], permissions=["see_look"]),
        SimpleNamespace(name=SimpleNamespace(val="invalid"), permissions=["see_look"]),
        SimpleNamespace(name="ValidName", permissions=["see_look"])
    ]

    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[
        SimpleNamespace(name=123, id=1),
        SimpleNamespace(name="ValidName", id=2)
    ])

    creds = {"base_url": "test"}
    deploy_permission_sets.write_permission_sets(permission_set_list, creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "update_permission_set", "2", "-"],
        input=json.dumps({"name": "ValidName", "permissions": ["see_look"]}),
        text=True,
        creds=creds
    )


# 21. Test duplicate names in source
def test_duplicate_names_in_source(mocker):
    source_permission_sets = [
        SimpleNamespace(name="Taco", permissions=["see_looks"]),
        SimpleNamespace(name="Taco", permissions=["see_user_dashboards"])
    ]

    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[])
    mock_run = mocker.patch("looker_deployer.commands.deploy_permission_sets.run_cli_command")
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run.return_value = mock_res

    creds = {"base_url": "test"}
    deploy_permission_sets.write_permission_sets(source_permission_sets, creds)

    assert mock_run.call_count == 1
    calls = mock_run.call_args_list
    assert "create_permission_set" in calls[0][0][0]
    payload = json.loads(calls[0][1].get("input"))
    assert payload["permissions"] == ["see_user_dashboards"]


# 22. Test duplicate names in target delete behavior
def test_duplicate_names_in_target_delete(mocker):
    source_permission_sets = [
        SimpleNamespace(name="Taco", permissions=["see_looks"])
    ]
    target_permission_sets = [
        SimpleNamespace(name="Taco", id=1),
        SimpleNamespace(name="Taco", id=2)
    ]

    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=target_permission_sets)
    mock_run = mocker.patch("looker_deployer.commands.deploy_permission_sets.run_cli_command")
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run.return_value = mock_res

    creds = {"base_url": "test"}
    deploy_permission_sets.write_permission_sets(source_permission_sets, creds, allow_delete=True)

    call_args_list = [c[0][0] for c in mock_run.call_args_list]
    delete_calls = [args for args in call_args_list if "delete_permission_set" in args]

    assert len(delete_calls) == 1, "Duplicate target permission set was not deleted!"
    assert "2" in delete_calls[0]


# 23. Test looker-cli throws permission error
def test_looker_cli_throws_permission_error(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_permission_sets.run_cli_command")
    mock_run.side_effect = PermissionError("[Errno 13] Permission denied")

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_permission_sets.get_filtered_permission_sets(creds)
    assert "looker-cli" in str(exc_info.value)


# 24. Test get_filtered_permission_sets mixed JSON types
def test_get_filtered_permission_sets_mixed_json_types(mocker):
    mixed_list = [
        {"name": "Taco", "built_in": False},
        42,
        "hello",
        None
    ]
    mock_run = mocker.patch("looker_deployer.commands.deploy_permission_sets.run_cli_command")
    mock_run.return_value = SimpleNamespace(returncode=0, stdout=json.dumps(mixed_list), stderr="")

    creds = {"base_url": "test"}
    res = deploy_permission_sets.get_filtered_permission_sets(creds)
    assert len(res) == 4

    mock_run_write = mocker.patch("looker_deployer.commands.deploy_permission_sets.run_cli_command")
    mock_run_write.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[])

    deploy_permission_sets.write_permission_sets(res, creds)
    assert mock_run_write.call_count == 1
    kwargs = mock_run_write.call_args[1]
    payload = json.loads(kwargs.get("input"))
    assert payload["name"] == "Taco"
