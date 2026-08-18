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
from types import SimpleNamespace
from unittest.mock import call

from looker_deployer.commands import deploy_role_to_group
from looker_deployer.commands import deploy_groups


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_role_to_group.run_cli_command")


def test_write_role_to_group_empty_groups_list(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    source_roles = [SimpleNamespace(name="Explorer", id=1)]
    target_roles = [SimpleNamespace(name="Explorer", id=10)]
    target_groups = [SimpleNamespace(name="Taco", id=101)]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    def sub_run_side_effect(cmd, **kwargs):
        if "role_groups" in cmd:
            return SimpleNamespace(stdout="", stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = sub_run_side_effect

    deploy_role_to_group.write_role_to_group(source_creds, target_creds)

    for c in mock_run_cli_command.call_args_list:
        assert "set_role_groups" not in c[0][0]


def test_write_role_to_group_json_empty_array(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    source_roles = [SimpleNamespace(name="Explorer", id=1)]
    target_roles = [SimpleNamespace(name="Explorer", id=10)]
    target_groups = [SimpleNamespace(name="Taco", id=101)]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    def sub_run_side_effect(cmd, **kwargs):
        if "role_groups" in cmd:
            return SimpleNamespace(stdout="[]", stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = sub_run_side_effect

    deploy_role_to_group.write_role_to_group(source_creds, target_creds)

    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "role", "role_groups", "1"], creds=source_creds, text=True),
        call(["looker-cli", "api", "role", "set_role_groups", "10", "-"], creds=target_creds, text=True, input="[]")
    ])


def test_main(mocker):
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_role_to_group.build_creds")
    mock_write = mocker.patch("looker_deployer.commands.deploy_role_to_group.write_role_to_group")

    mock_build_creds.side_effect = lambda ini, name: {f"{name}_creds": "true"}

    args = SimpleNamespace(
        debug=True,
        ini="test.ini",
        source="source_env",
        target=["target_1", "target_2"],
        pattern="test_pattern"
    )

    deploy_role_to_group.main(args)

    assert mock_build_creds.call_count == 3
    mock_build_creds.assert_has_calls([
        call("test.ini", "source_env"),
        call("test.ini", "target_1"),
        call("test.ini", "target_2")
    ], any_order=True)

    mock_write.assert_has_calls([
        call({"source_env_creds": "true"}, {"target_1_creds": "true"}, "test_pattern"),
        call({"source_env_creds": "true"}, {"target_2_creds": "true"}, "test_pattern")
    ])
