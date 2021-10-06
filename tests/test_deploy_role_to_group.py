from looker_deployer.commands import deploy_role_to_group
from looker_sdk import methods, models


class mockSettings:
    base_url = "taco"


class mockAuth:
    settings = mockSettings()


sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")
source_sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")
target_sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")


def test_get_filtered_roles(mocker):
    role_list = [
        models.Role(name="Taco"),
        models.Role(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_roles")
    sdk.all_roles.return_value = role_list

    roles = deploy_role_to_group.get_filtered_roles(sdk)
    assert roles == role_list


def test_get_filtered_roles_filter(mocker):
    role_list = [
        models.Role(name="Taco"),
        models.Role(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_roles")
    sdk.all_roles.return_value = role_list

    roles = deploy_role_to_group.get_filtered_roles(sdk, "Burrito")
    assert roles == [models.Role(name="Burrito")]


def test_write_role_to_group_new(mocker):
    group_1 = models.Group(name="Taco", id=1)
    group_2 = models.Group(name="Taco Supreme", id=2)
    role = [models.Role(name="Explorer", id=1)]
    role_group = [group_1]
    groups_list = [group_1, group_2]

    mocker.patch.object(source_sdk, "all_roles")
    mocker.patch.object(source_sdk, "all_groups")
    mocker.patch.object(source_sdk, "role_groups")
    mocker.patch.object(target_sdk, "all_roles")
    mocker.patch.object(target_sdk, "all_groups")
    mocker.patch.object(target_sdk, "set_role_groups")

    source_sdk.all_roles.return_value = role
    target_sdk.all_roles.return_value = role
    source_sdk.all_groups.return_value = groups_list
    target_sdk.all_groups.return_value = groups_list
    source_sdk.role_groups.return_value = role_group

    deploy_role_to_group.write_role_to_group(source_sdk, target_sdk)
    target_sdk.set_role_groups.assert_called_once_with(
        role_id=role[0].id, body=[group_1.id])
