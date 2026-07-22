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
import re
import logging
from types import SimpleNamespace
import pytest
from looker_deployer.commands import deploy_user_attributes
from looker_deployer import cli
from looker_deployer.utils.exceptions import LookerCLIError


# 2. Test run_cli failure (LookerCLIError propagation)
def test_run_cli_failure(mocker):
    mock_run = mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli_command")
    mock_run.side_effect = LookerCLIError(
        command="looker-cli test",
        exit_code=1,
        stdout="",
        stderr="cli error"
    )
    creds = {"base_url": "test"}
    with pytest.raises(LookerCLIError) as exc_info:
        deploy_user_attributes.run_cli(["test"], creds)
    assert exc_info.value.stderr == "cli error"


# 3. Test get_filtered_user_attributes handles invalid JSON
def test_get_filtered_user_attributes_invalid_json(mocker):
    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", return_value="invalid json")
    creds = {"base_url": "test"}
    with pytest.raises(json.JSONDecodeError):
        deploy_user_attributes.get_filtered_user_attributes(creds)


# 4. Test system user attributes are filtered out
def test_get_filtered_user_attributes_filters_system(mocker):
    attrs = [
        {"name": "sys_attr", "is_system": True, "id": "1"},
        {"name": "user_attr", "is_system": False, "id": "2"}
    ]
    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", return_value=json.dumps(attrs))
    creds = {"base_url": "test"}
    res = deploy_user_attributes.get_filtered_user_attributes(creds)
    assert len(res) == 1
    assert res[0].name == "user_attr"
    assert res[0].id == "2"


# 5. Test get_filtered_user_attributes with invalid regex pattern
def test_get_filtered_user_attributes_invalid_regex(mocker):
    attrs = [
        {"name": "user_attr", "is_system": False, "id": "2"}
    ]
    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", return_value=json.dumps(attrs))
    creds = {"base_url": "test"}
    with pytest.raises(re.error):
        deploy_user_attributes.get_filtered_user_attributes(creds, pattern="[unclosed bracket")


# 5b. Test get_filtered_user_attributes raises AttributeError when 'name' is missing
def test_get_filtered_user_attributes_missing_name(mocker):
    attrs = [
        {"is_system": False, "id": "2"}  # missing name
    ]
    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", return_value=json.dumps(attrs))
    creds = {"base_url": "test"}
    with pytest.raises(AttributeError):
        deploy_user_attributes.get_filtered_user_attributes(creds)


# 6. Test delete behavior (allow_delete=True vs False)
def test_write_user_attributes_delete_allowed(mocker):
    source_attrs = []
    target_attrs = [
        {"name": "old_attr", "is_system": False, "id": "100"}
    ]
    target_groups = []

    calls = []

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            return json.dumps(target_groups)
        elif "delete_user_attribute" in cmd:
            return ""
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)

    deploy_user_attributes.write_user_attributes(source_creds, target_creds, allow_delete=True)

    assert (["api", "userattribute", "delete_user_attribute", "100"], target_creds) in calls


def test_write_user_attributes_delete_not_allowed(mocker):
    source_attrs = []
    target_attrs = [
        {"name": "old_attr", "is_system": False, "id": "100"}
    ]
    target_groups = []

    calls = []

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            return json.dumps(target_groups)
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)

    deploy_user_attributes.write_user_attributes(source_creds, target_creds, allow_delete=False)

    assert not any(cmd == ["api", "userattribute", "delete_user_attribute", "100"] for cmd, creds in calls)


# 7. Test missing target group mapping
def test_write_user_attributes_missing_target_group(mocker):
    source_attrs = [
        {"name": "my_attr", "label": "my_attr", "type": "string", "id": "1", "is_system": False}
    ]
    target_attrs = []
    target_groups = [
        {"name": "TargetGroupOnly", "id": "10"}
    ]
    source_gv = [
        {"id": "gv_1", "group_id": "50", "user_attribute_id": "1", "value": "val"}
    ]

    calls = []

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds, kwargs))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            if creds == source_creds:
                return json.dumps([{"name": "SourceGroupOnly", "id": "50"}])
            elif creds == target_creds:
                return json.dumps(target_groups)
        elif "create_user_attribute" in cmd:
            res = source_attrs[0].copy()
            res["id"] = "100"
            return json.dumps(res)
        elif "all_user_attribute_group_values" in cmd:
            if cmd[-1] == "1" and creds == source_creds:
                return json.dumps(source_gv)
            elif cmd[-1] == "100" and creds == target_creds:
                return "[]"
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)

    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    for cmd, creds, kwargs in calls:
        if "set_user_attribute_group_values" in cmd:
            assert kwargs.get("input") == "[]"


