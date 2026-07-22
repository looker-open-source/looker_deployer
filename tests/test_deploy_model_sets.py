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
from looker_deployer.commands import deploy_model_sets
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_model_sets.run_cli_command")


def test_get_filtered_model_sets(mock_run_cli_command):
    model_set_list = [
        {"name": "Taco", "built_in": False},
        {"name": "Burrito", "built_in": False}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(model_set_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    model_sets = deploy_model_sets.get_filtered_model_sets(creds)
    assert [m.name for m in model_sets] == ["Taco", "Burrito"]
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "all_model_sets"],
        text=True,
        creds=creds
    )


def test_get_filtered_model_sets_filter(mock_run_cli_command):
    model_set_list = [
        {"name": "Taco", "built_in": False},
        {"name": "Burrito", "built_in": False}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(model_set_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    model_sets = deploy_model_sets.get_filtered_model_sets(creds, "Burrito")
    assert [m.name for m in model_sets] == ["Burrito"]


def test_write_model_sets_new(mock_run_cli_command, mocker):
    model_set_list = [SimpleNamespace(name="Taco", models=["model1"])]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[])

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets(model_set_list, creds)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "create_model_set", "-"],
        input=json.dumps({"name": "Taco", "models": ["model1"]}),
        text=True,
        creds=creds
    )


def test_write_model_sets_existing(mock_run_cli_command, mocker):
    model_set_list = [SimpleNamespace(name="Taco", models=["model1"])]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[SimpleNamespace(name="Taco", id=1)])

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets(model_set_list, creds)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "update_model_set", "1", "-"],
        input=json.dumps({"name": "Taco", "models": ["model1"]}),
        text=True,
        creds=creds
    )


def test_write_model_sets_delete(mock_run_cli_command, mocker):
    model_set_list = [SimpleNamespace(name="Taco", models=["model1"])]
    target_model_sets = [SimpleNamespace(name="Taco", id=1), SimpleNamespace(name="Burrito", id=2)]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=target_model_sets)

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets(model_set_list, creds, allow_delete=True)
    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "role", "delete_model_set", "2"], text=True, creds=creds)
    ])


def test_get_filtered_model_sets_command_not_found(mock_run_cli_command):
    mock_run_cli_command.side_effect = FileNotFoundError("[Errno 2] No such file or directory: 'looker-cli'")

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_model_sets.get_filtered_model_sets(creds)
    assert "looker-cli command not found" in str(exc_info.value)


