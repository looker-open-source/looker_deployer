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
from unittest.mock import patch, mock_open
from looker_deployer.commands import deploy_content_export
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_content_export.run_cli_command")


def test_adv_export_content_called_process_error(mock_run_cli_command):
    mock_run_cli_command.side_effect = LookerCLIError("looker-cli cat", 1, "", "")
    creds = {"base_url": "test"}

    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()):
        with pytest.raises(LookerCLIError):
            deploy_content_export.export_content("dashboard", "1", creds, "foo/bar", False)


def test_adv_send_export_loops(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.recurse_folders")
    deploy_content_export.recurse_folders.side_effect = [
        ["folderA", "Shared"],
        ["folderB", "Shared"]
    ]
    mocker.patch("pathlib.Path.mkdir")
    mocker.patch("looker_deployer.commands.deploy_content_export.export_spaces")
    mocker.patch("looker_deployer.commands.deploy_content_export.export_content")

    creds = {"base_url": "test"}
    deploy_content_export.send_export(
        creds=creds,
        local_target="./foo/bar",
        folders=["1", "2"],
        dashboards=["3", "4"],
        looks=["5", "6"],
        debug=False
    )

    # Verify recurse_folders was called for each folder
    deploy_content_export.recurse_folders.assert_any_call("1", [], creds, False)
    deploy_content_export.recurse_folders.assert_any_call("2", [], creds, False)

    # Verify export_spaces was called for each folder with reversed paths
    deploy_content_export.export_spaces.assert_any_call("1", creds, "foo/bar/Shared", False)
    deploy_content_export.export_spaces.assert_any_call("2", creds, "foo/bar/Shared", False)

    # Verify export_content called for each dashboard and look
    deploy_content_export.export_content.assert_any_call("dashboard", "3", creds, "foo/bar", False)
    deploy_content_export.export_content.assert_any_call("dashboard", "4", creds, "foo/bar", False)
    deploy_content_export.export_content.assert_any_call("look", "5", creds, "foo/bar", False)
    deploy_content_export.export_content.assert_any_call("look", "6", creds, "foo/bar", False)


def test_adv_send_export_invalid_filesystem_chars(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.recurse_folders")
    deploy_content_export.recurse_folders.return_value = ["subfolder", "folder\0name", "Shared"]

    mocker.patch("looker_deployer.commands.deploy_content_export.export_spaces")

    creds = {"base_url": "test"}
    with pytest.raises((TypeError, OSError, ValueError)):
        deploy_content_export.send_export(
            creds=creds,
            local_target="./foo/bar",
            folders=["1"],
            debug=False
        )
