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
import subprocess  # noqa: F401
import json
import os  # noqa: F401
import configparser  # noqa: F401
from types import SimpleNamespace
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.match_by_key import match_by_key
from looker_deployer.utils.cli import run_cli_command
from looker_deployer.utils.exceptions import LookerCLIError
from looker_deployer.commands import deploy_groups
from looker_deployer.utils.parse_ini import build_creds

logger = deploy_logging.get_logger(__name__)


def get_filtered_roles(creds, pattern=None):
    try:
        result = run_cli_command(
            ["looker-cli", "api", "role", "all_roles"],
            text=True,
            creds=creds
        )
    except FileNotFoundError as e:
        logger.error(f"looker-cli command not found: {e}")
        raise RuntimeError("looker-cli command not found. Please ensure it is installed and in your PATH.") from e
    except LookerCLIError as e:
        logger.error(f"looker-cli failed to get roles: {e.stderr}")
        raise

    if not result.stdout.strip():
        return []

    try:
        parsed = json.loads(result.stdout, object_hook=lambda d: SimpleNamespace(**d))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from looker-cli: {e}")
        if result.stdout:
            raise RuntimeError(f"Failed to parse JSON from looker-cli: {e}") from e
        return []

    if isinstance(parsed, list):
        roles = parsed
    elif isinstance(parsed, SimpleNamespace):
        roles = [parsed]
    else:
        logger.error(f"Unexpected JSON structure returned from looker-cli: {parsed}")
        raise RuntimeError(f"Unexpected JSON structure returned from looker-cli: {parsed}")

    logger.debug(
        "Roles pulled",
        extra={
            "role_names": [getattr(i, "name", "Unknown") for i in roles]
        }
    )

    if pattern:
        compiled_pattern = re.compile(pattern)
        roles = [i for i in roles if getattr(i, "name", None) is not None and compiled_pattern.search(str(getattr(i, "name")))]
        logger.debug(
            "Roles filtered",
            extra={
                "filtered_roles": [getattr(i, "name", "Unknown") for i in roles],
                "pattern": pattern
            }
        )

    return roles


def write_role_to_group(source_creds, target_creds, pattern=None):

    roles = get_filtered_roles(source_creds, pattern)
    target_roles = get_filtered_roles(target_creds, pattern)
    target_groups = deploy_groups.get_filtered_groups(target_creds, pattern=None, exclude_managed=False)

    for role in roles:
        role_name = getattr(role, "name", None)
        role_id = getattr(role, "id", None)
        if not role_name or role_id is None:
            continue

        matched_role = match_by_key(target_roles, role, "name")
        if not matched_role:
            logger.warning(f"Role '{role_name}' not found on target. Skipping group assignment.")
            continue

        matched_role_id = getattr(matched_role, "id", None)
        if matched_role_id is None:
            logger.warning(f"Matched role '{role_name}' has no ID on target. Skipping.")
            continue

        # Get role groups from source env
        try:
            res = run_cli_command(
                ["looker-cli", "api", "role", "role_groups", str(role_id)],
                text=True,
                creds=source_creds
            )
        except LookerCLIError as e:
            logger.error(f"looker-cli failed to get role groups for role {role_name}: {e.stderr}")
            continue

        try:
            role_groups = json.loads(res.stdout, object_hook=lambda d: SimpleNamespace(**d))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse role groups JSON: {e}")
            continue

        if not isinstance(role_groups, list):
            if isinstance(role_groups, SimpleNamespace):
                role_groups = [role_groups]
            else:
                role_groups = []

        updated_role_groups = []
        for role_group in role_groups:
            target_group = match_by_key(target_groups, role_group, "name")

            if target_group:
                target_group_id = getattr(target_group, "id", None)
                if target_group_id is not None:
                    role_group.id = target_group_id
                    updated_role_groups.append(role_group)

        groups_for_update = [getattr(i, "id") for i in updated_role_groups]
        logger.debug("Updating Role Group. Updating...")
        logger.debug("Deploying Role Group",
                     extra={"role_name": role_name,
                            "group_ids": groups_for_update})

        try:
            run_cli_command(
                ["looker-cli", "api", "role", "set_role_groups", str(matched_role_id), "-"],
                text=True,
                creds=target_creds,
                input=json.dumps(groups_for_update)
            )
            logger.info("Deployment Complete",
                        extra={"role_name": role_name,
                               "group_ids": groups_for_update})
        except LookerCLIError as e:
            logger.error(f"looker-cli failed to set role groups: {e.stderr}")


def main(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        source_creds = build_creds(args.ini, args.source)
        for t in args.target:
            target_creds = build_creds(args.ini, t)
            write_role_to_group(source_creds, target_creds, args.pattern)
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e
