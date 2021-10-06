from looker_deployer.commands import deploy_groups
from looker_sdk import methods, models


class mockSettings:
    base_url = "taco"


class mockAuth:
    settings = mockSettings()


sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")


def test_get_filtered_groups(mocker):
    group_list = [
        models.Group(name="Taco"),
        models.Group(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_groups")
    sdk.all_groups.return_value = group_list

    groups = deploy_groups.get_filtered_groups(sdk)
    assert groups == group_list


def test_get_filtered_groups_filter(mocker):
    group_list = [
        models.Group(name="Taco"),
        models.Group(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_groups")
    sdk.all_groups.return_value = group_list

    groups = deploy_groups.get_filtered_groups(sdk, "Burrito")
    assert groups == [models.Group(name="Burrito")]


def test_write_groups_new(mocker):
    group_list = [models.WriteGroup(name="Taco")]

    mocker.patch.object(sdk, "all_groups")
    mocker.patch.object(sdk, "create_group")

    deploy_groups.write_groups(group_list, sdk)
    sdk.create_group.assert_called_once_with(group_list[0])


def test_write_groups_existing(mocker):
    group_list = [models.WriteGroup(name="Taco")]

    mocker.patch.object(sdk, "all_groups")
    mocker.patch.object(sdk, "update_group")

    sdk.all_groups.return_value = [models.Group(name="Taco", id=1)]

    deploy_groups.write_groups(group_list, sdk)
    sdk.update_group.assert_called_once_with(1, group_list[0])
