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
from looker_deployer.utils.parse_ini import build_creds
logger = deploy_logging.get_logger(__name__)


def get_filtered_groups(creds, pattern=None):
    try:
        result = run_cli_command(
            ["looker-cli", "api", "group", "all_groups"],
            text=True,
            creds=creds
        )
    except FileNotFoundError as e:
        logger.error(f"looker-cli command not found: {e}")
        raise RuntimeError("looker-cli command not found. Please ensure it is installed and in your PATH.") from e
    except LookerCLIError as e:
        logger.error(f"looker-cli failed to get groups: {e.stderr}")
        raise

    stdout = result.stdout.strip()
    if not stdout:
        return []

    try:
        groups = json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from looker-cli: {e}")
        raise RuntimeError(f"Failed to parse JSON from looker-cli: {e}") from e

    if not isinstance(groups, list):
        groups = [groups]

    logger.debug(
        "Groups pulled",
        extra={
            "groups_name": [getattr(i, "name", "Unknown") for i in groups]
        }
    )

    groups = [i for i in groups if not getattr(i, "externally_managed", False)]

    if pattern:
        compiled_pattern = re.compile(pattern)
        groups = [i for i in groups if getattr(i, "name", None) is not None and compiled_pattern.search(str(i.name))]
        logger.debug(
            "Groups in Group filtered",
            extra={
                "filtered_groups": [getattr(i, "name", "Unknown") for i in groups],
                "pattern": pattern
            }
        )

    return groups


def write_groups_in_group(source_creds, target_creds, pattern=None):  # noqa: C901

    groups = get_filtered_groups(source_creds, pattern)
    target_groups = get_filtered_groups(target_creds, pattern=None)

    for group in groups:
        matched_group = match_by_key(target_groups, group, "name")
        if not matched_group:
            logger.warning(f"Group '{getattr(group, 'name', 'Unknown')}' not found on target. Skipping.")
            continue
        logger.debug("Group Matched " + getattr(matched_group, "name", "Unknown"))

        # Run looker-cli group subgroup list <group_id> on source
        try:
            res_source = run_cli_command(
                ["looker-cli", "api", "group", "all_group_groups", str(group.id)],
                text=True,
                creds=source_creds
            )
        except FileNotFoundError as e:
            raise RuntimeError("looker-cli command not found.") from e
        except LookerCLIError as e:
            logger.error(f"Failed to list subgroups on source: {e.stderr}")
            raise

        stdout_source = res_source.stdout.strip()
        groups_in_group = []
        if stdout_source:
            groups_in_group = json.loads(stdout_source, object_hook=lambda d: SimpleNamespace(**d))
            if not isinstance(groups_in_group, list):
                groups_in_group = [groups_in_group]

        # Run looker-cli group subgroup list <group_id> on target
        try:
            res_target = run_cli_command(
                ["looker-cli", "api", "group", "all_group_groups", str(matched_group.id)],
                text=True,
                creds=target_creds
            )
        except FileNotFoundError as e:
            raise RuntimeError("looker-cli command not found.") from e
        except LookerCLIError as e:
            logger.error(f"Failed to list subgroups on target: {e.stderr}")
            raise

        stdout_target = res_target.stdout.strip()
        target_groups_in_group = []
        if stdout_target:
            target_groups_in_group = json.loads(stdout_target, object_hook=lambda d: SimpleNamespace(**d))
            if not isinstance(target_groups_in_group, list):
                target_groups_in_group = [target_groups_in_group]

        updated_groups_in_group = []
        for nested_group in groups_in_group:
            target_nested_group = match_by_key(target_groups, nested_group, "name")
            if target_nested_group:
                nested_group.id = target_nested_group.id
                updated_groups_in_group.append(nested_group)
        groups_in_group = updated_groups_in_group

        source_group_ids = [str(nested_group.id) for nested_group in groups_in_group]
        target_group_ids = [str(nested_group.id) for nested_group in target_groups_in_group]

        all_group_ids = list(set().union(source_group_ids, target_group_ids))

        for group_id in all_group_ids:
            in_source = group_id in source_group_ids
            in_target = group_id in target_group_ids

            if in_source and not in_target:
                logger.debug("No Groups in Group found. Creating...")
                logger.debug("Deploying Groups in Group",
                             extra={"group_name": getattr(group, "name", "Unknown"),
                                    "group_group_id": group_id})
                try:
                    payload_id = int(group_id)
                except ValueError:
                    payload_id = group_id
                try:
                    run_cli_command(
                        ["looker-cli", "api", "group", "add_group_group", str(matched_group.id), "-"],
                        text=True,
                        creds=target_creds,
                        input=json.dumps({"group_id": str(payload_id)})
                    )
                except LookerCLIError as e:
                    logger.error(f"Failed to add subgroup: {e.stderr}")
                    raise
                logger.info("Deployment Complete",
                            extra={"group_name": getattr(group, "name", "Unknown"),
                                   "group_group_id": group_id})

            elif not in_source and in_target:
                logger.debug("Extra Groups in Group found. Deleting...")
                logger.debug("Removing Groups in Group",
                             extra={"group_name": getattr(group, "name", "Unknown"),
                                    "group_group_id": group_id})
                try:
                    run_cli_command(
                        ["looker-cli", "api", "group", "delete_group_from_group", str(matched_group.id), str(group_id)],
                        text=True,
                        creds=target_creds
                    )
                except LookerCLIError as e:
                    logger.error(f"Failed to remove subgroup: {e.stderr}")
                    raise
                logger.info("Deployment Complete",
                            extra={"group_name": getattr(group, "name", "Unknown"),
                                   "group_group_id": group_id})


def main(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        source_creds = build_creds(args.ini, args.source)
        for t in args.target:
            target_creds = build_creds(args.ini, t)
            write_groups_in_group(source_creds, target_creds, args.pattern)
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e
