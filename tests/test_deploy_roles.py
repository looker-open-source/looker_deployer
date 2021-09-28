from looker_sdk.rtl import model
from looker_sdk.sdk.api31.models import PermissionSet
from looker_deployer.commands import deploy_roles
from looker_sdk import methods, models


class mockSettings:
    base_url = "taco"


class mockAuth:
    settings = mockSettings()


sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")


def test_get_filtered_roles(mocker):
    role_list = [
        models.Role(name="Taco"),
        models.Role(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_roles")
    sdk.all_roles.return_value = role_list

    roles = deploy_roles.get_filtered_roles(sdk)
    assert roles == role_list


def test_get_filtered_roles_filter(mocker):
    role_list = [
        models.Role(name="Taco"),
        models.Role(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_roles")
    sdk.all_roles.return_value = role_list

    roles = deploy_roles.get_filtered_roles(sdk, "Burrito")
    assert roles == [models.Role(name="Burrito")]


def test_write_roles_new(mocker):
    permission_set = models.PermissionSet(name="P1",id=1)
    model_set = models.ModelSet(name="M1",id=1)
    role_list = [models.WriteRole(name="Taco",permission_set=permission_set,model_set=model_set, permission_set_id=1,model_set_id=1)]


    mocker.patch.object(sdk, "all_roles")
    mocker.patch.object(sdk, "create_role")
    mocker.patch.object(sdk, "all_permission_sets")
    mocker.patch.object(sdk, "all_model_sets")

    sdk.all_permission_sets.return_value = [models.PermissionSet(name="P1",id=1)]
    sdk.all_model_sets.return_value = [models.ModelSet(name="M1",id=1)]

    deploy_roles.write_roles(role_list,sdk)
    sdk.create_role.assert_called_once_with(role_list[0])


def test_write_roles_existing(mocker):
    permission_set = models.PermissionSet(name="P1",id=1)
    model_set = models.ModelSet(name="M1",id=1)
    role_list = [models.WriteRole(name="Taco",permission_set=permission_set,model_set=model_set, permission_set_id=1,model_set_id=1)]

    mocker.patch.object(sdk, "all_roles")
    mocker.patch.object(sdk, "update_role")
    mocker.patch.object(sdk, "all_permission_sets")
    mocker.patch.object(sdk, "all_model_sets")

    sdk.all_roles.return_value = [models.Role(name="Taco",permission_set=permission_set,model_set=model_set, permission_set_id=1,model_set_id=1,id=1)]
    sdk.all_permission_sets.return_value = [models.PermissionSet(name="P1",id=1)]
    sdk.all_model_sets.return_value = [models.ModelSet(name="M1",id=1)]

    deploy_roles.write_roles(role_list,sdk)
    sdk.update_role.assert_called_once_with(1,role_list[0])