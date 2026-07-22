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
import json
from types import SimpleNamespace
from looker_deployer.commands import deploy_boards


class MockCompletedProcess:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


class MockLook:
    slug = "TacoCat"
    title = "foobarbaz"
    id = 1


class MockDash:
    slug = "BurritoCat"
    title = "foobarbaz"
    id = 2


class MockBoardItem:
    id = 5
    dashboard_id = 2
    look_id = 1


class MockBoardSection:
    id = 4
    board_items = [MockBoardItem()]


class MockBoard:
    id = 3
    title = "foo"
    description = "bar"
    board_sections = [MockBoardSection()]


@pytest.fixture
def mock_run_subprocess_command(mocker):
    return mocker.patch("looker_deployer.commands.deploy_boards.run_subprocess_command")


def test_match_dashboard_id(mock_run_subprocess_command):
    dash = {"slug": "BurritoCat", "title": "foobarbaz", "id": 2}

    def mock_run(cmd, **kwargs):
        if len(cmd) > 3:
            if cmd[3] == "search_dashboards":
                return MockCompletedProcess(json.dumps([dash]))
            if cmd[3] == "dashboard":
                return MockCompletedProcess(json.dumps(dash))
        return MockCompletedProcess()

    mock_run_subprocess_command.side_effect = mock_run

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    dash_id = deploy_boards.match_dashboard_id(1, source_creds, target_creds)
    assert dash_id == 2


def test_match_dashboard_id_multi(mock_run_subprocess_command):
    dash = {"slug": "BurritoCat", "title": "foobarbaz", "id": 2}

    def mock_run(cmd, **kwargs):
        if len(cmd) > 3:
            if cmd[3] == "search_dashboards":
                return MockCompletedProcess(json.dumps([dash, dash]))
            if cmd[3] == "dashboard":
                return MockCompletedProcess(json.dumps(dash))
        return MockCompletedProcess()

    mock_run_subprocess_command.side_effect = mock_run

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    with pytest.raises(deploy_boards.MultipleAssetsFoundError):
        deploy_boards.match_dashboard_id(1, source_creds, target_creds)


def test_match_look_id(mock_run_subprocess_command):
    look = {"slug": "TacoCat", "title": "foobarbaz", "id": 1}

    def mock_run(cmd, **kwargs):
        if len(cmd) > 3:
            if cmd[3] == "search_looks":
                return MockCompletedProcess(json.dumps([look]))
            if cmd[3] == "look":
                return MockCompletedProcess(json.dumps(look))
        return MockCompletedProcess()

    mock_run_subprocess_command.side_effect = mock_run

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    look_id = deploy_boards.match_look_id(1, source_creds, target_creds)
    assert look_id == 1


def test_match_look_id_multi(mock_run_subprocess_command):
    look = {"slug": "TacoCat", "title": "foobarbaz", "id": 1}

    def mock_run(cmd, **kwargs):
        if len(cmd) > 3:
            if cmd[3] == "search_looks":
                return MockCompletedProcess(json.dumps([look, look]))
            if cmd[3] == "look":
                return MockCompletedProcess(json.dumps(look))
        return MockCompletedProcess()

    mock_run_subprocess_command.side_effect = mock_run

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    with pytest.raises(deploy_boards.MultipleAssetsFoundError):
        deploy_boards.match_look_id(1, source_creds, target_creds)


def test_return_board(mock_run_subprocess_command):
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps([{"id": 42, "title": "foo"}]))
    source_creds = {"base_url": "source"}
    board = deploy_boards.return_board("foo", source_creds)
    assert board.id == 42


def test_return_board_multi(mock_run_subprocess_command):
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps([{"id": 42, "title": "foo"}, {"id": 81, "title": "foo"}]))

    source_creds = {"base_url": "source"}
    with pytest.raises(deploy_boards.MultipleAssetsFoundError):
        deploy_boards.return_board("foo", source_creds)


def test_create_or_update_board_create(mock_run_subprocess_command):
    test_board = SimpleNamespace(title="taco", description="burrito")

    def mock_run(cmd, **kwargs):
        if "all_boards" in cmd:
            return MockCompletedProcess(json.dumps([]))
        if "create_board" in cmd:
            return MockCompletedProcess(json.dumps({"id": 3}))
        return MockCompletedProcess()

    mock_run_subprocess_command.side_effect = mock_run

    target_creds = {"base_url": "target"}
    board_id = deploy_boards.create_or_update_board(test_board, target_creds)
    assert board_id == 3


