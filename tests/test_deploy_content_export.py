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
from unittest.mock import patch, mock_open
from pathlib import Path
import subprocess
from looker_deployer.commands import deploy_content_export
from looker_deployer.utils.exceptions import LookerCLIError
from types import SimpleNamespace


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")


def test_export_space(mock_run_cli_command):
    creds = {"base_url": "test"}
    deploy_content_export.export_spaces("1", creds, "foo/bar", False)
    mock_run_cli_command.assert_called_with([
        "looker-cli",
        "folder",
        "export",
        "1",
        "--dir",
        "foo/bar"
    ], creds=creds, check=True, capture_output=True, text=True)


def test_export_space_debug(mock_run_cli_command):
    creds = {"base_url": "test"}
    deploy_content_export.export_spaces("1", creds, "foo/bar", True)
    mock_run_cli_command.assert_called_with([
        "looker-cli",
        "folder",
        "export",
        "1",
        "--dir",
        "foo/bar"
    ], creds=creds, check=True, capture_output=True, text=True)


def test_recurse_folders(mock_run_cli_command):
    creds = {"base_url": "test"}
    mock_result = SimpleNamespace(stdout='{"name": "foo", "parent_id": null}', stderr="")
    mock_run_cli_command.return_value = mock_result

    folder = deploy_content_export.recurse_folders("1", [], creds, False)
    assert folder == ["foo"]
    mock_run_cli_command.assert_called_with(["looker-cli", "folder", "cat", "1"], creds=creds, check=True, capture_output=True, text=True)


def test_recurse_folders_json_decode_error(mock_run_cli_command):
    creds = {"base_url": "test"}
    mock_result = SimpleNamespace(stdout='invalid json', stderr="")
    mock_run_cli_command.return_value = mock_result

    with pytest.raises(json.JSONDecodeError):
        deploy_content_export.recurse_folders("1", [], creds, False)


def test_recurse_folders_subprocess_error(mock_run_cli_command, mocker):
    creds = {"base_url": "test"}
    mock_run_cli_command.side_effect = LookerCLIError(
        command="looker-cli",
        exit_code=1,
        stdout="fake stdout",
        stderr="fake stderr"
    )

    mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

    with pytest.raises(LookerCLIError):
        deploy_content_export.recurse_folders("1", [], creds, False)

    mock_logger.error.assert_called_once_with(
        "Failed to retrieve folder information",
        extra={
            "stdout": "fake stdout",
            "stderr": "fake stderr",
            "folder_id": "1",
            "error": "Command 'looker-cli' failed with exit code 1.\nStdout: fake stdout\nStderr: fake stderr"
        }
    )


def test_send_export(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.recurse_folders")
    deploy_content_export.recurse_folders.return_value = ["baz", "bosh", "Shared"]

    mocker.patch("pathlib.Path.mkdir")

    mocker.patch("looker_deployer.commands.deploy_content_export.export_spaces")
    creds = {"base_url": "test"}
    deploy_content_export.send_export(creds, "./foo/bar", folders=["1"], debug=False)
    deploy_content_export.export_spaces.assert_called_with("1", creds, "foo/bar/Shared/bosh", False)


def test_export_dashboard(mock_run_cli_command):
    creds = {"base_url": "test"}
    fake_file_path = Path("foo/bar/dashboard_1.json")
    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()) as mocked_file:
        deploy_content_export.export_content("dashboard", "1", creds, "foo/bar", False)

        mocked_file.assert_called_once_with(fake_file_path, 'w')
        mock_run_cli_command.assert_called_with([
            "looker-cli",
            "dashboard",
            "cat",
            "1"
        ], stdout=mocked_file(), stderr=subprocess.PIPE, creds=creds, check=True, text=True)


def test_export_look(mock_run_cli_command):
    creds = {"base_url": "test"}
    fake_file_path = Path("foo/bar/look_1.json")
    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()) as mocked_file:
        deploy_content_export.export_content("look", "1", creds, "foo/bar", False)

        mocked_file.assert_called_once_with(fake_file_path, 'w')
        mock_run_cli_command.assert_called_with([
            "looker-cli",
            "look",
            "cat",
            "1"
        ], stdout=mocked_file(), stderr=subprocess.PIPE, creds=creds, check=True, text=True)


