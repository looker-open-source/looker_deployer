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
from looker_deployer.commands import deploy_content, deploy_content_export
from looker_deployer.utils.exceptions import LookerCLIError


def test_create_or_return_space_called_process_error_cases(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=[])
    mock_logger_error = mocker.patch.object(deploy_content.logger, "error")
    mock_run_cli_command = mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")

    creds = {"base_url": "test"}

    # Case 1: stdout/stderr are None
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, None, None)

    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content.create_or_return_space("test_space", "0", creds, False)

    mock_logger_error.assert_called_once_with(
        "looker-cli api folder create_folder failed",
        extra={"stdout": None, "stderr": None}
    )

    # Case 2: stdout/stderr are empty strings
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "")
    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content.create_or_return_space("test_space", "0", creds, False)
    mock_logger_error.assert_called_once_with(
        "looker-cli api folder create_folder failed",
        extra={"stdout": "", "stderr": ""}
    )

    # Case 3: stdout/stderr have actual outputs
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "mocked stdout", "mocked stderr")
    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content.create_or_return_space("test_space", "0", creds, False)
    mock_logger_error.assert_called_once_with(
        "looker-cli api folder create_folder failed",
        extra={"stdout": "mocked stdout", "stderr": "mocked stderr"}
    )


def test_import_content_called_process_error_cases(mocker):
    mock_logger_error = mocker.patch.object(deploy_content.logger, "error")
    mock_run_cli_command = mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")

    creds = {"base_url": "test"}

    # Case 1: stdout/stderr are None
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, None, None)

    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content.import_content("dashboard", "tacocat.json", "42", creds, False)
    mock_logger_error.assert_called_once_with(
        "looker-cli import failed",
        extra={"stdout": None, "stderr": None}
    )

    # Case 2: stdout/stderr are empty strings
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "")
    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content.import_content("dashboard", "tacocat.json", "42", creds, False)
    mock_logger_error.assert_called_once_with(
        "looker-cli import failed",
        extra={"stdout": "", "stderr": ""}
    )

    # Case 3: stdout/stderr have actual outputs
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "mocked import stdout", "mocked import stderr")
    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content.import_content("dashboard", "tacocat.json", "42", creds, False)
    mock_logger_error.assert_called_once_with(
        "looker-cli import failed",
        extra={"stdout": "mocked import stdout", "stderr": "mocked import stderr"}
    )


def test_export_spaces_called_process_error_cases(mocker):
    mock_logger_error = mocker.patch.object(deploy_content_export.logger, "error")
    mock_run_cli_command = mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")

    creds = {"base_url": "test"}

    # Case 1: stdout/stderr are None
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, None, None)

    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content_export.export_spaces("42", creds, "path", False)
    mock_logger_error.assert_called_once_with(
        "looker-cli folder export failed",
        extra={"stdout": None, "stderr": None}
    )

    # Case 2: stdout/stderr are empty strings
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "")
    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content_export.export_spaces("42", creds, "path", False)
    mock_logger_error.assert_called_once_with(
        "looker-cli folder export failed",
        extra={"stdout": "", "stderr": ""}
    )

    # Case 3: stdout/stderr have actual outputs
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "mocked export stdout", "mocked export stderr")
    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content_export.export_spaces("42", creds, "path", False)
    mock_logger_error.assert_called_once_with(
        "looker-cli folder export failed",
        extra={"stdout": "mocked export stdout", "stderr": "mocked export stderr"}
    )


def test_export_content_called_process_error_cases(mocker):
    mocker.patch("builtins.open", mocker.mock_open())
    mock_logger_error = mocker.patch.object(deploy_content_export.logger, "error")
    mock_run_cli_command = mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")

    creds = {"base_url": "test"}

    # Case 1: stdout/stderr are None
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, None, None)

    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content_export.export_content("dashboard", "42", creds, "path", False)
    mock_logger_error.assert_called_once_with(
        "looker-cli dashboard cat failed",
        extra={"stdout": None, "stderr": None}
    )

    # Case 2: stdout/stderr are empty strings
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "", "")
    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content_export.export_content("dashboard", "42", creds, "path", False)
    mock_logger_error.assert_called_once_with(
        "looker-cli dashboard cat failed",
        extra={"stdout": "", "stderr": ""}
    )

    # Case 3: stdout/stderr have actual outputs
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "mocked cat stdout", "mocked cat stderr")
    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content_export.export_content("dashboard", "42", creds, "path", False)
    mock_logger_error.assert_called_once_with(
        "looker-cli dashboard cat failed",
        extra={"stdout": "mocked cat stdout", "stderr": "mocked cat stderr"}
    )


def test_recurse_folders_called_process_error_cases(mocker):
    mock_logger_error = mocker.patch.object(deploy_content_export.logger, "error")
    mock_run_cli_command = mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")

    creds = {"base_url": "test"}

    # Case 1: stdout/stderr are None
    e = LookerCLIError("cmd", 1, None, None)
    mock_run_cli_command.side_effect = e

    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content_export.recurse_folders("42", [], creds, False)
    mock_logger_error.assert_called_once_with(
        "Failed to retrieve folder information",
        extra={
            "stdout": None,
            "stderr": None,
            "folder_id": "42",
            "error": str(e)
        }
    )

    # Case 2: stdout/stderr are empty strings
    e = LookerCLIError("cmd", 1, "", "")
    mock_run_cli_command.side_effect = e
    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content_export.recurse_folders("42", [], creds, False)
    mock_logger_error.assert_called_once_with(
        "Failed to retrieve folder information",
        extra={
            "stdout": "",
            "stderr": "",
            "folder_id": "42",
            "error": str(e)
        }
    )

    # Case 3: stdout/stderr have actual outputs
    e = LookerCLIError("cmd", 1, "mocked recurse stdout", "mocked recurse stderr")
    mock_run_cli_command.side_effect = e
    mock_logger_error.reset_mock()
    with pytest.raises(LookerCLIError):
        deploy_content_export.recurse_folders("42", [], creds, False)
    mock_logger_error.assert_called_once_with(
        "Failed to retrieve folder information",
        extra={
            "stdout": "mocked recurse stdout",
            "stderr": "mocked recurse stderr",
            "folder_id": "42",
            "error": str(e)
        }
    )