def test_create_board_create_board_call(mock_run_subprocess_command):
    test_board = SimpleNamespace(title="taco", description="burrito", id=42)

    def mock_run(cmd, **kwargs):
        if "all_boards" in cmd:
            return MockCompletedProcess(json.dumps([]))
        if "create_board" in cmd:
            return MockCompletedProcess(json.dumps({"id": 3}))
        return MockCompletedProcess()

    mock_run_subprocess_command.side_effect = mock_run
    target_creds = {"base_url": "target"}
    deploy_boards.create_or_update_board(test_board, target_creds)

    mock_run_subprocess_command.assert_any_call(
        ["looker-cli", "api", "board", "create_board", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"title": "taco", "description": "burrito"})
    )


def test_create_or_update_board_search_error(mock_run_subprocess_command):
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps([{"id": 1, "title": "foo"}, {"id": 2, "title": "foo"}]))

    test_board = SimpleNamespace(title="foo")
    target_creds = {"base_url": "target"}
    with pytest.raises(AssertionError):
        deploy_boards.create_or_update_board(test_board, target_creds)


def test_create_or_update_board_update(mock_run_subprocess_command):
    test_board = SimpleNamespace(title="taco", description="burrito")

    def mock_run(cmd, **kwargs):
        if "all_boards" in cmd:
            return MockCompletedProcess(json.dumps([{"id": 3, "board_sections": [], "title": "taco"}]))
        if "update_board" in cmd:
            return MockCompletedProcess(json.dumps({"id": 3}))
        return MockCompletedProcess()

    mock_run_subprocess_command.side_effect = mock_run

    target_creds = {"base_url": "target"}
    board_id = deploy_boards.create_or_update_board(test_board, target_creds)
    assert board_id == 3


def test_create_or_update_board_update_board_call(mock_run_subprocess_command):
    test_board = SimpleNamespace(title="taco", description="burrito", id=42)

    def mock_run(cmd, **kwargs):
        if "all_boards" in cmd:
            return MockCompletedProcess(json.dumps([{"id": 3, "board_sections": [], "title": "taco"}]))
        if "update_board" in cmd:
            return MockCompletedProcess(json.dumps({"id": 3}))
        return MockCompletedProcess()

    mock_run_subprocess_command.side_effect = mock_run

    target_creds = {"base_url": "target"}
    deploy_boards.create_or_update_board(test_board, target_creds)
    mock_run_subprocess_command.assert_any_call(
        ["looker-cli", "api", "board", "update_board", "3", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"title": "taco", "description": "burrito"})
    )


def test_create_or_update_board_update_delete_call(mock_run_subprocess_command):
    test_board = SimpleNamespace(title="taco", description="burrito", id=42)

    def mock_run(cmd, **kwargs):
        if "all_boards" in cmd:
            return MockCompletedProcess(json.dumps([{"id": 3, "board_sections": [{"id": 10}], "title": "taco"}]))
        if "update_board" in cmd:
            return MockCompletedProcess(json.dumps({"id": 3}))
        if "delete_board_section" in cmd:
            return MockCompletedProcess(json.dumps({}))
        return MockCompletedProcess()

    mock_run_subprocess_command.side_effect = mock_run

    target_creds = {"base_url": "target"}
    deploy_boards.create_or_update_board(test_board, target_creds)
    mock_run_subprocess_command.assert_any_call(
        ["looker-cli", "api", "board", "delete_board_section", "10"],
        creds=target_creds,
        text=True,
        input=None
    )


def test_create_board_section(mock_run_subprocess_command):
    test_board_section = SimpleNamespace(title="taco", description="burrito")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 4}))

    target_creds = {"base_url": "target"}
    board_section_id = deploy_boards.create_board_section(test_board_section, 1, target_creds)
    assert board_section_id == 4


def test_create_board_section_create_board_section_call(mock_run_subprocess_command):
    test_board_section = SimpleNamespace(title="taco", description="burrito", id="42")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 4}))

    target_creds = {"base_url": "target"}
    deploy_boards.create_board_section(test_board_section, "1", target_creds)

    mock_run_subprocess_command.assert_any_call(
        ["looker-cli", "api", "board", "create_board_section", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"board_id": "1", "title": "taco", "description": "burrito"})
    )