def test_recurse_folders_missing_name_key(mock_run_cli_command):
    creds = {"base_url": "test"}
    mock_result = SimpleNamespace(stdout='{"parent_id": null}', stderr="")
    mock_run_cli_command.return_value = mock_result

    with pytest.raises(KeyError):
        deploy_content_export.recurse_folders("1", [], creds, False)


def test_export_spaces_called_process_error(mock_run_cli_command, mocker):
    creds = {"base_url": "test"}
    mock_run_cli_command.side_effect = LookerCLIError(
        command="looker-cli",
        exit_code=1,
        stdout="fake stdout",
        stderr="fake stderr"
    )

    mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

    with pytest.raises(LookerCLIError):
        deploy_content_export.export_spaces("1", creds, "foo/bar", False)

    mock_logger.error.assert_called_once_with(
        "looker-cli folder export failed",
        extra={"stdout": "fake stdout", "stderr": "fake stderr"}
    )


def test_export_content_called_process_error(mock_run_cli_command, mocker):
    creds = {"base_url": "test"}
    fake_file_path = Path("foo/bar/dashboard_1.json")
    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()) as mocked_file:
        mock_run_cli_command.side_effect = LookerCLIError(
            command="looker-cli",
            exit_code=1,
            stdout="fake stdout",
            stderr="fake stderr"
        )

        mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

        with pytest.raises(LookerCLIError):
            deploy_content_export.export_content("dashboard", "1", creds, "foo/bar", False)

        mocked_file.assert_called_once_with(fake_file_path, 'w')
        mock_logger.error.assert_called_once_with(
            "looker-cli dashboard cat failed",
            extra={"stdout": "fake stdout", "stderr": "fake stderr"}
        )


def test_export_spaces_called_process_error_none_outputs(mock_run_cli_command, mocker):
    creds = {"base_url": "test"}
    mock_run_cli_command.side_effect = LookerCLIError(
        command="looker-cli",
        exit_code=1,
        stdout=None,
        stderr=None
    )

    mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

    with pytest.raises(LookerCLIError):
        deploy_content_export.export_spaces("1", creds, "foo/bar", False)

    mock_logger.error.assert_called_once_with(
        "looker-cli folder export failed",
        extra={"stdout": None, "stderr": None}
    )


def test_export_content_called_process_error_none_outputs(mock_run_cli_command, mocker):
    creds = {"base_url": "test"}
    fake_file_path = Path("foo/bar/dashboard_1.json")
    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()) as mocked_file:
        mock_run_cli_command.side_effect = LookerCLIError(
            command="looker-cli",
            exit_code=1,
            stdout=None,
            stderr=None
        )

        mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

        with pytest.raises(LookerCLIError):
            deploy_content_export.export_content("dashboard", "1", creds, "foo/bar", False)

        mocked_file.assert_called_once_with(fake_file_path, 'w')
        mock_logger.error.assert_called_once_with(
            "looker-cli dashboard cat failed",
            extra={"stdout": None, "stderr": None}
        )


def test_export_spaces_called_process_error_empty_outputs(mock_run_cli_command, mocker):
    creds = {"base_url": "test"}
    mock_run_cli_command.side_effect = LookerCLIError(
        command="looker-cli",
        exit_code=1,
        stdout="",
        stderr=""
    )

    mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

    with pytest.raises(LookerCLIError):
        deploy_content_export.export_spaces("1", creds, "foo/bar", False)

    mock_logger.error.assert_called_once_with(
        "looker-cli folder export failed",
        extra={"stdout": "", "stderr": ""}
    )


def test_export_content_called_process_error_empty_outputs(mock_run_cli_command, mocker):
    creds = {"base_url": "test"}
    fake_file_path = Path("foo/bar/dashboard_1.json")
    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()) as mocked_file:
        mock_run_cli_command.side_effect = LookerCLIError(
            command="looker-cli",
            exit_code=1,
            stdout="",
            stderr=""
        )

        mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

        with pytest.raises(LookerCLIError):
            deploy_content_export.export_content("dashboard", "1", creds, "foo/bar", False)

        mocked_file.assert_called_once_with(fake_file_path, 'w')
        mock_logger.error.assert_called_once_with(
            "looker-cli dashboard cat failed",
            extra={"stdout": "", "stderr": ""}
        )
