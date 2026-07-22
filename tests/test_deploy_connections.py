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
from looker_deployer.commands import deploy_connections
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_connections.run_cli_command")


def test_get_filtered_connections(mock_run_cli_command):
    mock_res = MagicMock()
    mock_res.stdout = '[{"name": "Taco"}, {"name": "Burrito"}]'
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "https://mylooker.com"}
    conns = deploy_connections.get_filtered_connections(creds)

    assert conns == [{"name": "Taco"}, {"name": "Burrito"}]
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "connection", "all_connections"],
        creds=creds,
        capture_output=True,
        text=True,
        check=True
    )


def test_get_filtered_connections_filter(mock_run_cli_command):
    mock_res = MagicMock()
    mock_res.stdout = '[{"name": "Taco"}, {"name": "Burrito"}]'
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "https://mylooker.com"}
    conns = deploy_connections.get_filtered_connections(creds, "Burrito")

    assert conns == [{"name": "Burrito"}]
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "connection", "all_connections"],
        creds=creds,
        capture_output=True,
        text=True,
        check=True
    )


@pytest.fixture
def mock_temp_file(mocker):
    mock_file = mocker.MagicMock()
    mock_file.name = "mocked_temp_file.json"
    mock_named_temp = mocker.patch("looker_deployer.commands.deploy_connections.tempfile.NamedTemporaryFile")
    mock_named_temp.return_value.__enter__.return_value = mock_file
    return mock_named_temp, mock_file


@pytest.fixture
def mock_json_dump(mocker):
    return mocker.patch("looker_deployer.commands.deploy_connections.json.dump")


@pytest.fixture
def mock_os_remove(mocker):
    return mocker.patch("looker_deployer.commands.deploy_connections.os.remove")


def test_write_connections(mock_run_cli_command, mock_temp_file, mock_os_remove, mock_json_dump):
    mock_named_temp, mock_file = mock_temp_file
    conn_list = [{"name": "Taco"}]
    creds = {"base_url": "https://mylooker.com"}

    deploy_connections.write_connections(conn_list, creds)

    mock_named_temp.assert_called_once_with(mode="w", delete=False)
    mock_json_dump.assert_called_once_with(conn_list[0], mock_file)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "connection", "import", "mocked_temp_file.json"],
        creds=creds,
        check=True
    )
    mock_os_remove.assert_called_once_with("mocked_temp_file.json")


def test_write_connections_with_password(mock_run_cli_command, mock_temp_file, mock_os_remove, mock_json_dump):
    mock_named_temp, mock_file = mock_temp_file
    conn_list = [{"name": "Taco"}]
    db_config = {"Taco": "Cat"}
    creds = {"base_url": "https://mylooker.com"}

    deploy_connections.write_connections(conn_list, creds, db_config)

    assert conn_list[0]["password"] == "Cat"
    mock_named_temp.assert_called_once_with(mode="w", delete=False)
    mock_json_dump.assert_called_once_with(conn_list[0], mock_file)
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "connection", "import", "mocked_temp_file.json"],
        creds=creds,
        check=True
    )
    mock_os_remove.assert_called_once_with("mocked_temp_file.json")


def test_send_connections(mocker):
    mock_get = mocker.patch("looker_deployer.commands.deploy_connections.get_filtered_connections")
    mock_write = mocker.patch("looker_deployer.commands.deploy_connections.write_connections")

    deploy_connections.send_connections("source_creds", "target_creds", "pattern", {"Taco": "Cat"})

    mock_get.assert_called_once_with("source_creds", "pattern")
    mock_write.assert_called_once_with(mock_get.return_value, "target_creds", {"Taco": "Cat"})


def test_main(mocker):
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_connections.parse_ini.build_creds")
    mock_send = mocker.patch("looker_deployer.commands.deploy_connections.send_connections")

    args = mocker.MagicMock()
    args.debug = True
    args.include_password = False
    args.ini = "looker.ini"
    args.source = "env1"
    args.target = ["env2", "env3"]
    args.pattern = "pattern"

    mock_build_creds.side_effect = [{"base_url": "1"}, {"base_url": "2"}, {"base_url": "3"}]

    deploy_connections.main(args)

    mock_build_creds.assert_has_calls([
        mocker.call("looker.ini", "env1"),
        mocker.call("looker.ini", "env2"),
        mocker.call("looker.ini", "env3")
    ])

    mock_send.assert_has_calls([
        mocker.call({"base_url": "1"}, {"base_url": "2"}, "pattern", None),
        mocker.call({"base_url": "1"}, {"base_url": "3"}, "pattern", None)
    ])


def test_main_with_password(mocker):
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_connections.parse_ini.build_creds")
    mock_send = mocker.patch("looker_deployer.commands.deploy_connections.send_connections")
    mock_read_ini = mocker.patch("looker_deployer.commands.deploy_connections.parse_ini.read_ini")
    mock_read_ini.return_value = {"Databases": {"Taco": "Cat"}}

    args = mocker.MagicMock()
    args.debug = False
    args.include_password = True
    args.ini = "looker.ini"
    args.source = "env1"
    args.target = ["env2"]
    args.pattern = None

    mock_build_creds.side_effect = [{"base_url": "1"}, {"base_url": "2"}]

    deploy_connections.main(args)

    mock_build_creds.assert_has_calls([
        mocker.call("looker.ini", "env1"),
        mocker.call("looker.ini", "env2")
    ])

    mock_send.assert_called_once_with({"base_url": "1"}, {"base_url": "2"}, None, {"Taco": "Cat"})


def test_write_connections_cleanup_on_subprocess_error(mock_run_cli_command, mock_temp_file, mock_os_remove, mock_json_dump):
    mock_named_temp, mock_file = mock_temp_file
    conn_list = [{"name": "Taco"}]
    creds = {"base_url": "https://mylooker.com"}

    mock_run_cli_command.side_effect = LookerCLIError("cmd", 1, "out", "err")

    with pytest.raises(LookerCLIError):
        deploy_connections.write_connections(conn_list, creds)

    mock_os_remove.assert_called_once_with("mocked_temp_file.json")