# 7b. Test write_user_attributes raises AttributeError when label or type is missing
def test_write_user_attributes_missing_label_or_type(mocker):
    source_attrs = [
        {"name": "my_attr", "id": "1", "is_system": False}
    ]
    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=lambda cmd, creds, **kwargs: json.dumps(source_attrs) if "all_user_attributes" in cmd else "[]")

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    with pytest.raises(AttributeError):
        deploy_user_attributes.write_user_attributes(source_creds, target_creds)


# 8. Test CLI parser configuration and routing
def test_cli_parsing(mocker):
    mock_main = mocker.patch("looker_deployer.commands.deploy_user_attributes.main")

    import sys
    test_args = [
        "looker-deployer",
        "user_attributes",
        "--source", "dev",
        "--target", "prod", "staging",
        "--ini", "custom.ini",
        "--pattern", "my_prefix.*",
        "--delete",
        "--debug"
    ]
    mocker.patch.object(sys, "argv", test_args)

    cli.main()

    mock_main.assert_called_once()
    called_args = mock_main.call_args[0][0]
    assert called_args.source == "dev"
    assert called_args.target == ["prod", "staging"]
    assert called_args.ini == "custom.ini"
    assert called_args.pattern == "my_prefix.*"
    assert called_args.delete is True
    assert called_args.debug is True


# 8b. Test CLI parser handles missing --source
def test_cli_parsing_missing_source(mocker):
    import sys
    test_args = [
        "looker-deployer",
        "user_attributes",
        "--target", "prod"
    ]
    mocker.patch.object(sys, "argv", test_args)
    with pytest.raises(SystemExit):
        cli.main()


# 8c. Test CLI parser handles missing --target
def test_cli_parsing_missing_target(mocker):
    import sys
    test_args = [
        "looker-deployer",
        "user_attributes",
        "--source", "dev"
    ]
    mocker.patch.object(sys, "argv", test_args)
    with pytest.raises(SystemExit):
        cli.main()


# 12. Test main programmatically with empty target list
def test_main_empty_target(mocker):
    mock_build_creds = mocker.patch("looker_deployer.commands.deploy_user_attributes.build_creds")
    mock_write = mocker.patch("looker_deployer.commands.deploy_user_attributes.write_user_attributes")

    args = SimpleNamespace(
        debug=False,
        ini="looker.ini",
        source="dev",
        target=[],
        pattern=None,
        delete=False
    )

    deploy_user_attributes.main(args)
    mock_build_creds.assert_called_once_with("looker.ini", "dev")
    mock_write.assert_not_called()


# 13. Test main setting debug logger level
def test_main_debug_level(mocker):
    mocker.patch("looker_deployer.commands.deploy_user_attributes.build_creds")
    mocker.patch("looker_deployer.commands.deploy_user_attributes.write_user_attributes")
    mock_logger_set_level = mocker.patch.object(deploy_user_attributes.logger, "setLevel")

    args = SimpleNamespace(
        debug=True,
        ini="looker.ini",
        source="dev",
        target=["prod"],
        pattern=None,
        delete=False
    )

    deploy_user_attributes.main(args)
    mock_logger_set_level.assert_called_once_with(logging.DEBUG)


# 14. Test add_group_name_information with type mismatch (int group_id, str key in lookup)
def test_add_group_name_information_int_gid_str_lookup():
    list_to_update = [SimpleNamespace(group_id=123)]
    group_lookup = {"123": "MyGroup"}
    res = deploy_user_attributes.add_group_name_information(list_to_update, group_lookup)
    assert res[0].name == "MyGroup"


# 15. Test add_group_name_information with type mismatch (str group_id, int key in lookup)
def test_add_group_name_information_str_gid_int_lookup():
    list_to_update = [SimpleNamespace(group_id="456")]
    group_lookup = {456: "AnotherGroup"}
    res = deploy_user_attributes.add_group_name_information(list_to_update, group_lookup)
    assert res[0].name == "AnotherGroup"


