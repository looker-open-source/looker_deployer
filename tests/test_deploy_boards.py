import pytest
from looker_deployer.commands import deploy_boards
from looker_sdk import methods, models

sdk = methods.LookerSDK("foo", "bar", "baz", "bosh")


class MockLook:
    slug = "TacoCat"
    title = "foobarbaz"
    id = 1


class MockDash:
    slug = "BurritoCat"
    title = "foobarbaz"
    id = 2


class MockHomepageItem:
    id = 5


class MockHomepageSection:
    id = 4


class MockHomepage:
    id = 3
    title = "foo"
    description = "bar"
    homepage_sections = [MockHomepageSection()]


def test_match_dashboard_id(mocker):
    dash = MockDash()
    mocker.patch.object(sdk, "dashboard")
    sdk.dashboard.return_value = dash
    mocker.patch.object(sdk, "search_dashboards")
    sdk.search_dashboards.return_value = [dash]

    dash_id = deploy_boards.match_dashboard_id(1, sdk, sdk)
    assert dash_id == 2


def test_match_dashboard_id_multi(mocker):
    dash = MockDash()
    mocker.patch.object(sdk, "dashboard")
    sdk.dashboard.return_value = dash
    mocker.patch.object(sdk, "search_dashboards")
    sdk.search_dashboards.return_value = [dash, dash]

    with pytest.raises(AssertionError):
        deploy_boards.match_dashboard_id(1, sdk, sdk)


def test_match_look_id(mocker):
    look = MockLook()
    mocker.patch.object(sdk, "look")
    sdk.look.return_value = look
    mocker.patch.object(sdk, "search_looks")
    sdk.search_looks.return_value = [look]

    look_id = deploy_boards.match_look_id(1, sdk, sdk)
    assert look_id == 1


def test_match_look_id_multi(mocker):
    look = MockLook()
    mocker.patch.object(sdk, "look")
    sdk.look.return_value = look
    mocker.patch.object(sdk, "search_looks")
    sdk.search_looks.return_value = [look, look]

    with pytest.raises(AssertionError):
        deploy_boards.match_look_id(1, sdk, sdk)


def test_return_board(mocker):
    mocker.patch.object(sdk, "search_homepages")
    sdk.search_homepages.return_value = [42]
    board_id = deploy_boards.return_board("foo", sdk)
    assert board_id == 42


def test_return_board_multi(mocker):
    mocker.patch.object(sdk, "search_homepages")
    sdk.search_homepages.return_value = [42, 81]

    with pytest.raises(AssertionError):
        deploy_boards.return_board("foo", sdk)


def test_create_or_update_board_create(mocker):
    test_board = models.Homepage(title="taco", description="burrito")
    test_board_resp = MockHomepage()
    mocker.patch.object(sdk, "search_homepages")
    mocker.patch.object(sdk, "create_homepage")
    sdk.search_homepages.return_value = []
    sdk.create_homepage.return_value = test_board_resp
    board_id = deploy_boards.create_or_update_board(test_board, sdk)
    assert board_id == 3


def test_create_board_create_homepage_call(mocker):
    test_board = models.Homepage(title="taco", description="burrito", id=42)
    mocker.patch.object(sdk, "search_homepages")
    mocker.patch.object(sdk, "create_homepage")
    sdk.search_homepages.return_value = []
    deploy_boards.create_or_update_board(test_board, sdk)
    sdk.create_homepage.assert_called_with(models.Homepage(title="taco", description="burrito"))


def test_create_or_update_board_search_error(mocker):
    mocker.patch.object(sdk, "search_homepages")
    sdk.search_homepages.return_value = ["foo", "bar"]
    with pytest.raises(AssertionError):
        deploy_boards.create_or_update_board("foo", sdk)


def test_create_or_update_board_update(mocker):
    test_board = models.Homepage(title="taco", description="burrito")
    test_board_resp = MockHomepage()
    mocker.patch.object(sdk, "search_homepages")
    mocker.patch.object(sdk, "update_homepage")
    mocker.patch.object(sdk, "delete_homepage_section")
    sdk.search_homepages.return_value = [MockHomepage()]
    sdk.update_homepage.return_value = test_board_resp
    board_id = deploy_boards.create_or_update_board(test_board, sdk)
    assert board_id == 3


def test_create_or_update_board_update_homepage_call(mocker):
    test_board = models.Homepage(title="taco", description="burrito", id=42)
    mocker.patch.object(sdk, "search_homepages")
    mocker.patch.object(sdk, "update_homepage")
    mocker.patch.object(sdk, "delete_homepage_section")
    sdk.search_homepages.return_value = [MockHomepage()]
    deploy_boards.create_or_update_board(test_board, sdk)
    sdk.update_homepage.assert_called_with(3, models.Homepage(title="taco", description="burrito"))


