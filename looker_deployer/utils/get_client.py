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

from looker_deployer import version
from looker_sdk import api_settings, methods, requests_transport, auth_session, serialize, _settings
from typing import Optional


def configure_sdk(
    config_file: str = "looker.ini",
    section: Optional[str] = None,
    config_settings: Optional[api_settings.ApiSettings] = None,
) -> methods.Looker31SDK:
    """Default dependency configuration"""
    settings = (
        _settings(config_file, section) if config_settings is None else config_settings
    )
    settings.is_configured()
    settings.headers['User-Agent'] = f"Looker Deployer {version.__version__}"
    transport = requests_transport.RequestsTransport.configure(settings)
    return methods.Looker31SDK(
        auth_session.AuthSession(settings, transport, serialize.deserialize31, "3.1"),
        serialize.deserialize31,
        serialize.serialize31,
        transport,
        "3.1",
    )


def get_client(ini, env):
    sdk = configure_sdk(config_file=ini, section=env)
    return sdk