# 16. Test add_group_name_information with invalid group_id string (cannot convert to int)
def test_add_group_name_information_invalid_gid_str():
    list_to_update = [SimpleNamespace(group_id="invalid_id")]
    group_lookup = {789: "SomeGroup"}
    res = deploy_user_attributes.add_group_name_information(list_to_update, group_lookup)
    assert res[0].name is None


# 17. Test get_user_attribute_group_value handles invalid JSON
def test_get_user_attribute_group_value_invalid_json(mocker):
    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", return_value="invalid json")
    creds = {"base_url": "test"}
    with pytest.raises(json.JSONDecodeError):
        deploy_user_attributes.get_user_attribute_group_value(creds, SimpleNamespace(id="1"))


# 18. Test write_user_attributes handles invalid JSON from group list
def test_write_user_attributes_source_groups_invalid_json(mocker):
    source_attrs = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False}
    ]

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        if "all_user_attributes" in cmd:
            return json.dumps(source_attrs)
        elif "all_groups" in cmd:
            return "invalid json"
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)
    with pytest.raises(json.JSONDecodeError):
        deploy_user_attributes.write_user_attributes(source_creds, target_creds)


# 19. Test write_user_attributes when source group ID is completely missing from lookup
def test_write_user_attributes_source_group_id_not_in_lookup(mocker):
    source_attrs = [
        {"name": "my_attr", "label": "my_attr", "type": "string", "id": "1", "is_system": False}
    ]
    target_attrs = []
    target_groups = [
        {"name": "TargetGroupOnly", "id": "10"}
    ]
    source_gv = [
        {"id": "gv_1", "group_id": "999", "user_attribute_id": "1", "value": "val"}
    ]

    calls = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds, kwargs))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            if creds == source_creds:
                return json.dumps([{"name": "SourceGroupOnly", "id": "50"}])
            elif creds == target_creds:
                return json.dumps(target_groups)
        elif "create_user_attribute" in cmd:
            res = source_attrs[0].copy()
            res["id"] = "100"
            return json.dumps(res)
        elif "all_user_attribute_group_values" in cmd:
            if cmd[-1] == "1" and creds == source_creds:
                return json.dumps(source_gv)
            elif cmd[-1] == "100" and creds == target_creds:
                return "[]"
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)
    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    for cmd, creds, kwargs in calls:
        if "set_user_attribute_group_values" in cmd:
            assert kwargs.get("input") == "[]"


# 20. Test write_user_attributes group_id type mismatch between target_group and target_group_values
def test_write_user_attributes_group_id_type_mismatch(mocker):
    source_attrs = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False}
    ]
    target_attrs = [
        {"name": "Cheese", "id": "100", "label": "Cheese", "type": "string", "is_system": False}
    ]

    source_gv = [
        {"id": "gv_1", "group_id": 1, "user_attribute_id": "1", "value": "yummy"}
    ]
    target_gv = [
        {"id": "gv_2", "group_id": "1", "user_attribute_id": "100", "value": "yummy"}
    ]

    target_groups = [
        {"name": "Taco", "id": 1}
    ]
    source_groups = [
        {"name": "Taco", "id": 1}
    ]

    calls = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds, kwargs))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            if creds == source_creds:
                return json.dumps(source_groups)
            elif creds == target_creds:
                return json.dumps(target_groups)
        elif "all_user_attribute_group_values" in cmd:
            if cmd[-1] == "1" and creds == source_creds:
                return json.dumps(source_gv)
            elif cmd[-1] == "100" and creds == target_creds:
                return json.dumps(target_gv)
        elif "update_user_attribute" in cmd:
            return json.dumps(target_attrs[0])
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)
    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    set_calls = [(cmd, kwargs) for cmd, creds, kwargs in calls if "set_user_attribute_group_values" in cmd]
    assert len(set_calls) == 1
    payload = json.loads(set_calls[0][1].get("input"))
    assert payload == [{"group_id": "1", "value": "yummy"}]


# 21. Test empty list of user attributes in source with allow_delete=True
def test_write_user_attributes_empty_source_delete_allowed(mocker):
    target_attrs = [
        {"name": "old_attr", "is_system": False, "id": "100"}
    ]
    calls = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds, kwargs))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return "[]"
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            return "[]"
        elif "delete_user_attribute" in cmd:
            return "{}"
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)

    deploy_user_attributes.write_user_attributes(source_creds, target_creds, allow_delete=True)

    assert any(cmd == ["api", "userattribute", "delete_user_attribute", "100"] and creds == target_creds for cmd, creds, kwargs in calls)


