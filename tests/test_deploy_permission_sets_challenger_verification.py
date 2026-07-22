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

import json
import pytest
import random
from types import SimpleNamespace
from looker_deployer.commands import deploy_permission_sets
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_permission_sets.run_cli_command")


def test_write_permission_sets_subprocess_os_error_on_create(mock_run_cli_command, mocker):
    source_permission_sets = [SimpleNamespace(name="Taco", permissions=["see_looks"])]
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[])

    mock_run_cli_command.side_effect = OSError("Command execution failed")

    target_creds = {"base_url": "target"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_permission_sets.write_permission_sets(source_permission_sets, target_creds)
    assert "command not found or execution failed" in str(exc_info.value)


def test_write_permission_sets_subprocess_os_error_on_update(mock_run_cli_command, mocker):
    source_permission_sets = [SimpleNamespace(name="Taco", permissions=["see_looks"])]
    target_permission_sets = [SimpleNamespace(name="Taco", id=1)]
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=target_permission_sets)

    mock_run_cli_command.side_effect = OSError("Command execution failed")

    target_creds = {"base_url": "target"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_permission_sets.write_permission_sets(source_permission_sets, target_creds)
    assert "command not found or execution failed" in str(exc_info.value)


def test_write_permission_sets_subprocess_os_error_on_delete(mock_run_cli_command, mocker):
    source_permission_sets = [SimpleNamespace(name="Taco", permissions=["see_looks"])]
    target_permission_sets = [SimpleNamespace(name="Taco", id=1), SimpleNamespace(name="Taco", id=2)]
    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=target_permission_sets)

    run_count = 0

    def side_effect(*args, **kwargs):
        nonlocal run_count
        run_count += 1
        if run_count == 1:
            return SimpleNamespace(stdout="", stderr="")
        raise OSError("Delete command failed")

    mock_run_cli_command.side_effect = side_effect

    target_creds = {"base_url": "target"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_permission_sets.write_permission_sets(source_permission_sets, target_creds, allow_delete=True)
    assert "command not found or execution failed" in str(exc_info.value)


def test_differential_fuzzing_permission_sets(mock_run_cli_command, mocker):
    random.seed(42)

    names = ["Taco", "Burrito", "Quesadilla", None, 42, SimpleNamespace(x=1)]
    permissions_options = [["see_looks"], ["see_user"], SimpleNamespace(y=2), {1, 2, 3}, None]
    ids = [1, 2, 3, 4, 5, None]

    def gen_ps(is_target=False):
        ps = SimpleNamespace()
        name = random.choice(names)
        if name is not None:
            ps.name = name
        perms = random.choice(permissions_options)
        if perms is not None and not is_target:
            ps.permissions = perms
        if is_target:
            ps_id = random.choice(ids)
            if ps_id is not None:
                ps.id = ps_id
        return ps

    def oracle_predict(source_ps, target_ps, allow_delete):
        valid_targets = []
        for t in target_ps:
            name = getattr(t, "name", None)
            if name is not None and isinstance(name, str):
                valid_targets.append(t)

        valid_sources = []
        for s in source_ps:
            name = getattr(s, "name", None)
            if name is not None and isinstance(name, str):
                valid_sources.append(s)

        deduped_sources = {}
        for s in valid_sources:
            deduped_sources[s.name] = s

        expected_calls = []
        for s_name, s in deduped_sources.items():
            payload = {}
            if hasattr(s, "name"):
                payload["name"] = s.name
            if hasattr(s, "permissions"):
                payload["permissions"] = s.permissions

            try:
                serialized = json.dumps(payload)
            except (TypeError, ValueError):
                continue

            matched_target = None
            for t in valid_targets:
                if getattr(t, "name") == s.name:
                    matched_target = t
                    break

            if matched_target is None:
                expected_calls.append(("create", s.name, serialized))
            else:
                target_id = getattr(matched_target, "id", None)
                if target_id is not None:
                    expected_calls.append(("update", str(target_id), serialized))

        if allow_delete:
            matched_source_names = set()
            for t in valid_targets:
                matched_source = deduped_sources.get(t.name)

                should_delete = False
                if matched_source:
                    if matched_source.name not in matched_source_names:
                        matched_source_names.add(matched_source.name)
                    else:
                        should_delete = True
                else:
                    should_delete = True

                if should_delete:
                    target_id = getattr(t, "id", None)
                    if target_id is not None:
                        expected_calls.append(("delete", str(target_id)))

        return expected_calls

    target_creds = {"base_url": "target"}

    for iteration in range(200):
        mock_run_cli_command.reset_mock()
        source_ps = [gen_ps(is_target=False) for _ in range(random.randint(0, 5))]
        target_ps = [gen_ps(is_target=True) for _ in range(random.randint(0, 5))]
        allow_delete = random.choice([True, False])

        mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=target_ps)

        # Always return success in differential fuzzing because oracle expects success
        mock_run_cli_command.side_effect = None
        mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")

        try:
            deploy_permission_sets.write_permission_sets(source_ps, target_creds, allow_delete=allow_delete)
        except (RuntimeError, FileNotFoundError, LookerCLIError):
            pass

        actual_calls = []
        for call_arg in mock_run_cli_command.call_args_list:
            cmd_args = call_arg[0][0]
            kwargs = call_arg[1]
            if "create_permission_set" in cmd_args:
                payload = kwargs.get("input")
                name = json.loads(payload)["name"]
                actual_calls.append(("create", name, payload))
            elif "update_permission_set" in cmd_args:
                target_id = cmd_args[4]
                payload = kwargs.get("input")
                actual_calls.append(("update", target_id, payload))
            elif "delete_permission_set" in cmd_args:
                target_id = cmd_args[4]
                actual_calls.append(("delete", target_id))

        expected = oracle_predict(source_ps, target_ps, allow_delete)

        assert actual_calls == expected, f"Mismatch on iteration {iteration}:\nSource: {source_ps}\nTarget: {target_ps}\nDelete: {allow_delete}\nExpected: {expected}\nActual: {actual_calls}"
