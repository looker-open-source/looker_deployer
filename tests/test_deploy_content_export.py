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

from unittest.mock import patch, mock_open
from pathlib import Path
import subprocess
from looker_sdk import methods
from looker_deployer.commands import deploy_content_export


class mockSpace:
    name = "foo"
    parent_id = None


class mockSettings:
    base_url = "taco"


class mockAuth:
    settings = mockSettings()


sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")


def test_export_space(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.get_gzr_creds")
    deploy_content_export.get_gzr_creds.return_value = ("foobar.com", "1234", "abc", "xyz", "True")

    mocker.patch("subprocess.run")
    deploy_content_export.export_spaces("1", "env", "ini", "foo/bar", False)
    subprocess.run.assert_called_with([
        "gzr",
        "space",
        "export",
        "1",
        "--dir",
        "foo/bar",
        "--host",
        "foobar.com",
        "--port",
        "1234",
        "--client-id",
        "abc",
        "--client-secret",
        "xyz"
    ])


def test_export_space_debug(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.get_gzr_creds")
    deploy_content_export.get_gzr_creds.return_value = ("foobar.com", "1234", "abc", "xyz", "True")

    mocker.patch("subprocess.run")
    deploy_content_export.export_spaces("1", "env", "ini", "foo/bar", True)
    subprocess.run.assert_called_with([
        "gzr",
        "space",
        "export",
        "1",
        "--dir",
        "foo/bar",
        "--host",
        "foobar.com",
        "--port",
        "1234",
        "--client-id",
        "abc",
        "--client-secret",
        "xyz",
        "--debug"
    ])


def test_export_space_no_verify_ssl(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.get_gzr_creds")
    deploy_content_export.get_gzr_creds.return_value = ("foobar.com", "1234", "abc", "xyz", "False")

    mocker.patch("subprocess.run")
    deploy_content_export.export_spaces("1", "env", "ini", "foo/bar", False)
    subprocess.run.assert_called_with([
        "gzr",
        "space",
        "export",
        "1",
        "--dir",
        "foo/bar",
        "--host",
        "foobar.com",
        "--port",
        "1234",
        "--client-id",
        "abc",
        "--client-secret",
        "xyz",
        "--no-verify-ssl"
    ])


def test_export_space_win(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.get_gzr_creds")
    deploy_content_export.get_gzr_creds.return_value = ("foobar.com", "1234", "abc", "xyz", "True")

    mocker.patch("os.name", "nt")

    mocker.patch("subprocess.run")
    deploy_content_export.export_spaces("1", "env", "ini", "foo/bar", False)
    subprocess.run.assert_called_with([
        "cmd.exe",
        "/c",
        "gzr",
        "space",
        "export",
        "1",
        "--dir",
        "foo/bar",
        "--host",
        "foobar.com",
        "--port",
        "1234",
        "--client-id",
        "abc",
        "--client-secret",
        "xyz"
    ])


def test_recurse_folders(mocker):
    mocker.patch.object(sdk, "space")
    sdk.space.return_value = mockSpace()

    folder = deploy_content_export.recurse_folders("1", [], sdk, False)
    assert folder == ["foo"]


def test_send_export(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.recurse_folders")
    deploy_content_export.recurse_folders.return_value = ["baz", "bosh", "Shared"]

    mocker.patch("pathlib.Path.mkdir")

    mocker.patch("looker_deployer.commands.deploy_content_export.export_spaces")
    deploy_content_export.send_export("sdk", "env", "ini", "./foo/bar", folders="1", debug=False)
    deploy_content_export.export_spaces.assert_called_with("1", "env", "ini", "foo/bar/Shared/bosh", False)


def test_export_dashboard(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.get_gzr_creds")
    deploy_content_export.get_gzr_creds.return_value = ("foobar.com", "1234", "abc", "xyz", "True")

    fake_file_path = Path("foo/bar/dashboard_1.json")
    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()) as mocked_file:
        mocker.patch("subprocess.run")
        deploy_content_export.export_content("dashboard", "1", "env", "ini", "foo/bar", False)

        # assert "foo/bar/dashboard_1.json" opened and on write mode 'w'
        mocked_file.assert_called_once_with(fake_file_path, 'w')


def test_export_look(mocker):
    mocker.patch("looker_deployer.commands.deploy_content_export.get_gzr_creds")
    deploy_content_export.get_gzr_creds.return_value = ("foobar.com", "1234", "abc", "xyz", "True")

    fake_file_path = Path("foo/bar/look_1.json")
    with patch('looker_deployer.commands.deploy_content_export.open', mock_open()) as mocked_file:
        mocker.patch("subprocess.run")
        deploy_content_export.export_content("look", "1", "env", "ini", "foo/bar", False)

        # assert "foo/bar/look_1.json" opened and on write mode 'w'
        mocked_file.assert_called_once_with(fake_file_path, 'w')