# 22. Test empty list of group values for a user attribute
def test_write_user_attributes_empty_group_values_deletes_target_values(mocker):
    source_attrs = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False}
    ]
    target_attrs = [
        {"name": "Cheese", "id": "100", "label": "Cheese", "type": "string", "is_system": False}
    ]

    target_gv = [
        {"id": "gv_2", "group_id": "1", "user_attribute_id": "100", "value": "yummy"}
    ]

    target_groups = [
        {"name": "Taco", "id": "1"}
    ]
    source_groups = [
        {"name": "Taco", "id": "1"}
    ]

    calls = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds, kwargs))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            if creds == source_creds:
                return json.dumps(source_groups)
            elif creds == target_creds:
                return json.dumps(target_groups)
        elif "all_user_attribute_group_values" in cmd:
            if cmd[-1] == "1" and creds == source_creds:
                return "[]"
            elif cmd[-1] == "100" and creds == target_creds:
                return json.dumps(target_gv)
        elif "update_user_attribute" in cmd:
            return json.dumps(target_attrs[0])
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)
    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    set_calls = [(cmd, kwargs) for cmd, creds, kwargs in calls if "set_user_attribute_group_values" in cmd]
    assert len(set_calls) == 1
    payload = json.loads(set_calls[0][1].get("input"))
    assert payload == []


# 23. Test missing/None values in group value schema
def test_write_user_attributes_none_value_matching(mocker):
    source_attrs = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False}
    ]
    target_attrs = [
        {"name": "Cheese", "id": "100", "label": "Cheese", "type": "string", "is_system": False}
    ]

    source_gv = [
        {"id": "gv_1", "group_id": "1", "user_attribute_id": "1"}
    ]
    target_gv = [
        {"id": "gv_2", "group_id": "1", "user_attribute_id": "100", "value": None}
    ]

    target_groups = [
        {"name": "Taco", "id": "1"}
    ]
    source_groups = [
        {"name": "Taco", "id": "1"}
    ]

    calls = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds):
        calls.append((cmd, creds))
        if cmd == ["user-attribute", "ls", "--format", "json"]:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif cmd == ["group", "ls", "--format", "json"]:
            if creds == source_creds:
                return json.dumps(source_groups)
            elif creds == target_creds:
                return json.dumps(target_groups)
        elif cmd == ["user-attribute", "group-value", "ls", "1", "--format", "json"] and creds == source_creds:
            return json.dumps(source_gv)
        elif cmd == ["user-attribute", "group-value", "ls", "100", "--format", "json"] and creds == target_creds:
            return json.dumps(target_gv)
        elif "user-attribute" in cmd and "update" in cmd:
            return json.dumps(target_attrs[0])
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)
    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    action_calls = [cmd for cmd, creds in calls if cmd[0] == "group" and "attribute-value" in cmd]
    assert len(action_calls) == 0


# 24. Test non-numeric string group ID matches directly in lookup
def test_add_group_name_information_non_numeric_string():
    list_to_update = [SimpleNamespace(group_id="group_abc")]
    group_lookup = {"group_abc": "MyGroup"}
    res = deploy_user_attributes.add_group_name_information(list_to_update, group_lookup)
    assert res[0].name == "MyGroup"


# 25. Test non-numeric string group ID not in lookup (graceful None name)
def test_add_group_name_information_non_numeric_string_missing():
    list_to_update = [SimpleNamespace(group_id="group_xyz")]
    group_lookup = {"group_abc": "MyGroup"}
    res = deploy_user_attributes.add_group_name_information(list_to_update, group_lookup)
    assert res[0].name is None


