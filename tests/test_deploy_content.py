# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import os
import subprocess
from looker_sdk import methods, models
from looker_deployer.commands import deploy_content
from looker_deployer.utils import parse_ini


class mockSettings:
    base_url = "taco"


class mockAuth:
    settings = mockSettings()


sdk = methods.LookerSDK(mockAuth(), "bar", "baz", "bosh", "bizz")

TRUE_INI = {
    "taco": {
        "base_url": "https://phoobarbaz.com:1234",
        "client_id": "abc",
        "client_secret": "xyz",
        "verify_ssl": "True"
    }
}

FALSE_INI = {
    "taco": {
        "base_url": "https://phoobarbaz.com:1234",
        "client_id": "abc",
        "client_secret": "xyz",
        "verify_ssl": "False"
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
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name")
    deploy_content.get_space_ids_from_name.return_value = ["42"]
    target_id = deploy_content.create_or_return_space("foo", "bar", "baz")
    assert target_id == "42"


def test_create_or_return_space_multi_found(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name")
    deploy_content.get_space_ids_from_name.return_value = ["42", "13"]
    with pytest.raises(AssertionError):
        deploy_content.create_or_return_space("foo", "bar", "baz")


def test_create_or_return_space_none_found(mocker):
    mocker.patch.object(sdk, "create_space")
    mocker.patch("looker_deployer.commands.deploy_content.get_space_ids_from_name")
    sdk.create_space.return_value = models.Space(name="Foo", parent_id="1", id="42")
    deploy_content.get_space_ids_from_name.return_value = []

    target_id = deploy_content.create_or_return_space("foo", "5", sdk)
    assert target_id == "42"


def test_get_gzr_creds_true(mocker):
    mocker.patch("looker_deployer.utils.parse_ini.read_ini")
    parse_ini.read_ini.return_value = TRUE_INI
    tup = deploy_content.get_gzr_creds("foo", "taco")
    assert tup == ("phoobarbaz.com", "1234", "abc", "xyz", "True")


def test_get_gzr_creds_false(mocker):
    mocker.patch("looker_deployer.utils.parse_ini.read_ini")
    parse_ini.read_ini.return_value = FALSE_INI
    tup = deploy_content.get_gzr_creds("foo", "taco")
    assert tup == ("phoobarbaz.com", "1234", "abc", "xyz", "False")


def test_import_content(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_gzr_creds")
    deploy_content.get_gzr_creds.return_value = ("foobar.com", "1234", "abc", "xyz", "True")

    mocker.patch("subprocess.run")
    deploy_content.import_content("dashboard", "tacocat.json", "42", "env", "ini", False)
    subprocess.run.assert_called_with([
        "gzr",
        "dashboard",
        "import",
        "tacocat.json",
        "42",
        "--host",
        "foobar.com",
        "--port",
        "1234",
        "--client-id",
        "abc",
        "--client-secret",
        "xyz",
        "--force"
    ])


def test_import_content_debug(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_gzr_creds")
    deploy_content.get_gzr_creds.return_value = ("foobar.com", "1234", "abc", "xyz", "True")

    mocker.patch("subprocess.run")
    deploy_content.import_content("dashboard", "tacocat.json", "42", "env", "ini", True)
    subprocess.run.assert_called_with([
        "gzr",
        "dashboard",
        "import",
        "tacocat.json",
        "42",
        "--host",
        "foobar.com",
        "--port",
        "1234",
        "--client-id",
        "abc",
        "--client-secret",
        "xyz",
        "--force",
        "--debug"
    ])


def test_import_content_no_verify_ssl(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_gzr_creds")
    deploy_content.get_gzr_creds.return_value = ("foobar.com", "1234", "abc", "xyz", "False")

    mocker.patch("subprocess.run")
    deploy_content.import_content("dashboard", "tacocat.json", "42", "env", "ini", False)
    subprocess.run.assert_called_with([
        "gzr",
        "dashboard",
        "import",
        "tacocat.json",
        "42",
        "--host",
        "foobar.com",
        "--port",
        "1234",
        "--client-id",
        "abc",
        "--client-secret",
        "xyz",
        "--force",
        "--no-verify-ssl"
    ])


def test_import_content_win(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.get_gzr_creds")
    deploy_content.get_gzr_creds.return_value = ("foobar.com", "1234", "abc", "xyz", "True")

    mocker.patch("os.name", "nt")

    mocker.patch("subprocess.run")
    deploy_content.import_content("dashboard", "tacocat.json", "42", "env", "ini", False)
    subprocess.run.assert_called_with([
        "cmd.exe",
        "/c",
        "gzr",
        "dashboard",
        "import",
        "tacocat.json",
        "42",
        "--host",
        "foobar.com",
        "--port",
        "1234",
        "--client-id",
        "abc",
        "--client-secret",
        "xyz",
        "--force"
    ])


def test_build_spaces(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.create_or_return_space")
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

    mocker.patch("looker_deployer.commands.deploy_content.build_spaces")
    mocker.patch("looker_deployer.commands.deploy_content.import_content")
    deploy_content.deploy_space("Foo/Shared/Bar/", "sdk", "env", "ini", False)
    deploy_content.build_spaces.assert_called_with(["Shared", "Bar"], "sdk")


def test_deploy_space_look_call(mocker):

    mocker.patch("os.listdir")
    mocker.patch("os.path.isfile")
    mocker.patch("os.path.isdir")

    os.listdir.return_value = ["Look_test"]
    os.path.isfile.return_value = True
    os.path.isdir.return_value = True

    mocker.patch("looker_deployer.commands.deploy_content.build_spaces")
    deploy_content.build_spaces.return_value = "42"

    mocker.patch("looker_deployer.commands.deploy_content.import_content")
    deploy_content.deploy_space("Foo/Shared/Bar", "sdk", "env", "ini", False)
    deploy_content.import_content.assert_called_once_with("look", "Foo/Shared/Bar/Look_test", "42", "env", "ini", False)


def test_deploy_space_dashboard_call(mocker):

    mocker.patch("os.listdir")
    mocker.patch("os.path.isfile")
    mocker.patch("os.path.isdir")

    os.listdir.return_value = ["Dashboard_test"]
    os.path.isfile.return_value = True
    os.path.isdir.return_value = True

    mocker.patch("looker_deployer.commands.deploy_content.build_spaces")
    deploy_content.build_spaces.return_value = "42"

    mocker.patch("looker_deployer.commands.deploy_content.import_content")
    deploy_content.deploy_space("Foo/Shared/Bar", "sdk", "env", "ini", False, False)
    deploy_content.import_content.assert_called_once_with(
        "dashboard",
        "Foo/Shared/Bar/Dashboard_test",
        "42",
        "env",
        "ini",
        False
    )


def test_deploy_content_build_call(mocker):

    mocker.patch("looker_deployer.commands.deploy_content.build_spaces")
    mocker.patch("looker_deployer.commands.deploy_content.import_content")
    deploy_content.deploy_content("look", "Foo/Shared/Bar/Baz/Dashboard_test.json", "sdk", "env", "ini", False)
    deploy_content.build_spaces.assert_called_with(["Shared", "Bar", "Baz"], "sdk")


def test_deploy_content_import_content_call(mocker):
    mocker.patch("looker_deployer.commands.deploy_content.build_spaces")
    deploy_content.build_spaces.return_value = "42"

    mocker.patch("looker_deployer.commands.deploy_content.import_content")
    deploy_content.deploy_content("look", "Foo/Shared/Bar/Look_test.json", "sdk", "env", "ini", False)
    deploy_content.import_content.assert_called_with("look", "Foo/Shared/Bar/Look_test.json", "42", "env", "ini", False)
