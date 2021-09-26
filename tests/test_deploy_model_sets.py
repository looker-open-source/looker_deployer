from looker_deployer.commands import deploy_model_sets
from looker_sdk import methods, models, error


class mockSettings:
    base_url = "taco"


class mockAuth:
    settings = mockSettings()


sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")


def test_get_filtered_model_sets(mocker):
    model_set_list = [
        models.ModelSet(name="Taco"),
        models.ModelSet(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_model_sets")
    sdk.all_model_sets.return_value = model_set_list

    model_sets = deploy_model_sets.get_filtered_model_sets(sdk)
    assert model_sets == model_set_list


def test_get_filtered_model_sets_filter(mocker):
    model_set_list = [
        models.ModelSet(name="Taco"),
        models.ModelSet(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_model_sets")
    sdk.all_model_sets.return_value = model_set_list

    model_sets = deploy_model_sets.get_filtered_model_sets(sdk, "Burrito")
    assert model_sets == [models.ModelSet(name="Burrito")]


def test_write_model_sets_new(mocker):
    model_set_list = [models.WriteModelSet(name="Taco")]

    mocker.patch.object(sdk, "all_model_sets")
    mocker.patch.object(sdk, "create_model_set")

    deploy_model_sets.write_model_sets(model_set_list,sdk)
    sdk.create_model_set.assert_called_once_with(model_set_list[0])


def test_write_model_sets_existing(mocker):
    model_set_list = [models.WriteModelSet(name="Taco")]

    mocker.patch.object(sdk, "all_model_sets")
    mocker.patch.object(sdk, "update_model_set")
    
    sdk.all_model_sets.return_value = [models.ModelSet(name="Taco",id=1)]
    
    deploy_model_sets.write_model_sets(model_set_list,sdk)
    sdk.update_model_set.assert_called_once_with(1, model_set_list[0])