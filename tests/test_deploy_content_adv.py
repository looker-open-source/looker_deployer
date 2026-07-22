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
from unittest.mock import MagicMock
import json
import tempfile
import shutil
import logging
import os
from looker_deployer.commands import deploy_content
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_content.run_cli_command")


def test_get_space_ids_from_name_debug(mock_run_cli_command):
    mock_res = MagicMock()
    mock_res.stdout = '[{"id": 42}]'
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    id_list = deploy_content.get_space_ids_from_name("foo", "0", creds, True)
    assert id_list == ["42"]
    mock_run_cli_command.assert_called_with(
        ["looker-cli", "api", "folder", "search_folders", "--name", "foo", "--parent_id", "0"],
        creds=creds,
        check=True,
        capture_output=True,
        text=True
    )


def test_get_space_ids_from_name_subprocess_error(mock_run_cli_command, mocker):
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "some stdout", "some error")
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.get_space_ids_from_name("foo", "0", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli folder search failed",
        extra={"stdout": "some stdout", "stderr": "some error"}
    )


def test_get_space_ids_from_name_json_decode_error(mock_run_cli_command):
    mock_res = MagicMock()
    mock_res.stdout = 'invalid json'
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    with pytest.raises(json.JSONDecodeError):
        deploy_content.get_space_ids_from_name("foo", "0", creds, False)


@pytest.mark.parametrize("folder_name", ["Embed Groups", "Users", "Embed Users"])
def test_get_space_ids_from_name_special_folders(mock_run_cli_command, folder_name):
    mock_res = MagicMock()
    mock_res.stdout = '[{"id": 100}]'
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    id_list = deploy_content.get_space_ids_from_name(folder_name, "0", creds, False)
    assert id_list == ["100"]
    mock_run_cli_command.assert_called_with(
        ["looker-cli", "api", "folder", "search_folders", "--name", folder_name],
        creds=creds,
        check=True,
        capture_output=True,
        text=True
    )


def test_create_or_return_space_slash_substitution(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name")
    deploy_content.get_space_ids_from_name.side_effect = [[], ["42"]]

    creds = {"base_url": "test"}
    target_id = deploy_content.create_or_return_space("foo/bar", "1", creds)
    assert target_id == "42"
    assert deploy_content.get_space_ids_from_name.call_count == 2
    deploy_content.get_space_ids_from_name.assert_any_call("foo/bar", "1", creds, False)
    deploy_content.get_space_ids_from_name.assert_any_call("foo\u2215bar", "1", creds, False)


def test_create_or_return_space_users_folder_prevent_create(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=[])
    creds = {"base_url": "test"}
    with pytest.raises(AssertionError):
        deploy_content.create_or_return_space("foo", "2", creds)


def test_create_or_return_space_debug(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=[])
    mock_res = MagicMock()
    mock_res.stdout = '{"id": 42}'
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    target_id = deploy_content.create_or_return_space("foo", "5", creds, True)
    assert target_id == "42"
    mock_run_cli_command.assert_called_with(
        ["looker-cli", "api", "folder", "create_folder", "-"],
        input='{"name": "foo", "parent_id": "5"}',
        creds=creds,
        check=True,
        capture_output=True,
        text=True
    )


def test_create_or_return_space_subprocess_error(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=[])
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "some create stdout", "some create error")
    mock_logger = mocker.patch("looker_deployer.commands.deploy_content.logger")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.create_or_return_space("foo", "5", creds, False)

    mock_logger.error.assert_called_once_with(
        "looker-cli api folder create_folder failed",
        extra={"stdout": "some create stdout", "stderr": "some create error"}
    )


def test_create_or_return_space_json_decode_error(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name", return_value=[])
    mock_res = MagicMock()
    mock_res.stdout = 'invalid json'
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    with pytest.raises(json.JSONDecodeError):
        deploy_content.create_or_return_space("foo", "5", creds, False)


def test_import_content_subprocess_error(mock_run_cli_command):
    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "out", "err")

    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError):
        deploy_content.import_content("dashboard", "tacocat.json", "42", creds, False)


def test_deploy_space_recursive(mocker):
    mocker.patch("os.listdir")
    mocker.patch("os.path.isfile")
    mocker.patch("os.path.isdir")

    def mock_listdir(path):
        if path.rstrip(os.sep) == "Foo/Shared/Bar":
            return ["Look_test", "ChildDir"]
        return []
    os.listdir.side_effect = mock_listdir

    def mock_isfile(path):
        return "Look_test" in path
    os.path.isfile.side_effect = mock_isfile

    def mock_isdir(path):
        return "ChildDir" in path
    os.path.isdir.side_effect = mock_isdir

    mocker.patch("looker_deployer.commands.deploy_content.build_spaces", return_value="42")
    mocker.patch("looker_deployer.commands.deploy_content.import_content")

    spy = mocker.spy(deploy_content, "deploy_space")
    creds = {"base_url": "test"}

    deploy_content.deploy_space("Foo/Shared/Bar", creds, True, "Shared", False)

    assert spy.call_count == 2
    spy.assert_any_call("Foo/Shared/Bar", creds, True, "Shared", False)
    spy.assert_any_call("Foo/Shared/Bar/ChildDir/", creds, True, "Shared", False)


