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
import random
import pytest
from types import SimpleNamespace
from unittest.mock import call

from looker_deployer.commands import deploy_model_sets


@pytest.fixture
def mock_run_cli_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_model_sets.run_cli_command")


def test_get_filtered_model_sets_invalid_regex(mock_run_cli_command):
    model_set_list = [
        {"name": "Taco", "built_in": False}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(model_set_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    with pytest.raises(RuntimeError) as exc_info:
        deploy_model_sets.get_filtered_model_sets(creds, pattern="[invalid-regex")
    assert "Invalid regular expression pattern" in str(exc_info.value)


def test_get_filtered_model_sets_filters_built_in(mock_run_cli_command):
    model_set_list = [
        {"name": "CustomSet", "built_in": False},
        {"name": "BuiltInSet", "built_in": True},
        {"name": "AnotherCustomSet"}
    ]
    mock_res = SimpleNamespace(stdout=json.dumps(model_set_list), stderr="")
    mock_run_cli_command.return_value = mock_res

    creds = {"base_url": "test"}
    model_sets = deploy_model_sets.get_filtered_model_sets(creds)
    assert [m.name for m in model_sets] == ["CustomSet", "AnotherCustomSet"]


def test_write_model_sets_skips_missing_names(mock_run_cli_command, mocker):
    source_model_sets = [
        SimpleNamespace(name="Taco", models=["model1"]),
        SimpleNamespace(models=["model2"])
    ]

    target_model_sets = [
        SimpleNamespace(name="Burrito", id=1),
        SimpleNamespace(id=2)
    ]

    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=target_model_sets)
    mock_logger = mocker.patch.object(deploy_model_sets.logger, "warning")

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets(source_model_sets, creds, allow_delete=True)

    mock_logger.assert_has_calls([
        call("Target model set is missing 'name' attribute. Skipping."),
        call("Source model set is missing 'name' attribute. Skipping.")
    ], any_order=True)

    mock_run_cli_command.assert_has_calls([
        call(
            ["looker-cli", "api", "role", "create_model_set", "-"],
            text=True,
            creds=creds,
            input=json.dumps({"name": "Taco", "models": ["model1"]})
        ),
        call(
            ["looker-cli", "api", "role", "delete_model_set", "1"],
            text=True,
            creds=creds
        )
    ], any_order=True)


def test_write_model_sets_special_characters(mock_run_cli_command, mocker):
    special_name = "Taco & Burrito \"Set\" \\ '$1' 🌮"
    model_set_list = [SimpleNamespace(name=special_name, models=["model1", "model2"])]

    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[])

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets(model_set_list, creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "create_model_set", "-"],
        text=True,
        creds=creds,
        input=json.dumps({"name": special_name, "models": ["model1", "model2"]})
    )


def test_write_model_sets_large_inputs(mock_run_cli_command, mocker):
    large_models = [f"model_{i}" for i in range(1000)]
    model_set_list = [SimpleNamespace(name="HugeSet", models=large_models)]

    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[])

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets(model_set_list, creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "create_model_set", "-"],
        text=True,
        creds=creds,
        input=json.dumps({"name": "HugeSet", "models": large_models})
    )


def test_write_model_sets_empty_models(mock_run_cli_command, mocker):
    model_set_list = [SimpleNamespace(name="EmptySet", models=[])]

    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[])

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets(model_set_list, creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "create_model_set", "-"],
        text=True,
        creds=creds,
        input=json.dumps({"name": "EmptySet", "models": []})
    )


def test_write_model_sets_missing_models_attribute(mock_run_cli_command, mocker):
    model_set_list = [SimpleNamespace(name="NoModelsAttr")]

    mock_res = SimpleNamespace(stdout="", stderr="")
    mock_run_cli_command.return_value = mock_res
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[])

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets(model_set_list, creds)

    mock_run_cli_command.assert_called_once_with(
        ["looker-cli", "api", "role", "create_model_set", "-"],
        text=True,
        creds=creds,
        input=json.dumps({"name": "NoModelsAttr"})
    )


def test_write_model_sets_empty_source_and_target(mock_run_cli_command, mocker):
    mocker.patch("looker_deployer.commands.deploy_model_sets.get_filtered_model_sets", return_value=[])

    creds = {"base_url": "test"}
    deploy_model_sets.write_model_sets([], creds, allow_delete=True)

    mock_run_cli_command.assert_not_called()


