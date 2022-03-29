from looker_deployer.commands import deploy_group_in_group
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


def test_get_filtered_groups(mocker):
    group_list = [
        models.Group(name="Taco"),
        models.Group(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_groups")
    sdk.all_groups.return_value = group_list

    groups = deploy_group_in_group.get_filtered_groups(sdk)
    assert groups == group_list


def test_get_filtered_groups_filter(mocker):
    group_list = [
        models.Group(name="Taco"),
        models.Group(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_groups")
    sdk.all_groups.return_value = group_list

    groups = deploy_group_in_group.get_filtered_groups(sdk, "Burrito")
    assert groups == [models.Group(name="Burrito")]


def test_write_groups_in_group_new(mocker):
    group_1 = models.Group(name="Taco", id=1)
    group_2 = models.Group(name="Taco Supreme", id=2)
    groups_list = [group_1, group_2]
    group_in_group = [group_1]

    mocker.patch.object(source_sdk, "all_groups")
    mocker.patch.object(source_sdk, "all_group_groups")
    mocker.patch.object(target_sdk, "all_groups")
    mocker.patch.object(target_sdk, "all_group_groups")
    mocker.patch.object(target_sdk, "add_group_group")

    source_sdk.all_groups.return_value = groups_list
    target_sdk.all_groups.return_value = groups_list
    source_sdk.all_group_groups.side_effect = mock_responses(
      {
        1: [],
        2: group_in_group
      })

    deploy_group_in_group.write_groups_in_group(source_sdk, target_sdk)
    target_sdk.add_group_group.assert_called_once_with(
      group_id=group_2.id, body=models.GroupIdForGroupInclusion(group_id=1))


def test_write_groups_in_group_change(mocker):
    group_1 = models.Group(name="Taco", id=1)
    group_2 = models.Group(name="Taco Supreme", id=2)
    group_3 = models.Group(name="Chalupa", id=3)
    groups_list = [group_1, group_2, group_3]
    group_in_group = [group_1]

    mocker.patch.object(source_sdk, "all_groups")
    mocker.patch.object(source_sdk, "all_group_groups")
    mocker.patch.object(target_sdk, "all_groups")
    mocker.patch.object(target_sdk, "all_group_groups")
    mocker.patch.object(target_sdk, "add_group_group")
    mocker.patch.object(target_sdk, "delete_group_from_group")

    source_sdk.all_groups.return_value = groups_list
    target_sdk.all_groups.return_value = groups_list
    source_sdk.all_group_groups.side_effect = mock_responses(
        {
            1: [],
            2: [],
            3: group_in_group
        })
    target_sdk.all_group_groups.side_effect = mock_responses(
        {
            1: [],
            2: group_in_group,
            3: []
        })

    deploy_group_in_group.write_groups_in_group(source_sdk, target_sdk)
    target_sdk.delete_group_from_group.assert_called_once_with(
      group_id=group_2.id, deleting_group_id=1)
    target_sdk.add_group_group.assert_called_once_with(
      group_id=group_3.id, body=models.GroupIdForGroupInclusion(group_id=1))