def test_send_content_spaces_no_override(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.deploy_space")
    creds = {"base_url": "test"}
    deploy_content.send_content(creds, target_folder=None, spaces=["s1", "s2"], recursive=True, debug=True, target_base="Shared")

    assert deploy_content.deploy_space.call_count == 2
    deploy_content.deploy_space.assert_any_call("s1", creds, True, "Shared", True)
    deploy_content.deploy_space.assert_any_call("s2", creds, True, "Shared", True)


def test_send_content_spaces_with_override(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.deploy_space")
    mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir = mocker.MagicMock()
    mock_temp_dir.__enter__.return_value = "/tmp/dir"
    tempfile.TemporaryDirectory.return_value = mock_temp_dir
    mocker.patch("shutil.copytree")

    creds = {"base_url": "test"}
    deploy_content.send_content(creds, target_folder="override", spaces=["s1"], recursive=True, debug=True, target_base="Shared")

    shutil.copytree.assert_called_once_with("s1", "/tmp/dir/override")
    deploy_content.deploy_space.assert_called_once_with("/tmp/dir/override", creds, True, "Shared", True)


def test_send_content_dashboards_no_override(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.deploy_content")
    creds = {"base_url": "test"}
    deploy_content.send_content(creds, target_folder=None, dashboards=["dash1.json"], recursive=False, debug=True, target_base="Shared")

    deploy_content.deploy_content.assert_called_once_with("dashboard", "dash1.json", creds, "Shared", True)


def test_send_content_dashboards_with_override(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.deploy_content")
    mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir = mocker.MagicMock()
    mock_temp_dir.__enter__.return_value = "/tmp/dir"
    tempfile.TemporaryDirectory.return_value = mock_temp_dir
    mocker.patch("os.makedirs")
    mocker.patch("shutil.copy")
    mocker.patch("os.listdir", return_value=["dash1.json"])

    creds = {"base_url": "test"}
    deploy_content.send_content(creds, target_folder="override", dashboards=["path/to/dash1.json"], recursive=False, debug=True, target_base="Shared")

    os.makedirs.assert_called_once_with("/tmp/dir/override")
    shutil.copy.assert_called_once_with("path/to/dash1.json", "/tmp/dir/override")
    deploy_content.deploy_content.assert_called_once_with("dashboard", "/tmp/dir/override/dash1.json", creds, "Shared", True)


def test_send_content_looks_no_override(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.deploy_content")
    creds = {"base_url": "test"}
    deploy_content.send_content(creds, target_folder=None, looks=["look1.json"], recursive=False, debug=True, target_base="Shared")

    deploy_content.deploy_content.assert_called_once_with("look", "look1.json", creds, "Shared", True)


def test_send_content_looks_with_override(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.deploy_content")
    mocker.patch("tempfile.TemporaryDirectory")
    mock_temp_dir = mocker.MagicMock()
    mock_temp_dir.__enter__.return_value = "/tmp/dir"
    tempfile.TemporaryDirectory.return_value = mock_temp_dir
    mocker.patch("os.makedirs")
    mocker.patch("shutil.copy")
    mocker.patch("os.listdir", return_value=["look1.json"])

    creds = {"base_url": "test"}
    deploy_content.send_content(creds, target_folder="override", looks=["path/to/look1.json"], recursive=False, debug=True, target_base="Shared")

    os.makedirs.assert_called_once_with("/tmp/dir/override")
    shutil.copy.assert_called_once_with("path/to/look1.json", "/tmp/dir/override")
    deploy_content.deploy_content.assert_called_once_with("look", "/tmp/dir/override/look1.json", creds, "Shared", True)


def test_main_debug(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.logger.setLevel")
    mocker.patch("looker_deployer.commands.deploy_content.send_content")
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_content.build_creds", return_value={"base_url": "test"})

    args = mocker.MagicMock()
    args.debug = True
    args.ini = "ini"
    args.env = "env"
    args.target_folder = "my_target_folder"
    args.folders = ["f1"]
    args.dashboards = None
    args.looks = None
    args.recursive = False

    deploy_content.main(args)

    deploy_content.logger.setLevel.assert_called_once_with(logging.DEBUG)
    assert args.target_folder == "my_target_folder/"
    assert args.target_base == "my_target_folder"

    mock_build_creds.assert_called_once_with("ini", "env")
    deploy_content.send_content.assert_called_once_with(
        {"base_url": "test"}, "my_target_folder/", ["f1"], None, None, False, True, "my_target_folder"
    )


def test_main_no_target_folder(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.logger.setLevel")
    mocker.patch("looker_deployer.commands.deploy_content.send_content")
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_content.build_creds", return_value={"base_url": "test"})

    args = mocker.MagicMock()
    args.debug = False
    args.ini = "ini"
    args.env = "env"
    args.target_folder = None
    args.folders = ["f1"]
    args.dashboards = None
    args.looks = None
    args.recursive = False

    deploy_content.main(args)

    assert args.target_base == "Shared"
    mock_build_creds.assert_called_once_with("ini", "env")
    deploy_content.send_content.assert_called_once_with(
        {"base_url": "test"}, None, ["f1"], None, None, False, False, "Shared"
    )