class LookerCliSimulator:
    def __init__(self, initial_model_sets):
        self.model_sets = {ms["id"]: dict(ms) for ms in initial_model_sets}
        self.next_id = max(self.model_sets.keys(), default=0) + 1
        self.calls = []

    def run(self, cmd, creds=None, **kwargs):
        self.calls.append(cmd)

        if "all_model_sets" in cmd:
            res = list(self.model_sets.values())
            return SimpleNamespace(returncode=0, stdout=json.dumps(res), stderr="")
        elif "create_model_set" in cmd:
            payload_str = kwargs.get("input")
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                return SimpleNamespace(returncode=1, stdout="", stderr="Malformed payload JSON")

            new_ms = {
                "id": self.next_id,
                "name": payload.get("name"),
                "models": payload.get("models", []),
                "built_in": False
            }
            self.model_sets[self.next_id] = new_ms
            self.next_id += 1
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        elif "update_model_set" in cmd:
            id_val = int(cmd[4])
            payload_str = kwargs.get("input")
            if id_val not in self.model_sets:
                return SimpleNamespace(returncode=1, stdout="", stderr=f"Model set ID {id_val} not found")
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                return SimpleNamespace(returncode=1, stdout="", stderr="Malformed payload JSON")

            self.model_sets[id_val]["name"] = payload.get("name", self.model_sets[id_val]["name"])
            if "models" in payload:
                self.model_sets[id_val]["models"] = payload["models"]
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        elif "delete_model_set" in cmd:
            id_val = int(cmd[4])
            if id_val not in self.model_sets:
                return SimpleNamespace(returncode=1, stdout="", stderr=f"Model set ID {id_val} not found")
            del self.model_sets[id_val]
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        return SimpleNamespace(returncode=1, stdout="", stderr=f"Unknown command {cmd}")


def test_write_model_sets_differential_fuzzing(mocker):
    random.seed(42)

    for iteration in range(200):
        target_model_sets = []
        num_target = random.randint(0, 10)
        used_target_names = set()
        next_target_id = 1
        for _ in range(num_target):
            if random.random() < 0.1:
                target_model_sets.append({"id": next_target_id, "models": ["m1"]})
            else:
                name = f"Set_{random.randint(1, 15)}"
                if name not in used_target_names:
                    target_model_sets.append({
                        "id": next_target_id,
                        "name": name,
                        "models": [f"m{random.randint(1, 5)}" for _ in range(random.randint(1, 3))],
                        "built_in": False
                    })
                    used_target_names.add(name)
            next_target_id += 1

        source_model_sets = []
        num_source = random.randint(0, 10)
        used_source_names = set()
        for _ in range(num_source):
            if random.random() < 0.1:
                source_model_sets.append(SimpleNamespace(models=["m1"]))
            else:
                name = f"Set_{random.randint(1, 15)}"
                if name not in used_source_names:
                    source_model_sets.append(SimpleNamespace(
                        name=name,
                        models=[f"m{random.randint(1, 5)}" for _ in range(random.randint(1, 3))]
                    ))
                    used_source_names.add(name)

        allow_delete = random.choice([True, False])

        sim = LookerCliSimulator(target_model_sets)
        mocker.patch("looker_deployer.commands.deploy_model_sets.run_cli_command", side_effect=sim.run)

        creds = {"base_url": "test"}
        deploy_model_sets.write_model_sets(source_model_sets, creds, allow_delete=allow_delete)

        valid_source = [s for s in source_model_sets if getattr(s, "name", None) is not None]
        valid_target = [t for t in target_model_sets if t.get("name") is not None]

        expected_target_by_name = {t["name"]: dict(t) for t in valid_target}

        for src in valid_source:
            if src.name in expected_target_by_name:
                expected_target_by_name[src.name]["models"] = src.models
            else:
                expected_target_by_name[src.name] = {
                    "name": src.name,
                    "models": src.models,
                    "built_in": False
                }

        if allow_delete:
            src_names = {s.name for s in valid_source}
            expected_target_by_name = {name: val for name, val in expected_target_by_name.items() if name in src_names}

        sim_state_by_name = {ms["name"]: ms for ms in sim.model_sets.values() if ms.get("name") is not None}

        assert set(sim_state_by_name.keys()) == set(expected_target_by_name.keys()), \
            f"Keys mismatch at iteration {iteration}. Sim: {sim_state_by_name.keys()}, Expected: {expected_target_by_name.keys()}"

        for name in expected_target_by_name:
            assert sim_state_by_name[name]["models"] == expected_target_by_name[name]["models"], \
                f"Models mismatch for '{name}' at iteration {iteration}. Sim: {sim_state_by_name[name]}, Expected: {expected_target_by_name[name]}"
