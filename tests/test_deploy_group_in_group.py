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
import subprocess
from types import SimpleNamespace
from looker_deployer.commands import deploy_group_in_group


def test_get_filtered_groups(mocker):
    group_list = [
        {"name": "Taco", "externally_managed": False},
        {"name": "Burrito", "externally_managed": False}
    ]
    mock_run = mocker.patch("looker_deployer.commands.deploy_group_in_group.run_cli_command")
    mock_run.return_value = subprocess.CompletedProcess(
        args=["looker-cli", "api", "group", "all_groups"],
        returncode=0,
        stdout=json.dumps(group_list)
    )

    creds = {"base_url": "test"}
    groups = deploy_group_in_group.get_filtered_groups(creds)

    mock_run.assert_called_once_with(
        ["looker-cli", "api", "group", "all_groups"],
        text=True,
        creds=creds
    )
    assert len(groups) == 2
    assert groups[0].name == "Taco"
    assert groups[1].name == "Burrito"


def test_get_filtered_groups_filter(mocker):
    group_list = [
        {"name": "Taco", "externally_managed": False},
        {"name": "Burrito", "externally_managed": False}
    ]
    mock_run = mocker.patch("looker_deployer.commands.deploy_group_in_group.run_cli_command")
    mock_res = subprocess.CompletedProcess(
        args=["looker-cli", "api", "group", "all_groups"],
        returncode=0,
        stdout=json.dumps(group_list)
    )
    mock_run.return_value = mock_res

    creds = {"base_url": "test"}
    groups = deploy_group_in_group.get_filtered_groups(creds, "Burrito")
    assert len(groups) == 1
    assert groups[0].name == "Burrito"


def test_write_groups_in_group_new(mocker):
    group_list = [
        {"name": "Taco", "id": 1, "externally_managed": False},
        {"name": "Taco Supreme", "id": 2, "externally_managed": False}
    ]

    mock_run = mocker.patch("looker_deployer.commands.deploy_group_in_group.run_cli_command")
    mock_get_groups = mocker.patch("looker_deployer.commands.deploy_group_in_group.get_filtered_groups")
    mock_get_groups.return_value = [SimpleNamespace(**g) for g in group_list]

    source_creds = {"inst": "source"}
    target_creds = {"inst": "target"}

    def side_effect(args, **kwargs):
        creds = kwargs.get("creds", {})
        if args == ["looker-cli", "api", "group", "all_group_groups", "1"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "2"]:
            if creds == source_creds:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps([{"name": "Taco", "id": 1, "externally_managed": False}]))
            else:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]")
        elif args[:5] == ["looker-cli", "api", "group", "add_group_group"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="")

    mock_run.side_effect = side_effect

    deploy_group_in_group.write_groups_in_group(source_creds, target_creds)

    mock_run.assert_any_call(
        ["looker-cli", "api", "group", "add_group_group", "2", "-"],
        text=True,
        creds=target_creds,
        input=json.dumps({"group_id": "1"})
    )


def test_write_groups_in_group_change(mocker):
    group_list = [
        {"name": "Taco", "id": 1, "externally_managed": False},
        {"name": "Taco Supreme", "id": 2, "externally_managed": False},
        {"name": "Chalupa", "id": 3, "externally_managed": False}
    ]

    mock_run = mocker.patch("looker_deployer.commands.deploy_group_in_group.run_cli_command")
    mock_get_groups = mocker.patch("looker_deployer.commands.deploy_group_in_group.get_filtered_groups")
    mock_get_groups.return_value = [SimpleNamespace(**g) for g in group_list]

    source_creds = {"inst": "source"}
    target_creds = {"inst": "target"}

    def side_effect(args, **kwargs):
        creds = kwargs.get("creds", {})
        if args == ["looker-cli", "api", "group", "all_group_groups", "1"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]")
        elif args == ["looker-cli", "api", "group", "all_group_groups", "2"]:
            if creds == source_creds:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]")
            else:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps([{"name": "Taco", "id": 1, "externally_managed": False}]))
        elif args == ["looker-cli", "api", "group", "all_group_groups", "3"]:
            if creds == source_creds:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps([{"name": "Taco", "id": 1, "externally_managed": False}]))
            else:
                return subprocess.CompletedProcess(args=args, returncode=0, stdout="[]")
        elif args[:5] in (["looker-cli", "api", "group", "add_group_group"], ["looker-cli", "api", "group", "delete_group_from_group"]):
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="")

    mock_run.side_effect = side_effect

    deploy_group_in_group.write_groups_in_group(source_creds, target_creds)

    mock_run.assert_any_call(
        ["looker-cli", "api", "group", "delete_group_from_group", "2", "1"],
        text=True,
        creds=target_creds
    )

    mock_run.assert_any_call(
        ["looker-cli", "api", "group", "add_group_group", "3", "-"],
        text=True,
        creds=target_creds,
        input=json.dumps({"group_id": "1"})
    )
