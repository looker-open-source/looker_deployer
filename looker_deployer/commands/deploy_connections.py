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

import logging
import re
import os
import subprocess  # noqa: F401
import json
import tempfile
import configparser
from looker_deployer.utils import deploy_logging
from looker_deployer.utils import parse_ini
from looker_deployer.utils.cli import run_cli_command
from looker_deployer.utils.exceptions import LookerCLIError

logger = deploy_logging.get_logger(__name__)


def get_filtered_connections(source_creds, pattern=None):
    cmd = ["looker-cli", "api", "connection", "all_connections"]

    result = run_cli_command(
        cmd,
        creds=source_creds,
        capture_output=True,
        text=True,
        check=True
    )
    connections = json.loads(result.stdout)

    logger.debug(
        "Connections pulled",
        extra={
            "connection_names": [i["name"] for i in connections]
        }
    )

    if pattern:
        compiled_pattern = re.compile(pattern)
        connections = [i for i in connections if compiled_pattern.search(i["name"])]
        logger.debug(
            "Connections filtered",
            extra={
                "filtered_connections": [i["name"] for i in connections],
                "pattern": pattern
            }
        )

    return connections


def write_connections(connections, target_creds, db_config=None):
    for conn in connections:
        if db_config and conn["name"] in db_config:
            logger.debug("Attempting password update", extra={"connection": conn["name"]})
            conn["password"] = db_config[conn["name"]]

        temp_file_name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                temp_file_name = f.name
                json.dump(conn, f)

            cmd = ["looker-cli", "connection", "import", temp_file_name]

            run_cli_command(
                cmd,
                creds=target_creds,
                check=True
            )
        finally:
            if temp_file_name is not None:
                try:
                    os.remove(temp_file_name)
                except OSError:
                    pass


def send_connections(source_creds, target_creds, pattern=None, db_config=None):
    connections = get_filtered_connections(source_creds, pattern)
    write_connections(connections, target_creds, db_config)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.include_password:
        db_config = parse_ini.read_ini(args.ini)["Databases"]
    else:
        db_config = None

    try:
        source_creds = parse_ini.build_creds(args.ini, args.source)

        for t in args.target:
            target_creds = parse_ini.build_creds(args.ini, t)
            send_connections(source_creds, target_creds, args.pattern, db_config)
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e
