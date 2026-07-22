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
import subprocess
from unittest.mock import patch, mock_open
from pathlib import Path
from looker_deployer.commands import deploy_content_export
from looker_deployer.utils.exceptions import LookerCLIError
from types import SimpleNamespace


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")


def test_export_spaces_subprocess_error(mock_run_cli_command):
    mock_run_cli_command.side_effect = LookerCLIError("looker-cli", 1, "", "")
    creds = {"base_url": "test"}

    with pytest.raises(LookerCLIError):
        deploy_content_export.export_spaces("1", creds, "foo/bar", False)


def test_export_content_debug(mock_run_cli_command):
    creds = {"base_url": "test"}
    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()) as mocked_file:
        deploy_content_export.export_content("dashboard", "1", creds, "foo/bar", True)

        mock_run_cli_command.assert_called_with([
            "looker-cli",
            "dashboard",
            "cat",
            "1"
        ], stdout=mocked_file(), stderr=subprocess.PIPE, creds=creds, check=True, text=True)


def test_export_content_subprocess_error(mock_run_cli_command):
    mock_run_cli_command.side_effect = LookerCLIError("looker-cli", 1, "", "")
    creds = {"base_url": "test"}

    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()):
        with pytest.raises(LookerCLIError):
            deploy_content_export.export_content("dashboard", "1", creds, "foo/bar", False)


def test_recurse_folders_debug(mock_run_cli_command):
    creds = {"base_url": "test"}
    mock_result = SimpleNamespace(stdout='{"name": "foo", "parent_id": null}', stderr="")
    mock_run_cli_command.return_value = mock_result

    folder = deploy_content_export.recurse_folders("1", [], creds, True)
    assert folder == ["foo"]
    mock_run_cli_command.assert_called_with(
        ["looker-cli", "folder", "cat", "1"],
        creds=creds,
        check=True,
        capture_output=True,
        text=True
    )


def test_recurse_folders_recursive(mock_run_cli_command, mocker):
    creds = {"base_url": "test"}

    mock_res_child = SimpleNamespace(stdout='{"name": "child", "parent_id": "parent"}', stderr="")
    mock_res_parent = SimpleNamespace(stdout='{"name": "parent", "parent_id": null}', stderr="")

    mock_run_cli_command.side_effect = [mock_res_child, mock_res_parent]

    folder_list = []
    folder = deploy_content_export.recurse_folders("child", folder_list, creds, False)
    assert folder == ["child", "parent"]


def test_send_export_dashboards(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.export_content")
    mocker.patch("pathlib.Path.mkdir")

    creds = {"base_url": "test"}
    deploy_content_export.send_export(creds, "./foo/bar", dashboards=["1", "2"], debug=False)

    assert deploy_content_export.export_content.call_count == 2
    deploy_content_export.export_content.assert_any_call("dashboard", "1", creds, "foo/bar", False)
    deploy_content_export.export_content.assert_any_call("dashboard", "2", creds, "foo/bar", False)


def test_send_export_looks(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.export_content")
    mocker.patch("pathlib.Path.mkdir")

    creds = {"base_url": "test"}
    deploy_content_export.send_export(creds, "./foo/bar", looks=["3"], debug=True)

    deploy_content_export.export_content.assert_called_once_with("look", "3", creds, "foo/bar", True)


def test_main_export_debug(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.logger.setLevel")
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_content_export.build_creds")
    mocker.patch("looker_deployer.commands.deploy_content_export.send_export")

    mock_build_creds.return_value = {"base_url": "test"}

    args = SimpleNamespace(
        debug=True,
        ini="ini",
        env="env",
        local_target="./foo/bar",
        folders=["1"],
        dashboards=None,
        looks=None
    )

    deploy_content_export.main(args)

    import logging
    deploy_content_export.logger.setLevel.assert_called_once_with(logging.DEBUG)
    deploy_content_export.send_export.assert_called_once_with(
        {"base_url": "test"}, "./foo/bar", ["1"], None, None, True
    )