def test_create_or_update_board_update_delete_call(mocker):
    test_board = models.Homepage(title="taco", description="burrito", id=42)
    mocker.patch.object(sdk, "search_homepages")
    mocker.patch.object(sdk, "update_homepage")
    mocker.patch.object(sdk, "delete_homepage_section")
    sdk.search_homepages.return_value = [MockHomepage()]
    deploy_boards.create_or_update_board(test_board, sdk)
    sdk.delete_homepage_section.assert_called()


def test_create_board_section(mocker):
    test_board_section = models.HomepageSection(title="taco", description="burrito")
    test_board_section_resp = MockHomepageSection()
    mocker.patch.object(sdk, "create_homepage_section")
    sdk.create_homepage_section.return_value = test_board_section_resp
    board_section_id = deploy_boards.create_board_section(test_board_section, 1, sdk)
    assert board_section_id == 4


def test_create_board_section_create_homepage_section_call(mocker):
    test_board_section = models.HomepageSection(
        title="taco",
        description="burrito",
        detail_url="foo",
        is_header=False,
        id="42"
    )
    mocker.patch.object(sdk, "create_homepage_section")
    deploy_boards.create_board_section(test_board_section, 1, sdk)

    sdk.create_homepage_section.assert_called_with(
        models.HomepageSection(
            title="taco",
            description="burrito",
            detail_url="foo",
            is_header=False,
            homepage_id=1
        )
    )


def test_create_board_item_dashboard(mocker):
    test_board_item = models.HomepageItem(title="taco", description="burrito", dashboard_id="42")
    test_board_item_resp = MockHomepageItem()
    mocker.patch("deploy_boards.match_dashboard_id")
    mocker.patch.object(sdk, "create_homepage_item")
    deploy_boards.match_dashboard_id.return_value = "1"
    sdk.create_homepage_item.return_value = test_board_item_resp
    board_item = deploy_boards.create_board_item(test_board_item, 1, sdk, sdk)
    assert board_item == test_board_item_resp


def test_create_board_item_look(mocker):
    test_board_item = models.HomepageItem(title="taco", description="burrito", look_id="42")
    test_board_item_resp = MockHomepageItem()
    mocker.patch("deploy_boards.match_look_id")
    mocker.patch.object(sdk, "create_homepage_item")
    deploy_boards.match_look_id.return_value = "1"
    sdk.create_homepage_item.return_value = test_board_item_resp
    board_item = deploy_boards.create_board_item(test_board_item, 1, sdk, sdk)
    assert board_item == test_board_item_resp


def test_create_board_item_dashboard_match_call(mocker):
    test_board_item = models.HomepageItem(title="taco", description="burrito", dashboard_id="42")
    mocker.patch("deploy_boards.match_dashboard_id")
    mocker.patch.object(sdk, "create_homepage_item")
    deploy_boards.create_board_item(test_board_item, 1, sdk, sdk)
    deploy_boards.match_dashboard_id.assert_called_with("42", sdk, sdk)


def test_create_board_item_look_match_call(mocker):
    test_board_item = models.HomepageItem(title="taco", description="burrito", look_id="42")
    mocker.patch("deploy_boards.match_look_id")
    mocker.patch.object(sdk, "create_homepage_item")
    deploy_boards.create_board_item(test_board_item, 1, sdk, sdk)
    deploy_boards.match_look_id.assert_called_with("42", sdk, sdk)


def test_create_board_item_dashboard_item_call(mocker):
    test_board_item = models.HomepageItem(title="taco", description="burrito", dashboard_id="42")
    mocker.patch("deploy_boards.match_dashboard_id")
    mocker.patch.object(sdk, "create_homepage_item")
    deploy_boards.match_dashboard_id.return_value = "1"
    deploy_boards.create_board_item(test_board_item, 10, sdk, sdk)
    sdk.create_homepage_item.assert_called_with(
        models.HomepageItem(
            title="taco",
            description="burrito",
            dashboard_id="1",
            url="/dashboards/1",
            homepage_section_id=10
        )
    )


def test_create_board_item_look_item_call(mocker):
    test_board_item = models.HomepageItem(title="taco", description="burrito", look_id="42")
    mocker.patch("deploy_boards.match_look_id")
    mocker.patch.object(sdk, "create_homepage_item")
    deploy_boards.match_look_id.return_value = "1"
    deploy_boards.create_board_item(test_board_item, 10, sdk, sdk)
    sdk.create_homepage_item.assert_called_with(
        models.HomepageItem(
            title="taco",
            description="burrito",
            look_id="1",
            url="/looks/1",
            homepage_section_id=10
        )
    )
