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
from looker_deployer.commands import deploy_code
import requests
from looker_deployer.utils.exceptions import LookerCLIError

CONFIG_NO_EXCLUDE = {
    "instances": [
        {
            "name": "foo",
            "endpoint": "bar",
            "spoke_project": "baz"
        }
    ],
    "hub_project": "bosh"
}

CONFIG_WITH_EXCLUDE = {
    "instances": [
        {
            "name": "foo",
            "endpoint": "bar",
            "spoke_project": "baz"
        },
        {
            "name": "taco",
            "endpoint": "burrito",
            "spoke_project": "bananna"
        }
    ],
    "hub_project": "bosh",
    "hub_deploy_exclude": ["taco"]
}

GOOD_RESPONSE = requests.Response()
GOOD_RESPONSE.status_code = 200
BAD_RESPONSE = requests.Response()
BAD_RESPONSE.status_code = 500
RESP_JSON = {
    "operations": [
        {"results": ["success"]}
    ]
}


def test_parse_hub_targets():

    targets = deploy_code.parse_hub_targets(CONFIG_NO_EXCLUDE)
    assert targets == ["foo"]


def test_parse_hub_targets_with_exclude():
    targets = deploy_code.parse_hub_targets(CONFIG_WITH_EXCLUDE)
    assert targets == ["foo"]


def test_parse_spoke_config():
    spoke_config = deploy_code.parse_spoke_config("foo", CONFIG_NO_EXCLUDE)
    assert spoke_config == {"name": "foo", "endpoint": "bar", "spoke_project": "baz"}


def test_parse_spoke_config_no_val():
    with pytest.raises(IndexError):
        deploy_code.parse_spoke_config("flurb", CONFIG_NO_EXCLUDE)


def test_parse_hub_excludes():
    test_config = CONFIG_NO_EXCLUDE
    deploy_code.parse_hub_excludes(test_config, ["taco"])
    assert test_config["hub_deploy_exclude"] == ["taco"]


def test_parse_hub_excludes_with_exclude():
    test_config = CONFIG_WITH_EXCLUDE
    deploy_code.parse_hub_excludes(test_config, ["foo"])
    assert test_config["hub_deploy_exclude"] == ["taco", "foo"]


def test_deploy_code(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_code.run_cli_command")
    mocker.patch("looker_deployer.commands.deploy_code.get_access_token", return_value="mocked_token")
    creds = {"base_url": "test"}
    deploy_code.deploy_code("foo", creds)

    assert mock_run.call_count == 2
    calls = mock_run.call_args_list

    token_creds = {"base_url": "test", "verify_ssl": None, "token": "mocked_token"}

    assert calls[0][0][0] == ["looker-cli", "api", "session", "update_session", "-"]
    assert calls[0][1].get("creds") == token_creds
    assert calls[0][1].get("input") == '{"workspace_id": "dev"}'

    assert calls[1][0][0] == ["looker-cli", "project", "deploy", "foo"]
    assert calls[1][1].get("creds") == token_creds


def test_deploy_code_assertion_error(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_code.run_cli_command")
    mocker.patch("looker_deployer.commands.deploy_code.get_access_token", return_value="mocked_token")

    def side_effect(cmd, *args, **kwargs):
        if "update_session" in cmd:
            return mocker.MagicMock()
        elif "deploy" in cmd:
            raise LookerCLIError("cmd", 1, "out", "error")
        return mocker.MagicMock()

    mock_run.side_effect = side_effect
    with pytest.raises(RuntimeError, match="Deployment failed due to CLI error"):
        deploy_code.deploy_code("foo", {"base_url": "test"})


def test_deploy_code_file_not_found(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_code.run_cli_command")
    mocker.patch("looker_deployer.commands.deploy_code.get_access_token", return_value="mocked_token")

    def side_effect(cmd, *args, **kwargs):
        if "update_session" in cmd:
            return mocker.MagicMock()
        elif "deploy" in cmd:
            raise FileNotFoundError("No such file or directory: 'looker-cli'")
        return mocker.MagicMock()

    mock_run.side_effect = side_effect
    with pytest.raises(FileNotFoundError, match="No such file or directory"):
        deploy_code.deploy_code("foo", {"base_url": "test"})


def test_deploy_code_invalid_credentials(mocker):
    mocker.patch("looker_deployer.commands.deploy_code.get_access_token", side_effect=Exception("Error: Unauthorized"))
    with pytest.raises(RuntimeError) as exc_info:
        deploy_code.deploy_code("foo", {"base_url": "test"})
    assert "Unauthorized" in str(exc_info.value.__cause__)