# 26. Test duplicate group names in target groups list
def test_write_user_attributes_duplicate_target_group_names(mocker):
    source_attrs = [
        {"name": "Cheese", "id": "1", "label": "Cheese", "type": "string", "is_system": False}
    ]
    target_attrs = [
        {"name": "Cheese", "id": "100", "label": "Cheese", "type": "string", "is_system": False}
    ]

    source_gv = [
        {"id": "gv_1", "group_id": "1", "user_attribute_id": "1", "value": "yummy"}
    ]
    target_gv = []

    target_groups = [
        {"name": "Taco", "id": "10"},
        {"name": "Taco", "id": "20"}
    ]
    source_groups = [
        {"name": "Taco", "id": "1"}
    ]

    calls = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds, kwargs))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            if creds == source_creds:
                return json.dumps(source_groups)
            elif creds == target_creds:
                return json.dumps(target_groups)
        elif "all_user_attribute_group_values" in cmd:
            if cmd[-1] == "1" and creds == source_creds:
                return json.dumps(source_gv)
            elif cmd[-1] == "100" and creds == target_creds:
                return json.dumps(target_gv)
        elif "update_user_attribute" in cmd:
            return json.dumps(target_attrs[0])
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)
    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    set_calls = [(cmd, kwargs) for cmd, creds, kwargs in calls if "set_user_attribute_group_values" in cmd]
    assert len(set_calls) == 1
    payload = json.loads(set_calls[0][1].get("input"))
    assert payload == [{"group_id": "10", "value": "yummy"}]


# 27. Test write_user_attributes all empty lists (no commands executed)
def test_write_user_attributes_all_empty(mocker):
    """Scenario 1: All lists are empty. No CLI commands should be executed except list/ls queries."""
    calls = []

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds))
        if "all_user_attributes" in cmd:
            return "[]"
        elif "all_groups" in cmd:
            return "[]"
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    # Verify no create, update, or delete commands are called
    for cmd, creds in calls:
        if any(x in cmd for x in ["all_user_attributes", "all_groups"]):
            continue
        pytest.fail(f"Unexpected CLI call: {cmd} with creds {creds}")


# 28. Test non-numeric group IDs (e.g. strings like 'group_foo')
def test_write_user_attributes_non_numeric_group_ids(mocker):
    """Scenario 2: Non-numeric group IDs (e.g. strings like 'group_foo')."""
    source_attrs = [
        {"name": "test_attr", "id": "1", "label": "test_attr", "type": "string", "is_system": False}
    ]
    target_attrs = [
        {"name": "test_attr", "id": "100", "label": "test_attr", "type": "string", "is_system": False}
    ]
    source_groups = [
        {"name": "GroupFoo", "id": "group_foo"}
    ]
    target_groups = [
        {"name": "GroupFoo", "id": "group_foo"}
    ]
    source_gv = [
        {"id": "gv_1", "group_id": "group_foo", "user_attribute_id": "1", "value": "val_foo"}
    ]
    target_gv = [
        {"id": "gv_2", "group_id": "group_foo", "user_attribute_id": "100", "value": "val_foo"}
    ]

    calls = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds, kwargs))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            if creds == source_creds:
                return json.dumps(source_groups)
            elif creds == target_creds:
                return json.dumps(target_groups)
        elif "all_user_attribute_group_values" in cmd:
            if cmd[-1] == "1":
                return json.dumps(source_gv)
            elif cmd[-1] == "100":
                return json.dumps(target_gv)
        elif "update_user_attribute" in cmd:
            return json.dumps(target_attrs[0])
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)

    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    set_calls = [(cmd, kwargs) for cmd, creds, kwargs in calls if "set_user_attribute_group_values" in cmd]
    assert len(set_calls) == 1
    payload = json.loads(set_calls[0][1].get("input"))
    assert payload == [{"group_id": "group_foo", "value": "val_foo"}]


# 29. Test write_user_attributes missing optional fields in source
def test_write_user_attributes_missing_optional_fields(mocker):
    """Scenario 3: Source user attribute is missing optional fields.
    The code should use default/fallback values (None/False) and not crash.
    """
    source_attrs = [
        {"name": "test_attr", "id": "1", "label": "test_attr", "type": "string", "is_system": False}
    ]
    calls = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds, kwargs))
        if "all_user_attributes" in cmd:
            return json.dumps(source_attrs) if creds == source_creds else "[]"
        elif "all_groups" in cmd:
            return "[]"
        elif "all_user_attribute_group_values" in cmd:
            return "[]"
        elif "create_user_attribute" in cmd:
            payload = json.loads(kwargs.get("input"))
            payload["id"] = "100"
            return json.dumps(payload)
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)

    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    create_call = next(((cmd, kwargs) for cmd, creds, kwargs in calls if "create_user_attribute" in cmd), None)
    assert create_call is not None
    payload = json.loads(create_call[1].get("input"))
    assert payload["name"] == "test_attr"
    assert payload["default_value"] is None
    assert payload["value_is_hidden"] is False
    assert payload["user_can_view"] is False
    assert payload["user_can_edit"] is False


