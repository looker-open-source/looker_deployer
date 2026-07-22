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
from unittest.mock import MagicMock
from looker_deployer.commands import deploy_content
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")


def test_get_space_ids_from_name_shared():
    creds = {"base_url": "test"}
    id_list = deploy_content.get_space_ids_from_name("Shared", "0", creds, False)
    assert id_list == ["1"]


def test_get_space_ids_from_name_not_shared(mock_run_cli_command):
    mock_res = MagicMock()
    mock_res.stdout = '[{"id": 42}]'
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    id_list = deploy_content.get_space_ids_from_name("foo", "0", creds, False)
    assert id_list == ["42"]
    mock_run_cli_command.assert_called_with(
        ["looker-cli", "api", "folder", "search_folders", "--name", "foo", "--parent_id", "0"],
        creds=creds,
        check=True,
        capture_output=True,
        text=True
    )


def test_create_or_return_space_one_found(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=["42"])
    creds = {"base_url": "test"}
    target_id = deploy_content.create_or_return_space("foo", "bar", creds)
    assert target_id == "42"


def test_create_or_return_space_multi_found(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=["42", "13"])
    creds = {"base_url": "test"}
    with pytest.raises(AssertionError):
        deploy_content.create_or_return_space("foo", "bar", creds)


def test_create_or_return_space_none_found(mock_run_cli_command, mocker):
    mock_res = MagicMock()
    mock_res.stdout = '{"id": 42}'
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=[])

    creds = {"base_url": "test"}
    target_id = deploy_content.create_or_return_space("foo", "5", creds, False)
    assert target_id == "42"
    mock_run_cli_command.assert_called_with(
        ["looker-cli", "api", "folder", "create_folder", "-"],
        input='{"name": "foo", "parent_id": "5"}',
        creds=creds,
        check=True,
        capture_output=True,
        text=True
    )


def test_import_content(mock_run_cli_command):
    creds = {"base_url": "test"}
    deploy_content.import_content("dashboard", "tacocat.json", "42", creds, False)
    mock_run_cli_command.assert_called_once_with([
        "looker-cli",
        "dashboard",
        "import",
        "tacocat.json",
        "42",
        "--force"
    ], creds=creds, check=True, capture_output=True, text=True)


def test_import_content_debug(mock_run_cli_command):
    creds = {"base_url": "test"}
    deploy_content.import_content("dashboard", "tacocat.json", "42", creds, True)
    mock_run_cli_command.assert_called_once_with([
        "looker-cli",
        "dashboard",
        "import",
        "tacocat.json",
        "42",
        "--force"
    ], creds=creds, check=True, capture_output=True, text=True)


def test_build_spaces(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.create_or_return_space", return_value="42")
    creds = {"base_url": "test"}
    space_id = deploy_content.build_spaces(["taco"], creds, False)
    assert space_id == "42"


def test_deploy_space_build_call(mocker):
    mocker.patch("os.listdir", return_value=["Dashboard", "Look"])
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("looker_deployer.commands.deploy_content.build_spaces")
    mocker.patch("looker_deployer.commands.deploy_content.import_content")

    creds = {"base_url": "test"}
    deploy_content.deploy_space("Foo/Shared/Bar/", creds, False, "Shared", False)
    deploy_content.build_spaces.assert_called_with(["Shared", "Bar"], creds, False)


def test_deploy_space_look_call(mocker):
    mocker.patch("os.listdir", return_value=["Look_test"])
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("looker_deployer.commands.deploy_content.build_spaces", return_value="42")
    mocker.patch("looker_deployer.commands.deploy_content.import_content")

    creds = {"base_url": "test"}
    deploy_content.deploy_space("Foo/Shared/Bar", creds, False, "Shared", False)
    deploy_content.import_content.assert_called_once_with("look", "Foo/Shared/Bar/Look_test", "42", creds, False)


def test_deploy_space_dashboard_call(mocker):
    mocker.patch("os.listdir", return_value=["Dashboard_test"])
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("looker_deployer.commands.deploy_content.build_spaces", return_value="42")
    mocker.patch("looker_deployer.commands.deploy_content.import_content")

    creds = {"base_url": "test"}
    deploy_content.deploy_space("Foo/Shared/Bar", creds, False, "Shared", False)
    deploy_content.import_content.assert_called_once_with("dashboard", "Foo/Shared/Bar/Dashboard_test", "42", creds, False)


def test_deploy_content_build_call(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.build_spaces")
    mocker.patch("looker_deployer.commands.deploy_content.import_content")

    creds = {"base_url": "test"}
    deploy_content.deploy_content("look", "Foo/Shared/Bar/Baz/Dashboard_test.json", creds, "Shared", False)
    deploy_content.build_spaces.assert_called_with(["Shared", "Bar", "Baz"], creds, False)


def test_deploy_content_import_content_call(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.build_spaces", return_value="42")
    mocker.patch("looker_deployer.commands.deploy_content.import_content")

    creds = {"base_url": "test"}
    deploy_content.deploy_content("look", "Foo/Shared/Bar/Look_test.json", creds, "Shared", False)
    deploy_content.import_content.assert_called_with("look", "Foo/Shared/Bar/Look_test.json", "42", creds, False)


def test_import_content_called_process_error(mock_run_cli_command, mocker):
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "fake stdout", "fake stderr")
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.import_content("dashboard", "tacocat.json", "42", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli import failed",
        extra={"stdout": "fake stdout", "stderr": "fake stderr"}
    )


def test_import_content_called_process_error_none_outputs(mock_run_cli_command, mocker):
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, None, None)
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.import_content("dashboard", "tacocat.json", "42", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli import failed",
        extra={"stdout": None, "stderr": None}
    )


def test_import_content_called_process_error_empty_outputs(mock_run_cli_command, mocker):
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "")
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.import_content("dashboard", "tacocat.json", "42", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli import failed",
        extra={"stdout": "", "stderr": ""}
    )


def test_create_or_return_space_called_process_error(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=[])
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "fake stdout", "fake stderr")
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.create_or_return_space("foo", "5", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli api folder create_folder failed",
        extra={"stdout": "fake stdout", "stderr": "fake stderr"}
    )


def test_create_or_return_space_called_process_error_none_outputs(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=[])
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, None, None)
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.create_or_return_space("foo", "5", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli api folder create_folder failed",
        extra={"stdout": None, "stderr": None}
    )
