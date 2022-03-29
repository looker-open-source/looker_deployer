from looker_deployer.commands import deploy_user_attributes
from looker_sdk import methods, models


class mockSettings:
    base_url = "taco"


class mockAuth:
    settings = mockSettings()


def mock_responses(responses, default_response=None):
    return lambda input: responses[input] \
        if input in responses else default_response


sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")
source_sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")
target_sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")


def test_get_filtered_user_attributes(mocker):
    user_attribute_list = [
        models.UserAttribute(name="Cheese", id=1),
        models.UserAttribute(name="Sauce", id=2)
    ]

    mocker.patch.object(sdk, "all_user_attributes")
    sdk.all_user_attributes.return_value = user_attribute_list

    user_attributes = deploy_user_attributes.get_filtered_user_attributes(sdk)
    assert user_attributes == user_attribute_list


def test_get_filtered_user_attributes_filter(mocker):
    user_attribute_list = [
        models.UserAttribute(name="Cheese", id=1),
        models.UserAttribute(name="Sauce", id=2)
    ]

    mocker.patch.object(sdk, "all_user_attributes")
    sdk.all_user_attributes.return_value = user_attribute_list

    user_attributes = deploy_user_attributes.get_filtered_user_attributes(
        sdk, "Cheese")
    assert user_attributes == [user_attribute_list[0]]


def test_write_user_attributes_new(mocker):
    user_attribute_list = [
        models.UserAttribute(name="Cheese", id=1, is_system=False)
    ]
    user_attribute_group_list = [models.UserAttributeGroupValue(
        id=1, group_id=1, user_attribute_id=1)]
    group_1 = models.Group(name="Taco", id=1)
    group_2 = models.Group(name="Taco Supreme", id=2)
    groups_list = [group_1, group_2]
    role_1 = models.Role(name="Explorer", id=1)
    role_list = [role_1]

    mocker.patch.object(source_sdk, "all_roles")
    mocker.patch.object(source_sdk, "all_groups")
    mocker.patch.object(source_sdk, "group")
    mocker.patch.object(source_sdk, "all_user_attributes")
    mocker.patch.object(source_sdk, "all_user_attribute_group_values")

    mocker.patch.object(target_sdk, "all_roles")
    mocker.patch.object(target_sdk, "all_groups")
    mocker.patch.object(target_sdk, "all_user_attributes")
    mocker.patch.object(target_sdk, "create_user_attribute")
    mocker.patch.object(target_sdk, "set_user_attribute_group_values")

    source_sdk.all_roles.return_value = role_list
    target_sdk.all_roles.return_value = role_list
    source_sdk.all_groups.return_value = groups_list
    target_sdk.all_groups.return_value = groups_list
    source_sdk.group.return_value = group_1
    source_sdk.all_user_attributes.return_value = user_attribute_list
    source_sdk.all_user_attribute_group_values.side_effect = mock_responses(
        {
            1: user_attribute_group_list,
            2: []
        }
    )

    deploy_user_attributes.write_user_attributes(source_sdk, target_sdk)
    target_sdk.create_user_attribute.assert_called_once_with(
        models.WriteUserAttribute(name="Cheese"))


def test_write_user_attributes_update_group_value(mocker):
    user_attribute_list = [
        models.UserAttribute(name="Cheese", id=1),
        models.UserAttribute(name="Sauce", id=2)
    ]
    user_attribute_group_list = [models.UserAttributeGroupValue(
        id=1, group_id=1, user_attribute_id=1)]
    group_1 = models.Group(name="Taco", id=1)
    group_2 = models.Group(name="Taco Supreme", id=2)
    groups_list = [group_1, group_2]
    role_1 = models.Role(name="Explorer", id=1)
    role_list = [role_1]

    mocker.patch.object(source_sdk, "all_roles")
    mocker.patch.object(source_sdk, "all_groups")
    mocker.patch.object(source_sdk, "group")
    mocker.patch.object(source_sdk, "all_user_attributes")
    mocker.patch.object(source_sdk, "all_user_attribute_group_values")

    mocker.patch.object(target_sdk, "all_roles")
    mocker.patch.object(target_sdk, "all_groups")
    mocker.patch.object(target_sdk, "all_user_attributes")
    mocker.patch.object(target_sdk, "create_user_attribute")
    mocker.patch.object(target_sdk, "set_user_attribute_group_values")

    source_sdk.all_roles.return_value = role_list
    target_sdk.all_roles.return_value = role_list
    source_sdk.all_groups.return_value = groups_list
    target_sdk.all_groups.return_value = groups_list
    source_sdk.group.return_value = group_1
    source_sdk.all_user_attributes.return_value = user_attribute_list
    source_sdk.all_user_attribute_group_values.side_effect = mock_responses(
        {
            1: user_attribute_group_list,
            2: []
        }
    )
    target_sdk.create_user_attribute.return_value = user_attribute_list[0]

    deploy_user_attributes.write_user_attributes(source_sdk, target_sdk)
    target_sdk.set_user_attribute_group_values.assert_called_once_with(
        user_attribute_id=1, body=user_attribute_group_list)