# 30. Test duplicate group values for the same group ID
def test_write_user_attributes_duplicate_group_values(mocker):
    """Scenario 4: Duplicate group values for the same group ID.
    The code tracks desired target group values via dict comprehension:
    desired_group_values = {str(gv.group_id): getattr(gv, "value", None) for gv in user_attribute_group_values}
    We want to ensure that only the last value is kept and reconciled correctly.
    """
    source_attrs = [
        {"name": "test_attr", "id": "1", "label": "test_attr", "type": "string", "is_system": False}
    ]
    target_attrs = [
        {"name": "test_attr", "id": "100", "label": "test_attr", "type": "string", "is_system": False}
    ]
    source_groups = [
        {"name": "GroupA", "id": "10"}
    ]
    target_groups = [
        {"name": "GroupA", "id": "10"}
    ]
    source_gv = [
        {"id": "gv_1", "group_id": "10", "user_attribute_id": "1", "value": "first_val"},
        {"id": "gv_2", "group_id": "10", "user_attribute_id": "1", "value": "second_val"}
    ]
    target_gv = [
        {"id": "gv_3", "group_id": "10", "user_attribute_id": "100", "value": "second_val"}
    ]

    calls = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds, kwargs))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            if creds == source_creds:
                return json.dumps(source_groups)
            elif creds == target_creds:
                return json.dumps(target_groups)
        elif "all_user_attribute_group_values" in cmd:
            if cmd[-1] == "1":
                return json.dumps(source_gv)
            elif cmd[-1] == "100":
                return json.dumps(target_gv)
        elif "update_user_attribute" in cmd:
            return json.dumps(target_attrs[0])
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)

    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    set_calls = [(cmd, kwargs) for cmd, creds, kwargs in calls if "set_user_attribute_group_values" in cmd]
    assert len(set_calls) == 1
    payload = json.loads(set_calls[0][1].get("input"))
    assert payload == [{"group_id": "10", "value": "second_val"}]


# 31. Test float-like string IDs or leading-zero string IDs
def test_write_user_attributes_float_like_string_ids(mocker):
    """Scenario 5: Float-like string IDs or leading-zero string IDs.
    e.g. source has group ID "0123" and target has group ID "123".
    """
    source_attrs = [
        {"name": "test_attr", "id": "1", "label": "test_attr", "type": "string", "is_system": False}
    ]
    target_attrs = [
        {"name": "test_attr", "id": "100", "label": "test_attr", "type": "string", "is_system": False}
    ]
    source_groups = [
        {"name": "GroupA", "id": "012"}
    ]
    target_groups = [
        {"name": "GroupA", "id": "12"}
    ]
    source_gv = [
        {"id": "gv_1", "group_id": "012", "user_attribute_id": "1", "value": "val"}
    ]
    target_gv = [
        {"id": "gv_2", "group_id": "12", "user_attribute_id": "100", "value": "val"}
    ]

    calls = []
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}

    def mock_run_cli(cmd, creds, **kwargs):
        calls.append((cmd, creds, kwargs))
        if "all_user_attributes" in cmd:
            if creds == source_creds:
                return json.dumps(source_attrs)
            elif creds == target_creds:
                return json.dumps(target_attrs)
        elif "all_groups" in cmd:
            if creds == source_creds:
                return json.dumps(source_groups)
            elif creds == target_creds:
                return json.dumps(target_groups)
        elif "all_user_attribute_group_values" in cmd:
            if cmd[-1] == "1":
                return json.dumps(source_gv)
            elif cmd[-1] == "100":
                return json.dumps(target_gv)
        elif "update_user_attribute" in cmd:
            return json.dumps(target_attrs[0])
        return "[]"

    mocker.patch("looker_deployer.commands.deploy_user_attributes.run_cli", side_effect=mock_run_cli)

    deploy_user_attributes.write_user_attributes(source_creds, target_creds)

    set_calls = [(cmd, kwargs) for cmd, creds, kwargs in calls if "set_user_attribute_group_values" in cmd]
    assert len(set_calls) == 1
    payload = json.loads(set_calls[0][1].get("input"))
    assert payload == [{"group_id": "12", "value": "val"}]
