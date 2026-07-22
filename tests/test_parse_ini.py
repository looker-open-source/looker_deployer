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
from looker_deployer.utils.parse_ini import build_creds


def test_build_creds_missing_section(mocker):
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("os.access", return_value=True)
    mocker.patch("looker_deployer.utils.parse_ini.read_ini", return_value={"other": {}})
    mocker.patch("os.environ", {})
    with pytest.raises(KeyError, match="Could not find section foo in dummy.ini"):
        build_creds("dummy.ini", "foo")


def test_build_creds_success_case_sensitive(mocker):
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("os.access", return_value=True)
    mocker.patch("looker_deployer.utils.parse_ini.read_ini", return_value={
        "foo": {"base_url": "url1", "client_id": "id1", "client_secret": "sec1", "verify_ssl": "true"}
    })
    mocker.patch("os.environ", {})
    creds = build_creds("dummy.ini", "foo")
    assert creds["base_url"] == "url1"
    assert creds["client_id"] == "id1"
    assert creds["client_secret"] == "sec1"
    assert creds["verify_ssl"] == "true"


def test_build_creds_success_capitalized(mocker):
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch("os.access", return_value=True)
    mocker.patch("looker_deployer.utils.parse_ini.read_ini", return_value={
        "Foo": {"base_url": "url2", "client_id": "id2", "client_secret": "sec2"}
    })
    mocker.patch("os.environ", {})
    creds = build_creds("dummy.ini", "foo")
    assert creds["base_url"] == "url2"
    assert creds["client_id"] == "id2"
    assert creds["client_secret"] == "sec2"


def test_build_creds_fallback_to_env(mocker):
    mocker.patch("os.path.isfile", return_value=False)  # ini not found
    mocker.patch("os.environ", {
        "LOOKERSDK_BASE_URL": "env_url",
        "LOOKERSDK_CLIENT_ID": "env_id"
    })
    creds = build_creds(None, "foo")  # No ini passed
    assert creds["base_url"] == "env_url"
    assert creds["client_id"] == "env_id"
    assert "client_secret" not in creds
