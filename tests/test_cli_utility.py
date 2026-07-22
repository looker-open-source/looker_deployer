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
from looker_deployer.utils.cli import run_cli_command, inject_auth_flags
from looker_deployer.utils.exceptions import LookerCLIError


def test_run_cli_command_windows(mocker):
    mocker.patch("looker_deployer.utils.cli.is_windows", return_value=True)
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run = mocker.patch("subprocess.run", return_value=mock_res)

    cmd = ["looker-cli", "group", "list"]
    run_cli_command(cmd)

    mock_run.assert_called_once()
    called_cmd = mock_run.call_args[0][0]
    assert called_cmd[:2] == ["cmd.exe", "/c"]


def test_run_cli_command_non_windows(mocker):
    mocker.patch("looker_deployer.utils.cli.is_windows", return_value=False)
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_run = mocker.patch("subprocess.run", return_value=mock_res)

    cmd = ["looker-cli", "group", "list"]
    run_cli_command(cmd)

    mock_run.assert_called_once_with(cmd, capture_output=True)


def test_run_cli_command_file_not_found(mocker):
    mocker.patch("subprocess.run", side_effect=FileNotFoundError("No such file or directory"))

    cmd = ["looker-cli", "group", "list"]
    with pytest.raises(FileNotFoundError, match="looker-cli command not found"):
        run_cli_command(cmd)


def test_run_cli_command_success(mocker):
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "success_result"
    mock_run = mocker.patch("subprocess.run", return_value=mock_res)

    cmd = ["looker-cli", "group", "list"]
    res = run_cli_command(cmd, capture_output=True, text=True)

    assert res.stdout == "success_result"
    mock_run.assert_called_once_with(cmd, capture_output=True, text=True)


def test_run_cli_command_failure(mocker):
    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stdout = b"some output"
    mock_res.stderr = b"some error"
    mocker.patch("subprocess.run", return_value=mock_res)

    cmd = ["looker-cli", "group", "list"]
    with pytest.raises(LookerCLIError) as excinfo:
        run_cli_command(cmd, check=True)

    assert excinfo.value.exit_code == 1
    assert "some error" in excinfo.value.stderr


def test_inject_auth_flags_standard_https():
    creds = {
        "base_url": "https://mylooker.com:19999",
        "client_id": "my_client_id",
        "client_secret": "my_client_secret",
        "verify_ssl": "true"
    }
    cmd = ["looker-cli", "group", "list"]
    expected = [
        "looker-cli",
        "--host", "mylooker.com",
        "--port", "19999",
        "--client-id", "my_client_id",
        "--client-secret", "my_client_secret",
        "group", "list"
    ]
    assert inject_auth_flags(cmd, creds) == expected


def test_inject_auth_flags_http():
    creds = {
        "base_url": "http://mylooker.com",
        "client_id": "my_client_id",
        "client_secret": "my_client_secret"
    }
    cmd = ["looker-cli", "group", "list"]
    expected = [
        "looker-cli",
        "--ssl=false",
        "--host", "mylooker.com",
        "--client-id", "my_client_id",
        "--client-secret", "my_client_secret",
        "group", "list"
    ]
    assert inject_auth_flags(cmd, creds) == expected


def test_inject_auth_flags_no_scheme():
    creds = {
        "base_url": "mylooker.com:19999",
        "client_id": "my_client_id",
        "client_secret": "my_client_secret"
    }
    cmd = ["looker-cli", "group", "list"]
    expected = [
        "looker-cli",
        "--host", "mylooker.com",
        "--port", "19999",
        "--client-id", "my_client_id",
        "--client-secret", "my_client_secret",
        "group", "list"
    ]
    assert inject_auth_flags(cmd, creds) == expected


def test_inject_auth_flags_verify_ssl_false():
    creds = {
        "base_url": "https://mylooker.com",
        "client_id": "my_client_id",
        "client_secret": "my_client_secret",
        "verify_ssl": "false"
    }
    cmd = ["looker-cli", "group", "list"]
    expected = [
        "looker-cli",
        "--host", "mylooker.com",
        "--client-id", "my_client_id",
        "--client-secret", "my_client_secret",
        "--verify-ssl=false",
        "group", "list"
    ]
    assert inject_auth_flags(cmd, creds) == expected


def test_inject_auth_flags_no_creds():
    creds = {}
    cmd = ["looker-cli", "group", "list"]
    assert inject_auth_flags(cmd, creds) == cmd
