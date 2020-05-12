import pytest
import os
import subprocess
from looker_sdk import methods, models
from looker_deployer.commands import deploy_content
from looker_deployer.utils import parse_ini

sdk = methods.LookerSDK("foo", "bar", "baz", "bosh")

INI = {
    "taco": {
        "base_url": "https://foobarbaz.com:1234",
        "client_id": "abc",
        "client_secret": "xyz"
    }
}


def test_get_space_ids_from_name_shared(mocker):
    mocker.patch.object(sdk, "search_spaces")
    id_list = deploy_content.get_space_ids_from_name("Shared", "0", sdk)
    assert id_list == ["1"]


def test_get_space_ids_from_name_not_shared(mocker):
    mocker.patch.object(sdk, "search_spaces")
    sdk.search_spaces.return_value = [models.Space(name="Foo", parent_id="1", id="42")]
    id_list = deploy_content.get_space_ids_from_name("foo", "0", sdk)
    assert id_list == ["42"]


def test_create_or_return_space_one_found(mocker):
    mocker.patch("deploy_content.get_space_ids_from_name")
    deploy_content.get_space_ids_from_name.return_value = ["42"]
    target_id = deploy_content.create_or_return_space("foo", "bar", "baz")
    assert target_id == "42"


def test_create_or_return_space_multi_found(mocker):
    mocker.patch("deploy_content.get_space_ids_from_name")
    deploy_content.get_space_ids_from_name.return_value = ["42", "13"]
    with pytest.raises(AssertionError):
        deploy_content.create_or_return_space("foo", "bar", "baz")


def test_create_or_return_space_none_found(mocker):
    mocker.patch.object(sdk, "create_space")
    mocker.patch("deploy_content.get_space_ids_from_name")
    sdk.create_space.return_value = models.Space(name="Foo", parent_id="1", id="42")
    deploy_content.get_space_ids_from_name.return_value = []

    target_id = deploy_content.create_or_return_space("foo", "2", sdk)
    assert target_id == "42"


def test_get_gzr_creds(mocker):
    mocker.patch("utils.parse_ini.read_ini")
    parse_ini.read_ini.return_value = INI
    tup = deploy_content.get_gzr_creds("foo", "taco")
    assert tup == ("foobarbaz.com", "abc", "xyz")


def test_export_space(mocker):
    mocker.patch("deploy_content.get_gzr_creds")
    deploy_content.get_gzr_creds.return_value = ("foobar.com", "abc", "xyz")

    mocker.patch("subprocess.call")
    deploy_content.export_spaces("env", "ini", "foo/bar")
    subprocess.call.assert_called_with([
        "gzr",
        "space",
        "export",
        "1",
        "--dir",
        "foo/bar",
        "--host",
        "foobar.com",
        "--client-id",
        "abc",
        "--client-secret",
        "xyz"
    ])


def test_import_content(mocker):
    mocker.patch("deploy_content.get_gzr_creds")
    deploy_content.get_gzr_creds.return_value = ("foobar.com", "abc", "xyz")

    mocker.patch("subprocess.call")
    deploy_content.import_content("dashboard", "tacocat.json", "42", "env", "ini")
    subprocess.call.assert_called_with([
        "gzr",
        "dashboard",
        "import",
        "tacocat.json",
        "42",
        "--host",
        "foobar.com",
        "--client-id",
        "abc",
        "--client-secret",
        "xyz",
        "--force"
    ])


def test_build_spaces(mocker):
    mocker.patch("deploy_content.create_or_return_space")
    deploy_content.create_or_return_space.return_value = "42"
    space_id = deploy_content.build_spaces(["taco"], sdk)
    assert space_id == "42"


def test_deploy_space_build_call(mocker):

    mocker.patch("os.listdir")
    mocker.patch("os.path.isfile")
    mocker.patch("os.path.isdir")

    os.listdir.return_value = ["Dashboard", "Look"]
    os.path.isfile.return_value = True
    os.path.isdir.return_value = True

    mocker.patch("deploy_content.build_spaces")
    mocker.patch("deploy_content.import_content")
    deploy_content.deploy_space("Foo/Shared/Bar/", "sdk", "env", "ini", False)
    deploy_content.build_spaces.assert_called_with(["Shared", "Bar"], "sdk")


def test_deploy_space_look_call(mocker):

    mocker.patch("os.listdir")
    mocker.patch("os.path.isfile")
    mocker.patch("os.path.isdir")

    os.listdir.return_value = ["Look_test"]
    os.path.isfile.return_value = True
    os.path.isdir.return_value = True

    mocker.patch("deploy_content.build_spaces")
    deploy_content.build_spaces.return_value = "42"

    mocker.patch("deploy_content.import_content")
    deploy_content.deploy_space("Foo/Shared/Bar", "sdk", "env", "ini", False)
    deploy_content.import_content.assert_called_once_with("look", "Foo/Shared/Bar/Look_test", "42", "env", "ini")


def test_deploy_space_dashboard_call(mocker):

    mocker.patch("os.listdir")
    mocker.patch("os.path.isfile")
    mocker.patch("os.path.isdir")

    os.listdir.return_value = ["Dashboard_test"]
    os.path.isfile.return_value = True
    os.path.isdir.return_value = True

    mocker.patch("deploy_content.build_spaces")
    deploy_content.build_spaces.return_value = "42"

    mocker.patch("deploy_content.import_content")
    deploy_content.deploy_space("Foo/Shared/Bar", "sdk", "env", "ini", False)
    deploy_content.import_content.assert_called_once_with(
        "dashboard",
        "Foo/Shared/Bar/Dashboard_test",
        "42",
        "env",
        "ini"
    )


def test_deploy_content_build_call(mocker):

    mocker.patch("deploy_content.build_spaces")
    mocker.patch("deploy_content.import_content")
    deploy_content.deploy_content("look", "Foo/Shared/Bar/Baz/Dashboard_test.json", "sdk", "env", "ini")
    deploy_content.build_spaces.assert_called_with(["Shared", "Bar", "Baz"], "sdk")


def test_deploy_content_import_content_call(mocker):
    mocker.patch("deploy_content.build_spaces")
    deploy_content.build_spaces.return_value = "42"

    mocker.patch("deploy_content.import_content")
    deploy_content.deploy_content("look", "Foo/Shared/Bar/Look_test.json", "sdk", "env", "ini")
    deploy_content.import_content.assert_called_with("look", "Foo/Shared/Bar/Look_test.json", "42", "env", "ini")
