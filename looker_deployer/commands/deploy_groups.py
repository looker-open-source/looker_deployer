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
from types import SimpleNamespace
import os  # noqa: F401
import configparser  # noqa: F401
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.cli import run_cli_command
from looker_deployer.utils.exceptions import LookerCLIError
from looker_deployer.utils.parse_ini import build_creds

logger = deploy_logging.get_logger(__name__)


def get_filtered_groups(creds, pattern=None, exclude_managed=True):
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
        for item in parsed:
            if not isinstance(item, SimpleNamespace):
                logger.error(f"Unexpected JSON structure returned from looker-cli list element: {item}")
                raise RuntimeError(f"Unexpected JSON structure returned from looker-cli list element: {item}")
        groups = parsed
    elif isinstance(parsed, SimpleNamespace):
        groups = [parsed]
    else:
        logger.error(f"Unexpected JSON structure returned from looker-cli: {parsed}")
        raise RuntimeError(f"Unexpected JSON structure returned from looker-cli: {parsed}")

    logger.debug(
        "Groups pulled",
        extra={
            "groups_names": [getattr(i, "name", "Unknown") for i in groups]
        }
    )

    if exclude_managed:
        groups = [i for i in groups if not getattr(i, 'externally_managed', False)]

    if pattern:
        compiled_pattern = re.compile(pattern)
        groups = [i for i in groups if getattr(i, "name", None) is not None and compiled_pattern.search(str(getattr(i, "name")))]
        logger.debug(
            "Groups filtered",
            extra={
                "filtered_groups": [getattr(i, "name", "Unknown") for i in groups],
                "pattern": pattern
            }
        )

    return groups


def write_groups(groups, target_creds, pattern=None, allow_delete=None):

    def safe_name(g):
        val = getattr(g, "name", None)
        return "" if val is None else str(val)

    unique_groups = []
    seen_names = set()
    for group in groups:
        name = getattr(group, "name", None)
        if name is not None:
            name_str = str(name)
            name_lower = name_str.lower()
            if name_lower not in seen_names:
                seen_names.add(name_lower)
                unique_groups.append(group)
        else:
            logger.warning("Source group is missing a 'name' attribute. Skipping.", extra={"group": repr(group)})
    groups = unique_groups

    target_groups = get_filtered_groups(target_creds, pattern, exclude_managed=False)

    valid_target_groups = []
    for t in target_groups:
        t_id = getattr(t, "id", None)
        if t_id is not None and str(t_id).strip() != "":
            valid_target_groups.append(t)
        else:
            group_name_str = safe_name(t) or "Unknown"
            logger.warning(
                f"Target group '{group_name_str}' has no valid 'id' attribute. Skipping."
            )
    target_groups = valid_target_groups

    seen_target_group_ids = set()

    for group in groups:
        group_name_raw = getattr(group, "name", None)
        if group_name_raw is None:
            continue
        group_name = str(group_name_raw)
        if not group_name:
            continue

        matched_group = next(
            (t for t in target_groups if safe_name(t).lower() == group_name.lower() and getattr(t, "id", None) not in seen_target_group_ids and not getattr(t, "externally_managed", False)),
            None
        )

        if not matched_group:
            matched_group = next(
                (t for t in target_groups if safe_name(t).lower() == group_name.lower() and getattr(t, "id", None) not in seen_target_group_ids),
                None
            )

        if matched_group:
            target_id = getattr(matched_group, "id", None)
            seen_target_group_ids.add(target_id)
            if getattr(matched_group, 'externally_managed', False):
                logger.warning(
                    f"Target group '{getattr(matched_group, 'name', 'Unknown')}' is externally managed. Skipping update/create.",
                    extra={"group": group_name}
                )
                continue

            matched_name = safe_name(matched_group)
            if group_name != matched_name:
                logger.debug("Existing Group found with different case. Updating...")
                logger.debug("Deploying Group", extra={"group": group_name})
                try:
                    run_cli_command(
                        ["looker-cli", "api", "group", "update_group", str(target_id), "-"],
                        input=json.dumps({"name": group_name}),
                        creds=target_creds,
                        text=True
                    )
                    logger.info("Deployment complete", extra={"group": group_name})
                except LookerCLIError as e:
                    logger.error(f"looker-cli failed to update group: {e.stderr}")
                    raise
            else:
                logger.debug(f"Group '{group_name}' exactly matches target. Skipping update.")

        else:
            logger.debug("No Group found. Creating...")
            logger.debug("Deploying Group", extra={"group": group_name})
            try:
                run_cli_command(
                    ["looker-cli", "api", "group", "create_group", "-"],
                    input=json.dumps({"name": group_name}),
                    creds=target_creds,
                    text=True
                )
                logger.info("Deployment complete", extra={"group": group_name})
            except LookerCLIError as e:
                logger.error(f"looker-cli failed to create group: {e.stderr}")
                raise

    if allow_delete:
        for target_group in target_groups:
            if getattr(target_group, 'externally_managed', False):
                continue

            target_id = getattr(target_group, 'id', None)

            if target_id not in seen_target_group_ids:
                target_name = safe_name(target_group) or "Unknown"
                logger.debug("No Source Group found. Deleting...")
                logger.debug("Deleting Group", extra={"group": target_name})
                try:
                    run_cli_command(
                        ["looker-cli", "api", "group", "delete_group", str(target_id)],
                        creds=target_creds,
                        text=True
                    )
                    logger.info("Delete complete", extra={"group": target_name})
                except LookerCLIError as e:
                    logger.error(f"looker-cli failed to delete group: {e.stderr}")
                    raise


def send_groups(source_creds, target_creds, pattern=None, allow_delete=None):
    groups = get_filtered_groups(source_creds, pattern)
    write_groups(groups, target_creds, pattern, allow_delete)


def main(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        source_creds = build_creds(args.ini, args.source)
        for t in args.target:
            target_creds = build_creds(args.ini, t)
            send_groups(source_creds, target_creds, args.pattern, args.delete)
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e