def test_get_filtered_model_sets_malformed_json(mock_run_cli_command):
    mock_res = SimpleNamespace(stdout="invalid json", stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_model_sets.get_filtered_model_sets(creds)
    assert "Failed to parse JSON from looker-cli" in str(exc_info.value)


def test_get_filtered_model_sets_unexpected_structure(mock_run_cli_command):
    mock_res = SimpleNamespace(stdout=json.dumps("some_string"), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_model_sets.get_filtered_model_sets(creds)
    assert "Unexpected JSON structure returned from looker-cli" in str(exc_info.value)


def test_send_model_sets(mocker):
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets")
    mocker.patch("looker_deployer.commands.deploy_model_sets.write_model_sets")

    source_model_sets = [SimpleNamespace(name="Taco")]
    deploy_model_sets.get_filtered_model_sets.return_value = source_model_sets

    deploy_model_sets.send_model_sets(
        "source_creds", "target_creds",
        pattern="pattern", allow_delete=True
    )

    deploy_model_sets.get_filtered_model_sets.assert_called_once_with(
        "source_creds", "pattern"
    )
    deploy_model_sets.write_model_sets.assert_called_once_with(
        source_model_sets, "target_creds", "pattern", True
    )


def test_main(mocker):
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_model_sets.build_creds")
    mocker.patch("looker_deployer.commands.deploy_model_sets.send_model_sets")

    mock_build_creds.side_effect = lambda ini, name: {f"{name}_creds": "true"}

    class MockArgs:
        ini = "looker.ini"
        source = "source_env"
        target = ["target_env_1", "target_env_2"]
        pattern = "some_pattern"
        delete = True
        debug = False

    args = MockArgs()
    deploy_model_sets.main(args)

    assert mock_build_creds.call_count == 3
    mock_build_creds.assert_has_calls([
        call("looker.ini", "source_env"),
        call("looker.ini", "target_env_1"),
        call("looker.ini", "target_env_2")
    ])

    deploy_model_sets.send_model_sets.assert_has_calls([
        call({"source_env_creds": "true"}, {"target_env_1_creds": "true"}, "some_pattern", True),
        call({"source_env_creds": "true"}, {"target_env_2_creds": "true"}, "some_pattern", True)
    ])


def test_get_filtered_model_sets_single_item(mock_run_cli_command):
    model_set = {"name": "Taco", "built_in": False}
    mock_res = SimpleNamespace(stdout=json.dumps(model_set), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    model_sets = deploy_model_sets.get_filtered_model_sets(creds)
    assert [m.name for m in model_sets] == ["Taco"]


def test_get_filtered_model_sets_empty_stdout(mock_run_cli_command):
    mock_res = SimpleNamespace(stdout="   ", stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    model_sets = deploy_model_sets.get_filtered_model_sets(creds)
    assert model_sets == []


def test_get_filtered_model_sets_subprocess_failure(mock_run_cli_command):
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "Some error")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
         deploy_model_sets.get_filtered_model_sets(creds)


def test_write_model_sets_create_failure(mock_run_cli_command, mocker):
    model_set_list = [SimpleNamespace(name="Taco", models=["model1"])]
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "Create failed")
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[])

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_model_sets.write_model_sets(model_set_list, creds)


def test_write_model_sets_update_failure(mock_run_cli_command, mocker):
    model_set_list = [SimpleNamespace(name="Taco", models=["model1"])]
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "Update failed")
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[SimpleNamespace(name="Taco", id=1)])

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_model_sets.write_model_sets(model_set_list, creds)


def test_write_model_sets_delete_failure(mock_run_cli_command, mocker):
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "Delete failed")
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[SimpleNamespace(name="Burrito", id=2)])

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_model_sets.write_model_sets([], creds, allow_delete=True)


def test_write_model_sets_update_missing_id(mock_run_cli_command, mocker):
    model_set_list = [SimpleNamespace(name="Taco", models=["model1"])]
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[SimpleNamespace(name="Taco")])
    mock_logger = mocker.patch.object(deploy_model_sets.logger, "error")

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets(model_set_list, creds)

    mock_logger.assert_called_once_with("Target model set 'Taco' is missing an 'id'. Skipping update.")
    mock_run_cli_command.assert_not_called()


def test_write_model_sets_delete_missing_id(mock_run_cli_command, mocker):
    model_set_list = [SimpleNamespace(name="Taco", models=["model1"])]
    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[SimpleNamespace(name="Taco", id=1), SimpleNamespace(name="Burrito")])
    mock_logger = mocker.patch.object(deploy_model_sets.logger, "error")

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets(model_set_list, creds, allow_delete=True)

    mock_logger.assert_called_once_with("Target model set 'Burrito' is missing an 'id'. Skipping delete.")
    for call_args in mock_run_cli_command.call_args_list:
        assert "delete" not in call_args[0][0]


def test_main_debug(mocker):
    mocker.patch("looker_deployer.commands.deploy_model_sets.build_creds")
    mocker.patch("looker_deployer.commands.deploy_model_sets.send_model_sets")
    mock_logger = mocker.patch.object(deploy_model_sets.logger, "setLevel")

    class MockArgs:
        ini = "looker.ini"
        source = "source_env"
        target = ["target_env_1"]
        pattern = "some_pattern"
        delete = True
        debug = True

    args = MockArgs()
    deploy_model_sets.main(args)
    mock_logger.assert_called_once_with(10)
