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


def test_write_connections(mock_run_cli_command):
    import json
    conn_list = [{"name": "Taco"}]
    creds = {"base_url": "https://mylooker.com"}

    deploy_connections.write_connections(conn_list, creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "connection", "import", "-"],
        creds=creds,
        check=True,
        input=json.dumps(conn_list[0]),
        text=True
    )


def test_write_connections_with_password(mock_run_cli_command):
    import json
    conn_list = [{"name": "Taco"}]
    db_config = {"Taco": "Cat"}
    creds = {"base_url": "https://mylooker.com"}

    deploy_connections.write_connections(conn_list, creds, db_config)

    assert conn_list[0]["password"] == "Cat"
    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "connection", "import", "-"],
        creds=creds,
        check=True,
        input=json.dumps(conn_list[0]),
        text=True
    )


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
