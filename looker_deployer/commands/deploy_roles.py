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
import json
import subprocess  # noqa: F401
from types import SimpleNamespace
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.cli import run_cli_command as run_subprocess_command
from looker_deployer.utils.match_by_key import match_by_key
from looker_deployer.utils.parse_ini import build_creds
from looker_deployer.utils.exceptions import LookerCLIError

logger = deploy_logging.get_logger(__name__)


def run_cli_command(creds, args, input_str=None):
    cmd = ["looker-cli"] + args
    logger.debug("Running CLI command", extra={"cmd": cmd})
    # run_subprocess_command will raise LookerCLIError on failure
    result = run_subprocess_command(cmd, creds=creds, text=True, input=input_str)

    stdout = result.stdout.strip()
    if stdout:
        try:
            return json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse CLI output as JSON. Raw output: {stdout}") from e

    if any(x in args for x in ["search", "list", "all_permission_sets", "all_model_sets", "all_roles"]):
        return []
    return None


def get_filtered_roles(creds, pattern=None):
    roles = run_cli_command(creds, ["api", "role", "all_roles"])
    if not roles:
        roles = []
    if not isinstance(roles, list):
        roles = [roles]

    roles = [i for i in roles if getattr(i, "name", None) != "Admin"]
    logger.debug("Roles pulled", extra={"roles_names": [getattr(i, "name", "Unknown") for i in roles]})

    if pattern:
        compiled_pattern = re.compile(pattern)
        roles = [i for i in roles if getattr(i, "name", None) is not None and compiled_pattern.search(str(i.name))]
        logger.debug("Roles filtered", extra={"filtered_roles": [getattr(i, "name", "Unknown") for i in roles], "pattern": pattern})

    return roles


def write_roles(roles, target_creds, pattern=None, allow_delete=None):
    target_roles = get_filtered_roles(target_creds, pattern)

    target_permission_sets = run_cli_command(target_creds, ["api", "role", "all_permission_sets"])
    if not target_permission_sets:
        target_permission_sets = []
    if not isinstance(target_permission_sets, list):
        target_permission_sets = [target_permission_sets]

    target_model_sets = run_cli_command(target_creds, ["api", "role", "all_model_sets"])
    if not target_model_sets:
        target_model_sets = []
    if not isinstance(target_model_sets, list):
        target_model_sets = [target_model_sets]

    for role in roles:
        matched_permission_set = match_by_key(target_permission_sets, getattr(role, "permission_set", None), "name") if getattr(role, "permission_set", None) else None
        matched_model_set = match_by_key(target_model_sets, getattr(role, "model_set", None), "name") if getattr(role, "model_set", None) else None

        permission_set_id = getattr(matched_permission_set, "id", None) if matched_permission_set else None
        model_set_id = getattr(matched_model_set, "id", None) if matched_model_set else None

        matched_role = match_by_key(target_roles, role, "name")
        role_exists = matched_role is not None

        role_body = {
            "name": getattr(role, "name", None),
            "permission_set_id": permission_set_id,
            "model_set_id": model_set_id
        }

        if not role_exists:
            logger.debug("No Role found. Creating...")
            logger.debug("Deploying Role", extra={"role": getattr(role, "name", "Unknown")})
            run_cli_command(target_creds, ["api", "role", "create_role", "-"], input_str=json.dumps(role_body))
            logger.info("Deployment complete", extra={"role": getattr(role, "name", "Unknown")})
        else:
            logger.debug("Existing Role found. Updating...")
            logger.debug("Deploying Role", extra={"role": getattr(role, "name", "Unknown")})
            run_cli_command(target_creds, ["api", "role", "update_role", str(getattr(matched_role, "id")), "-"], input_str=json.dumps(role_body))
            logger.info("Deployment complete", extra={"role": getattr(role, "name", "Unknown")})

    if allow_delete:
        for target_role in target_roles:
            matched_role = match_by_key(roles, target_role, "name")
            if not matched_role:
                logger.debug("No Source Role found. Deleting...")
                logger.debug("Deleting Role", extra={"role": getattr(target_role, "name", "Unknown")})
                run_cli_command(target_creds, ["api", "role", "delete_role", str(getattr(target_role, "id"))])
                logger.info("Delete complete", extra={"role": getattr(target_role, "name", "Unknown")})


def send_roles(source_creds, target_creds, pattern=None, allow_delete=None):
    roles = get_filtered_roles(source_creds, pattern)
    write_roles(roles, target_creds, pattern, allow_delete)


def main(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        source_creds = build_creds(args.ini, args.source)
        for t in args.target:
            target_creds = build_creds(args.ini, t)
            send_roles(source_creds, target_creds, args.pattern, args.delete)
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e
