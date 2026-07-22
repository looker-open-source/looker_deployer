# Copyright 2026 Google LLC
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
from unittest.mock import MagicMock, patch, mock_open
import json
from pathlib import Path
from looker_deployer.commands import deploy_content
from looker_deployer.commands import deploy_content_export
from looker_deployer.utils.exceptions import LookerCLIError


def test_adv_get_space_ids_from_name_users_empty(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")
    mock_res = MagicMock()
    mock_res.stdout = '[]'
    mock_run.return_value = mock_res

    creds = {"base_url": "test"}
    with pytest.raises(IndexError):
        deploy_content.get_space_ids_from_name("Users", "0", creds, False)


def test_adv_create_or_return_space_integer_users_parent(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=[])
    mock_run = mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")
    mock_res = MagicMock()
    mock_res.stdout = '{"id": 42}'
    mock_run.return_value = mock_res

    creds = {"base_url": "test"}
    res = deploy_content.create_or_return_space("foo", 2, creds, False)
    assert res == "42"
    mock_run.assert_called_with(
        ["looker-cli", "api", "folder", "create_folder", "-"],
        input='{"name": "foo", "parent_id": "2"}',
        creds=creds,
        check=True,
        capture_output=True,
        text=True
    )


def test_adv_deploy_space_windows_forward_slashes(mocker):
    import unittest.mock

    mocker.patch("os.listdir", return_value=["Look_1"])
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("os.path.isdir", return_value=False)

    mocker.patch("looker_deployer.commands.deploy_content.build_spaces", return_value="42")
    mocker.patch("looker_deployer.commands.deploy_content.import_content")

    creds = {"base_url": "test"}
    with unittest.mock.patch("looker_deployer.commands.deploy_content.os.name", "nt"), \
         unittest.mock.patch("looker_deployer.commands.deploy_content.os.sep", "\\"):
        deploy_content.deploy_space("Foo/Shared/Bar/", creds, False, "Shared", False)

    deploy_content.build_spaces.assert_called_once_with(["Shared", "Bar"], creds, False)


def test_adv_deploy_space_windows_backslashes_no_trailing(mocker):
    import unittest.mock

    mocker.patch("os.listdir", return_value=["Look_1"])
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("os.path.isdir", return_value=False)

    mocker.patch("looker_deployer.commands.deploy_content.build_spaces", return_value="42")
    mocker.patch("looker_deployer.commands.deploy_content.import_content")

    creds = {"base_url": "test"}
    with unittest.mock.patch("looker_deployer.commands.deploy_content.os.name", "nt"), \
         unittest.mock.patch("looker_deployer.commands.deploy_content.os.sep", "\\"):
        deploy_content.deploy_space("Foo\\Shared\\Bar", creds, False, "Shared", False)

    deploy_content.build_spaces.assert_called_once_with(["Shared", "Bar"], creds, False)


def test_adv_recurse_folders_stops_at_zero(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")

    mock_res_child = mocker.MagicMock()
    mock_res_child.stdout = '{"name": "child", "parent_id": "0"}'

    mock_res_zero = mocker.MagicMock()
    mock_res_zero.stdout = '{"name": "Shared", "parent_id": null}'

    mock_run.side_effect = [mock_res_child, mock_res_zero]

    creds = {"base_url": "test"}
    folder_list = []
    deploy_content_export.recurse_folders("child", folder_list, creds, False)

    assert mock_run.call_count == 2
    mock_run.assert_any_call(["looker-cli", "folder", "cat", "child"], creds=creds, check=True, capture_output=True, text=True)
    mock_run.assert_any_call(["looker-cli", "folder", "cat", "0"], creds=creds, check=True, capture_output=True, text=True)


def test_import_content_called_process_error_none_outputs(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")
    mock_run.side_effect = LookerCLIError("cmd", 1, None, None)
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.import_content("dashboard", "tacocat.json", "42", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli import failed",
        extra={"stdout": None, "stderr": None}
    )


def test_import_content_called_process_error_empty_outputs(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")
    mock_run.side_effect = LookerCLIError("cmd", 1, "", "")
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.import_content("dashboard", "tacocat.json", "42", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli import failed",
        extra={"stdout": "", "stderr": ""}
    )


def test_export_spaces_called_process_error_none_outputs(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")
    mock_run.side_effect = LookerCLIError("cmd", 1, None, None)
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content_export.export_spaces("1", creds, "foo/bar", False)

    mock_logger.error.assert_called_once_with(
        "looker-cli folder export failed",
        extra={"stdout": None, "stderr": None}
    )


def test_export_content_called_process_error_none_outputs(mocker):
    fake_file_path = Path("foo/bar/dashboard_1.json")
    creds = {"base_url": "test"}
    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()) as mocked_file:
        mock_run = mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")
        mock_run.side_effect = LookerCLIError("cmd", 1, None, None)
        mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

        with pytest.raises(LookerCLIError):
            deploy_content_export.export_content("dashboard", "1", creds, "foo/bar", False)

        mocked_file.assert_called_once_with(fake_file_path, 'w')
        mock_logger.error.assert_called_once_with(
            "looker-cli dashboard cat failed",
            extra={"stdout": None, "stderr": None}
        )


def test_create_or_return_space_called_process_error_empty_outputs(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=[])
    mock_run = mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")
    mock_run.side_effect = LookerCLIError("cmd", 1, "", "")
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.create_or_return_space("foo", "5", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli api folder create_folder failed",
        extra={"stdout": "", "stderr": ""}
    )


def test_get_space_ids_from_name_called_process_error_none_outputs(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")
    mock_run.side_effect = LookerCLIError("cmd", 1, None, None)
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.get_space_ids_from_name("foo", "0", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli folder search failed",
        extra={"stdout": None, "stderr": None}
    )


def test_get_space_ids_from_name_called_process_error_empty_outputs(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")
    mock_run.side_effect = LookerCLIError("cmd", 1, "", "")
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.get_space_ids_from_name("foo", "0", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli folder search failed",
        extra={"stdout": "", "stderr": ""}
    )


def test_recurse_folders_called_process_error_none_outputs(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")
    mock_run.side_effect = LookerCLIError("cmd", 1, None, None)
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content_export.recurse_folders("1", [], creds, False)

    expected_error_msg = "Command 'cmd' failed with exit code 1.\nStdout: None\nStderr: None"
    mock_logger.error.assert_called_once_with(
        "Failed to retrieve folder information",
        extra={
            "stdout": None,
            "stderr": None,
            "folder_id": "1",
            "error": expected_error_msg
        }
    )


def test_recurse_folders_called_process_error_empty_outputs(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")
    mock_run.side_effect = LookerCLIError("cmd", 1, "", "")
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content_export.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content_export.recurse_folders("1", [], creds, False)

    expected_error_msg = "Command 'cmd' failed with exit code 1.\nStdout: \nStderr: "
    mock_logger.error.assert_called_once_with(
        "Failed to retrieve folder information",
        extra={
            "stdout": "",
            "stderr": "",
            "folder_id": "1",
            "error": expected_error_msg
        }
    )
