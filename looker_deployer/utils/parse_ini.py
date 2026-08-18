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

import configparser
import os
from looker_deployer.utils import deploy_logging

logger = deploy_logging.get_logger(__name__)


def read_ini(ini="../looker.ini"):
    config = configparser.ConfigParser()
    config.read(ini)

    return config


def build_creds(ini, env_name):
    """
    Builds a credentials dictionary for a given environment from an INI file.
    Falls back to environment variables if INI file is not available or doesn't have the section.
    """
    creds = {}
    # Default fallback to environment variables
    for k in ["base_url", "client_id", "client_secret", "verify_ssl"]:
        env_val = os.environ.get(f"LOOKERSDK_{k.upper()}")
        if env_val is not None:
            creds[k] = env_val

    if ini:
        if not os.path.isfile(ini):
            logger.error(f"Configuration file not found: {ini}")
            raise FileNotFoundError(f"Configuration file not found: {ini}")
        if not os.access(ini, os.R_OK):
            logger.error(f"Configuration file not readable: {ini}")
            raise PermissionError(f"Configuration file not readable: {ini}")

        try:
            config_dict = read_ini(ini)
        except (OSError, configparser.Error) as e:
            logger.error(f"Failed to parse INI config file {ini}: {e}")
            raise RuntimeError(f"Failed to parse INI config file {ini}: {e}") from e

        # Try exact match, then capitalized match (for deploy_code compatibility)
        env_record = None
        if env_name in config_dict:
            env_record = config_dict[env_name]
        elif env_name.capitalize() in config_dict:
            env_record = config_dict[env_name.capitalize()]

        if env_record:
            for k in ["base_url", "client_id", "client_secret", "verify_ssl"]:
                if k in env_record:
                    creds[k] = env_record[k]
        else:
            if not creds:
                raise KeyError(f"Could not find section {env_name} in {ini}")
            else:
                logger.warning(f"Could not find section {env_name} in {ini}, using environment variables.")

    return creds
