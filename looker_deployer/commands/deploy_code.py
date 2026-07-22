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

import os
import subprocess  # noqa: F401
import oyaml as yaml
import logging
import configparser  # noqa: F401
import json
import requests
from looker_deployer.utils import deploy_logging
from looker_deployer.utils import parse_ini
from looker_deployer.utils.cli import run_cli_command
from looker_deployer.utils.exceptions import LookerCLIError

logger = deploy_logging.get_logger(__name__)


def parse_hub_targets(config):
    instances = config["instances"]
    if config.get("hub_deploy_exclude"):
        logger.info("Detected exclude list", extra={"excluded": config.get("hub_deploy_exclude")})
        excludes = config.get("hub_deploy_exclude")
        targets = [i["name"] for i in instances if i["name"] not in excludes]
    else:
        targets = [i["name"] for i in instances]

    logger.info("Parsed targets", extra={"targets": targets})
    return targets


def parse_spoke_config(spoke_name, config):
    spoke_config = [i for i in config["instances"] if i["name"] == spoke_name][0]
    logger.info("Parsed spoke config", extra={"config": spoke_config})

    return spoke_config


def parse_hub_excludes(config, arg=None):
    if arg and type(config.get("hub_deploy_exclude")) == list:
        config["hub_deploy_exclude"] += arg
    elif arg:
        config["hub_deploy_exclude"] = arg


def get_access_token(creds):
    base_url = creds["base_url"].rstrip("/")
    login_url = f"{base_url}/api/4.0/login"

    logger.debug("Logging in to get token", extra={"login_url": login_url})
    try:
        response = requests.post(
            login_url,
            data={
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"]
            },
            verify=str(creds.get("verify_ssl", "True")).lower() == "true",
            timeout=10
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        logger.error(f"Failed to obtain access token: {e}")
        raise


def deploy_code(project, creds):
    logger.info("Deploying", extra={"project": project})

    try:
        token = get_access_token(creds)
        token_creds = {
            "base_url": creds["base_url"],
            "verify_ssl": creds.get("verify_ssl"),
            "token": token
        }
        logger.debug("Switching session to dev mode")
        run_cli_command(
            ["looker-cli", "api", "session", "update_session", "-"],
            creds=token_creds,
            check=True,
            input=json.dumps({"workspace_id": "dev"}),
            capture_output=True,
            text=True
        )
    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to prepare dev session: {e}")
        raise RuntimeError("Failed to prepare dev session") from e

    command = [
        "looker-cli",
        "project",
        "deploy",
        project
    ]

    try:
        run_cli_command(command, creds=token_creds, check=True, capture_output=True, text=True)
        logger.info("Deployment complete. Status: success")
        return {"operations": [{"results": ["success"]}]}
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    with open("./code_config.yaml") as f:
        config = yaml.safe_load(f)

    if args.hub:
        project = config["hub_project"]

        parse_hub_excludes(config, args.hub_exclude)

        targets = parse_hub_targets(config)

        for target in targets:
            logger.info("Deploying hub to %s", target)
            creds = parse_ini.build_creds("./looker.ini", target)
            deploy_code(project, creds)

    if args.spoke:

        for i in args.spoke:
            try:
                spoke_config = parse_spoke_config(i, config)
            except IndexError:
                logger.error("Invalid name %s. Skipping...", i)
                continue

            project = spoke_config["spoke_project"]
            target = spoke_config["name"]
            creds = parse_ini.build_creds("./looker.ini", target)

            deploy_code(project, creds)
