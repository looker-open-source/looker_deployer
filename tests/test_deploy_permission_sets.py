from looker_deployer.commands import deploy_permission_sets
from looker_sdk import methods, models


class mockSettings:
    base_url = "taco"


class mockAuth:
    settings = mockSettings()


sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")


def test_get_filtered_permission_sets(mocker):
    permission_set_list = [
        models.PermissionSet(name="Taco"),
        models.PermissionSet(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_permission_sets")
    sdk.all_permission_sets.return_value = permission_set_list

    permission_sets = deploy_permission_sets.get_filtered_permission_sets(sdk)
    assert permission_sets == permission_set_list


def test_get_filtered_permission_sets_filter(mocker):
    permission_set_list = [
        models.PermissionSet(name="Taco"),
        models.PermissionSet(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_permission_sets")
    sdk.all_permission_sets.return_value = permission_set_list

    permission_sets = deploy_permission_sets.get_filtered_permission_sets(
        sdk, "Burrito")
    assert permission_sets == [models.PermissionSet(name="Burrito")]


def test_write_permission_sets_new(mocker):
    permission_set_list = [models.WritePermissionSet(name="Taco")]

    mocker.patch.object(sdk, "all_permission_sets")
    mocker.patch.object(sdk, "create_permission_set")

    deploy_permission_sets.write_permission_sets(permission_set_list, sdk)
    sdk.create_permission_set.assert_called_once_with(permission_set_list[0])


def test_write_permission_sets_existing(mocker):
    permission_set_list = [models.WritePermissionSet(name="Taco")]

    mocker.patch.object(sdk, "all_permission_sets")
    mocker.patch.object(sdk, "update_permission_set")

    sdk.all_permission_sets.return_value = [models.PermissionSet(
        name="Taco", id=1)]

    deploy_permission_sets.write_permission_sets(permission_set_list, sdk)
    sdk.update_permission_set.assert_called_once_with(
        1, permission_set_list[0])
