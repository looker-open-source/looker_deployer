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
from looker_deployer.commands import deploy_permission_sets
from looker_deployer.utils.exceptions import LookerCLIError


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_permission_sets.run_cli_command")


def test_invalid_regex_pattern(mock_run_cli_command):
    permission_set_list = [{"name": "Taco", "built_in": False}]
    mock_run_cli_command.return_value = SimpleNamespace(stdout=json.dumps(permission_set_list), stderr="")

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_permission_sets.get_filtered_permission_sets(creds, pattern="[invalid")
    assert "Invalid regular expression pattern" in str(exc_info.value)


def test_missing_name_attribute_source_in_match_by_key(mock_run_cli_command, mocker):
    source_permission_sets = [SimpleNamespace(permissions=["see_look"])]
    target_permission_sets = [SimpleNamespace(name="Taco", id=1)]

    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=target_permission_sets)

    target_creds = {"base_url": "target"}
    deploy_permission_sets.write_permission_sets(source_permission_sets, target_creds, {})
    mock_run_cli_command.assert_not_called()


def test_missing_name_attribute_target_in_match_by_key(mock_run_cli_command, mocker):
    source_permission_sets = [SimpleNamespace(name="Taco", permissions=["see_look"])]
    target_permission_sets = [SimpleNamespace(id=1)]

    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=target_permission_sets)
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")

    target_creds = {"base_url": "target"}
    deploy_permission_sets.write_permission_sets(source_permission_sets, target_creds)
    mock_run_cli_command.assert_called_once()
    assert "create_permission_set" in mock_run_cli_command.call_args[0][0]


def test_special_characters_in_names(mock_run_cli_command, mocker):
    special_name = "Taco's \"Special\" \\ Permission \n 🌮"
    permission_set_list = [SimpleNamespace(name=special_name, permissions=["see_look"])]

    mocker.patch("looker_deployer.commands.deploy_permission_sets.get_filtered_permission_sets", return_value=[])
    mock_run_cli_command.return_value = SimpleNamespace(stdout="", stderr="")

    target_creds = {"base_url": "target"}
    deploy_permission_sets.write_permission_sets(permission_set_list, target_creds)

    mock_run_cli_command.assert_called_once()
    kwargs = mock_run_cli_command.call_args[1]
    payload_str = kwargs.get("input")
    payload = json.loads(payload_str)
    assert payload["name"] == special_name


def test_fuzz_write_permission_sets(mock_run_cli_command, mocker):
    import random

    def random_val():
        choice = random.choice([
            "string_val", "", "special_🌮_\n_\"_'",
            123, 0, -1,
            True, False, None,
            ["a", "b"], [], [1, None],
            {"key": "value"}, {}
        ])
        return choice

    def random_object():
        obj_type = random.choice(["namespace", "dict", "string", "int", "list", "none"])
        if obj_type == "namespace":
            ns = SimpleNamespace()
            if random.random() > 0.2:
                ns.name = random_val()
            if random.random() > 0.2:
                ns.id = random_val()
            if random.random() > 0.2:
                ns.permissions = random_val()
            if random.random() > 0.2:
                ns.built_in = random_val()
            return ns
        elif obj_type == "dict":
            d = {}
            if random.random() > 0.2:
                d["name"] = random_val()
            if random.random() > 0.2:
                d["id"] = random_val()
            return d
        elif obj_type == "string":
            return random_val()
        elif obj_type == "int":
            return random.randint(-100, 100)
        elif obj_type == "list":
            return [random_val() for _ in range(random.randint(0, 3))]
        else:
            return None

    target_creds = {"base_url": "target"}

    for iteration in range(500):
        ret_code = random.choice([0, 1, -1])
        stdout_val = random.choice([
            "[]", "{}", '{"name": "Taco"}', '[{"name": "Burrito", "id": 5}]',
            "invalid json", "", "   ", "null", "[null]", '["string_in_list"]'
        ])
        stderr_val = random.choice(["", "some error message", "fatal error"])

        if ret_code != 0:
            mock_run_cli_command.side_effect = LookerCLIError("cmd", ret_code, stdout_val, stderr_val)
        else:
            mock_run_cli_command.side_effect = None
            mock_run_cli_command.return_value = SimpleNamespace(stdout=stdout_val, stderr=stderr_val)

        source_ps = [random_object() for _ in range(random.randint(0, 5))]
        pattern_val = random.choice([None, ".*", "Taco", "[invalid", ""])
        allow_delete_val = random.choice([None, True, False])

        try:
            deploy_permission_sets.write_permission_sets(
                source_ps, target_creds, pattern=pattern_val,
                allow_delete=allow_delete_val
            )
        except (RuntimeError, FileNotFoundError, LookerCLIError):
            pass
        except Exception as e:
            pytest.fail(f"Unhandled exception during fuzzing at iteration {iteration}: {type(e).__name__}: {e}\nSource: {source_ps}\nPattern: {pattern_val}")
