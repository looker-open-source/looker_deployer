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

import json
import pytest
from types import SimpleNamespace
from unittest.mock import call

from looker_deployer.commands import deploy_role_to_group
from looker_deployer.commands import deploy_groups
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_role_to_group.run_cli_command")


def test_get_filtered_roles_empty_stdout(mock_run_cli_command):
    mock_run_cli_command.return_value = SimpleNamespace(stdout="   \n   ", stderr="")
    creds = {"base_url": "test"}
    roles = deploy_role_to_group.get_filtered_roles(creds)
    assert roles == []


def test_get_filtered_roles_single_namespace_not_list(mock_run_cli_command):
    role_obj = {"name": "Admin", "id": 9}
    mock_run_cli_command.return_value = SimpleNamespace(stdout=json.dumps(role_obj), stderr="")
    creds = {"base_url": "test"}
    roles = deploy_role_to_group.get_filtered_roles(creds)
    assert len(roles) == 1
    assert roles[0].name == "Admin"
    assert roles[0].id == 9


def test_get_filtered_roles_unexpected_primitive(mock_run_cli_command):
    mock_run_cli_command.return_value = SimpleNamespace(stdout="12345", stderr="")
    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_role_to_group.get_filtered_roles(creds)
    assert "Unexpected JSON structure" in str(exc_info.value)