def test_create_board_item_dashboard(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(title="taco", description="burrito", dashboard_id="42")
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    board_item = deploy_boards.create_board_item(test_board_item, 1, source_creds, target_creds)
    assert board_item.id == 5


def test_create_board_item_look(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(title="taco", description="burrito", look_id="42")
    mocker.patch("looker_deployer.commands.deploy_boards.match_look_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    board_item = deploy_boards.create_board_item(test_board_item, 1, source_creds, target_creds)
    assert board_item.id == 5


def test_create_board_item_dashboard_match_call(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(title="taco", description="burrito", dashboard_id="42")
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 1, source_creds, target_creds)
    deploy_boards.match_dashboard_id.assert_called_with("42", source_creds, target_creds)


def test_create_board_item_look_match_call(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(title="taco", description="burrito", look_id="42")
    mocker.patch("looker_deployer.commands.deploy_boards.match_look_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 1, source_creds, target_creds)
    deploy_boards.match_look_id.assert_called_with("42", source_creds, target_creds)


def test_create_board_item_dashboard_item_call(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(title="taco", description="burrito", dashboard_id="42")
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)
    mock_run_subprocess_command.assert_any_call(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"board_section_id": "10", "dashboard_id": "1", "title": "taco", "description": "burrito"})
    )


def test_create_board_item_look_item_call(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(title="taco", description="burrito", look_id="42")
    mocker.patch("looker_deployer.commands.deploy_boards.match_look_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)
    mock_run_subprocess_command.assert_any_call(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps({"board_section_id": "10", "look_id": "1", "title": "taco", "description": "burrito"})
    )


def test_create_board_item_all_metadata(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(
        dashboard_id="42",
        title="taco",
        description="burrito",
        url="https://foo.bar",
        custom_title="customtaco",
        custom_description="customburrito",
        custom_url="https://custom.foo.bar",
        order=5,
        use_custom_image=True,
        lookml_dashboard_id="my_dash"
    )
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)
    expected_payload = {
        "board_section_id": "10",
        "dashboard_id": "1",
        "title": "taco",
        "description": "burrito",
        "url": "https://foo.bar",
        "custom_title": "customtaco",
        "custom_description": "customburrito",
        "custom_url": "https://custom.foo.bar",
        "order": 5,
        "use_custom_image": True,
        "lookml_dashboard_id": "my_dash"
    }
    mock_run_subprocess_command.assert_any_call(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps(expected_payload)
    )


def test_audit_board_with_misses(mock_run_subprocess_command, mocker):
    test_board = MockBoard()
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", side_effect=AssertionError)
    mocker.patch("looker_deployer.commands.deploy_boards.match_look_id", side_effect=AssertionError)

    def mock_run(cmd, **kwargs):
        if "dashboard" in cmd and "get" in cmd:
            return MockCompletedProcess(json.dumps({"title": "foobarbaz"}))
        if "look" in cmd and "get" in cmd:
            return MockCompletedProcess(json.dumps({"title": "foobarbaz"}))
        return MockCompletedProcess()

    mock_run_subprocess_command.side_effect = mock_run

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    missing = deploy_boards.audit_board_content(test_board, source_creds, target_creds)
    assert missing == ([{"dash_id": 2, "dash_title": "foobarbaz"}], [{"look_id": 1, "look_title": "foobarbaz"}])


def test_audit_board_no_misses(mocker):
    test_board = MockBoard()
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id")
    mocker.patch("looker_deployer.commands.deploy_boards.match_look_id")
    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    missing = deploy_boards.audit_board_content(test_board, source_creds, target_creds)
    assert missing == ([], [])


def test_create_board_item_stress_properties(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(
        dashboard_id="42",
        board_section_id=99,
        id=123,
        title="taco",
        description="burrito",
        url="https://foo.bar",
        custom_title="customtaco",
        custom_description="customburrito",
        custom_url="https://custom.foo.bar",
        order=5,
        use_custom_image=False,
        lookml_dashboard_id="lookml_dash_1",
        is_random_boolean=True,
        another_random_field="ignored"
    )
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)

    expected_payload = {
        "board_section_id": "10",
        "dashboard_id": "1",
        "title": "taco",
        "description": "burrito",
        "url": "https://foo.bar",
        "custom_title": "customtaco",
        "custom_description": "customburrito",
        "custom_url": "https://custom.foo.bar",
        "order": 5,
        "use_custom_image": False,
        "lookml_dashboard_id": "lookml_dash_1"
    }

    mock_run_subprocess_command.assert_any_call(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps(expected_payload)
    )

    last_call = mock_run_subprocess_command.call_args
    passed_input = json.loads(last_call[1]["input"])
    assert "is_random_boolean" not in passed_input
    assert "another_random_field" not in passed_input


def test_stress_vars_leak(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(
        dashboard_id="42",
        board_section_id=99,
        id=123,
        title="taco",
        can={"create": True, "read": True},
        url="https://readonly.url",
        _private_attr="secret",
        class_name="MockItem",
        board_id=77,
        content_metadata_id=999
    )
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)

    expected_payload = {
        "board_section_id": "10",
        "dashboard_id": "1",
        "title": "taco",
        "url": "https://readonly.url"
    }
    mock_run_subprocess_command.assert_called_once_with(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps(expected_payload)
    )


def test_create_board_item_empty_and_null_properties(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(
        dashboard_id="42",
        title="",
        description=None,
        custom_title="",
        custom_description="hello",
        url=""
    )
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)

    expected_payload = {
        "board_section_id": "10",
        "dashboard_id": "1",
        "title": "",
        "url": "",
        "custom_title": "",
        "custom_description": "hello"
    }
    mock_run_subprocess_command.assert_called_once_with(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps(expected_payload)
    )


def test_create_board_item_very_long_strings(mock_run_subprocess_command, mocker):
    long_title = "A" * 10000
    long_description = "B" * 10000
    test_board_item = SimpleNamespace(
        dashboard_id="42",
        title=long_title,
        description=long_description
    )
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)

    expected_payload = {
        "board_section_id": "10",
        "dashboard_id": "1",
        "title": long_title,
        "description": long_description
    }
    mock_run_subprocess_command.assert_called_once_with(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps(expected_payload)
    )


def test_create_board_item_nested_types(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(
        dashboard_id="42",
        title="taco",
        custom_description={"key": "value", "list": [1, 2, 3]},
        custom_title=SimpleNamespace(name="nested_namespace", val=99)
    )
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)

    expected_payload = {
        "board_section_id": "10",
        "dashboard_id": "1",
        "title": "taco",
        "custom_title": {"name": "nested_namespace", "val": 99},
        "custom_description": {"key": "value", "list": [1, 2, 3]}
    }
    mock_run_subprocess_command.assert_called_once_with(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps(expected_payload)
    )


def test_create_board_item_extremely_long_strings(mock_run_subprocess_command, mocker):
    long_str = "a" * 10000
    test_board_item = SimpleNamespace(
        dashboard_id="42",
        title=long_str,
        description=long_str
    )
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)

    expected_payload = {
        "board_section_id": "10",
        "dashboard_id": "1",
        "title": long_str,
        "description": long_str
    }
    mock_run_subprocess_command.assert_called_once_with(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps(expected_payload)
    )


def test_create_board_item_empty_strings(mock_run_subprocess_command, mocker):
    test_board_item = SimpleNamespace(
        dashboard_id="42",
        title="",
        description="",
        url=""
    )
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)

    expected_payload = {
        "board_section_id": "10",
        "dashboard_id": "1",
        "title": "",
        "description": "",
        "url": ""
    }
    mock_run_subprocess_command.assert_called_once_with(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps(expected_payload)
    )


def test_create_board_item_extreme_order_values(mock_run_subprocess_command, mocker):
    orders = [0, -5, 2147483647]
    for order in orders:
        test_board_item = SimpleNamespace(
            dashboard_id="42",
            order=order
        )
        mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
        mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

        source_creds = {"base_url": "source"}
        target_creds = {"base_url": "target"}
        deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)

        expected_payload = {
            "board_section_id": "10",
            "dashboard_id": "1",
            "order": order
        }
        mock_run_subprocess_command.assert_called_with(
            ["looker-cli", "api", "board", "create_board_item", "-"],
            creds=target_creds,
            text=True,
            input=json.dumps(expected_payload)
        )


def test_create_board_item_complex_types(mock_run_subprocess_command, mocker):
    nested_namespace = SimpleNamespace(nested_field="nested_value")
    test_board_item = SimpleNamespace(
        dashboard_id="42",
        title={"dict_key": "dict_value"},
        description=["list_item_1", "list_item_2"],
        custom_title=nested_namespace
    )
    mocker.patch("looker_deployer.commands.deploy_boards.match_dashboard_id", return_value="1")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 5}))

    source_creds = {"base_url": "source"}
    target_creds = {"base_url": "target"}
    deploy_boards.create_board_item(test_board_item, 10, source_creds, target_creds)

    expected_payload = {
        "board_section_id": "10",
        "dashboard_id": "1",
        "title": {"dict_key": "dict_value"},
        "description": ["list_item_1", "list_item_2"],
        "custom_title": {"nested_field": "nested_value"}
    }
    mock_run_subprocess_command.assert_called_once_with(
        ["looker-cli", "api", "board", "create_board_item", "-"],
        creds=target_creds,
        text=True,
        input=json.dumps(expected_payload)
    )


def test_create_board_section_adversarial(mock_run_subprocess_command):
    # Test section with title as None
    test_board_section = SimpleNamespace(title=None, description="")
    mock_run_subprocess_command.return_value = MockCompletedProcess(json.dumps({"id": 4}))

    target_creds = {"base_url": "target"}
    deploy_boards.create_board_section(test_board_section, 1, target_creds)
    mock_run_subprocess_command.assert_called_with(
        ["looker-cli", "api", "board", "create_board_section", "-"],
        creds=target_creds, text=True, input=json.dumps({"board_id": "1", "title": None})
    )

    # Test section with empty string description -> should not pass description since it's falsy
    test_board_section_2 = SimpleNamespace(title="taco", description="")
    deploy_boards.create_board_section(test_board_section_2, 1, target_creds)
    mock_run_subprocess_command.assert_called_with(
        ["looker-cli", "api", "board", "create_board_section", "-"],
        creds=target_creds, text=True, input=json.dumps({"board_id": "1", "title": "taco"})
    )
