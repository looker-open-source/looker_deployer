from looker_deployer.commands import deploy_connections
from looker_sdk import methods, models, error


class mockSettings:
    base_url = "taco"


class mockAuth:
    settings = mockSettings()


sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")


def test_get_filtered_connections(mocker):
    conn_list = [
        models.DBConnection(name="Taco"),
        models.DBConnection(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_connections")
    sdk.all_connections.return_value = conn_list

    conns = deploy_connections.get_filtered_connections(sdk)
    assert conns == conn_list


def test_get_filtered_connections_filter(mocker):
    conn_list = [
        models.DBConnection(name="Taco"),
        models.DBConnection(name="Burrito")
    ]

    mocker.patch.object(sdk, "all_connections")
    sdk.all_connections.return_value = conn_list

    conns = deploy_connections.get_filtered_connections(sdk, "Burrito")
    assert conns == [models.DBConnection(name="Burrito")]


def test_write_connections_new(mocker):
    conn_list = [models.WriteDBConnection(name="Taco")]

    mocker.patch.object(sdk, "connection", side_effect=error.SDKError("mocked error"))
    mocker.patch.object(sdk, "create_connection")

    deploy_connections.write_connections(conn_list, sdk)
    sdk.create_connection.assert_called_once_with(conn_list[0])


def test_write_connections_existing(mocker):
    conn_list = [models.WriteDBConnection(name="Taco")]

    mocker.patch.object(sdk, "connection")
    mocker.patch.object(sdk, "update_connection")

    sdk.connection.return_value = "foo"

    deploy_connections.write_connections(conn_list, sdk)
    sdk.update_connection.assert_called_once_with("Taco", conn_list[0])


def test_write_connections_update_pw_existing(mocker):
    conn_list = [models.WriteDBConnection(name="Taco")]
    conf = {"Taco": "Cat"}

    mocker.patch.object(sdk, "connection")
    mocker.patch.object(sdk, "update_connection")

    sdk.connection.return_value = "foo"

    deploy_connections.write_connections(conn_list, sdk, conf)
    sdk.update_connection.assert_called_once_with("Taco", models.WriteDBConnection(name="Taco", password="Cat"))


def test_write_connections_update_pw_new(mocker):
    conn_list = [models.WriteDBConnection(name="Taco")]
    conf = {"Taco": "Cat"}

    mocker.patch.object(sdk, "connection", side_effect=error.SDKError("mocked error"))
    mocker.patch.object(sdk, "create_connection")

    deploy_connections.write_connections(conn_list, sdk, conf)
    sdk.create_connection.assert_called_once_with(models.WriteDBConnection(name="Taco", password="Cat"))