def test_write_role_to_group_role_group_missing_fields(mock_run_cli_command, mocker):
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

    source_role_groups = [
        {"id": 5},               # missing name
        {"name": "Taco"},        # missing id
        {"name": "Taco", "id": 1}  # complete
    ]

    def sub_run_side_effect(cmd, **kwargs):
        if "role_groups" in cmd:
            return SimpleNamespace(stdout=json.dumps(source_role_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = sub_run_side_effect

    with pytest.raises(AttributeError):
        deploy_role_to_group.write_role_to_group(source_creds, target_creds)


def test_write_role_to_group_target_group_missing_fields(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    source_roles = [SimpleNamespace(name="Explorer", id=1)]
    target_roles = [SimpleNamespace(name="Explorer", id=10)]
    target_groups = [SimpleNamespace(id=101)]
    source_role_groups = [{"name": "Taco", "id": 1}]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    def sub_run_side_effect(cmd, **kwargs):
        if "role_groups" in cmd:
            return SimpleNamespace(stdout=json.dumps(source_role_groups), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = sub_run_side_effect

    with pytest.raises(AttributeError):
        deploy_role_to_group.write_role_to_group(source_creds, target_creds)


def test_write_role_to_group_target_roles_empty_or_none(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    source_roles = [SimpleNamespace(name="Explorer", id=1)]
    target_roles = []
    target_groups = [SimpleNamespace(name="Taco", id=101)]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    deploy_role_to_group.write_role_to_group(source_creds, target_creds)
    mock_run_cli_command.assert_not_called()


def test_write_role_to_group_subprocess_list_fails(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    source_roles = [
        SimpleNamespace(name="Explorer", id=1),
        SimpleNamespace(name="Viewer", id=2)
    ]
    target_roles = [
        SimpleNamespace(name="Explorer", id=10),
        SimpleNamespace(name="Viewer", id=20)
    ]
    target_groups = [SimpleNamespace(name="Taco", id=101)]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    def sub_run_side_effect(cmd, **kwargs):
        if "role_groups" in cmd:
            role_id = cmd[-1]
            if role_id == "1":
                raise LookerCLIError("cmd", 1, "", "Error listing groups")
            return SimpleNamespace(stdout=json.dumps([{"name": "Taco", "id": 1}]), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = sub_run_side_effect

    deploy_role_to_group.write_role_to_group(source_creds, target_creds)

    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "role", "role_groups", "1"], creds=source_creds, text=True),
        call(["looker-cli", "api", "role", "role_groups", "2"], creds=source_creds, text=True),
        call(["looker-cli", "api", "role", "set_role_groups", "20", "-"], creds=target_creds, text=True, input="[101]")
    ])


def test_write_role_to_group_subprocess_set_fails(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    source_roles = [
        SimpleNamespace(name="Explorer", id=1),
        SimpleNamespace(name="Viewer", id=2)
    ]
    target_roles = [
        SimpleNamespace(name="Explorer", id=10),
        SimpleNamespace(name="Viewer", id=20)
    ]
    target_groups = [SimpleNamespace(name="Taco", id=101)]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    def sub_run_side_effect(cmd, **kwargs):
        if "role_groups" in cmd:
            return SimpleNamespace(stdout=json.dumps([{"name": "Taco", "id": 1}]), stderr="")
        if "set_role_groups" in cmd:
            role_id = cmd[-2]
            if role_id == "10":
                raise LookerCLIError("cmd", 1, "", "Error setting groups")
            return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = sub_run_side_effect

    deploy_role_to_group.write_role_to_group(source_creds, target_creds)

    mock_run_cli_command.assert_has_calls([
        call(["looker-cli", "api", "role", "role_groups", "1"], creds=source_creds, text=True),
        call(["looker-cli", "api", "role", "set_role_groups", "10", "-"], creds=target_creds, text=True, input="[101]"),
        call(["looker-cli", "api", "role", "role_groups", "2"], creds=source_creds, text=True),
        call(["looker-cli", "api", "role", "set_role_groups", "20", "-"], creds=target_creds, text=True, input="[101]")
    ])


def test_main_multiple_targets_one_fails(mocker):
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_role_to_group.build_creds")
    mock_write = mocker.patch("looker_deployer.commands.deploy_role_to_group.write_role_to_group")

    mock_build_creds.side_effect = lambda ini, name: {f"{name}_creds": "true"}

    def write_side_effect(source, target, pattern):
        if target == {"target_1_creds": "true"}:
            raise RuntimeError("Target 1 is down!")
        return

    mock_write.side_effect = write_side_effect

    args = SimpleNamespace(
        debug=False,
        ini="test.ini",
        source="source_env",
        target=["target_1", "target_2"],
        pattern=None
    )

    with pytest.raises(RuntimeError) as exc_info:
        deploy_role_to_group.main(args)

    assert "Target 1 is down!" in str(exc_info.value)

    mock_write.assert_has_calls([
        call({"source_env_creds": "true"}, {"target_1_creds": "true"}, None)
    ])
    assert mock_write.call_count == 1


def test_write_role_to_group_huge_scale(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_role_to_group.get_filtered_roles")
    mocker.patch("looker_deployer.commands.deploy_groups.get_filtered_groups")

    num_roles = 500
    source_roles = [SimpleNamespace(name=f"Role_{i}", id=i) for i in range(num_roles)]
    target_roles = [SimpleNamespace(name=f"Role_{i}", id=i + 1000) for i in range(num_roles)]
    target_groups = [SimpleNamespace(name=f"Group_{i}", id=i + 10000) for i in range(1000)]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    deploy_role_to_group.get_filtered_roles.side_effect = lambda creds, pattern=None: (
        source_roles if creds == source_creds else target_roles
    )
    deploy_groups.get_filtered_groups.return_value = target_groups

    def sub_run_side_effect(cmd, **kwargs):
        if "role_groups" in cmd:
            role_id = int(cmd[-1])
            return SimpleNamespace(stdout=json.dumps([{"name": f"Group_{role_id}", "id": role_id}]), stderr="")
        return SimpleNamespace(stdout="", stderr="")

    mock_run_cli_command.side_effect = sub_run_side_effect

    deploy_role_to_group.write_role_to_group(source_creds, target_creds)

    assert mock_run_cli_command.call_count == 1000


def test_get_filtered_roles_invalid_regex(mock_run_cli_command):
    role_list = [
        {"name": "Taco", "id": 1},
        {"name": "Burrito", "id": 2}
    ]
    mock_run_cli_command.return_value = SimpleNamespace(stdout=json.dumps(role_list), stderr="")
    creds = {"base_url": "test"}
    import re
    with pytest.raises(re.error):
        deploy_role_to_group.get_filtered_roles(creds, pattern="[")


def test_write_role_to_group_subprocess_raises_exception(mock_run_cli_command, mocker):
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

    mock_run_cli_command.side_effect = OSError("Subprocess failed unexpectedly")

    with pytest.raises(OSError) as exc_info:
        deploy_role_to_group.write_role_to_group(source_creds, target_creds)
    assert "Subprocess failed unexpectedly" in str(exc_info.value)
