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
from looker_deployer.utils import parse_ini  # noqa: F401
from looker_deployer.utils.match_by_key import match_by_key
from looker_deployer.utils.cli import run_cli_command
from looker_deployer.utils.exceptions import LookerCLIError
from looker_deployer.utils.parse_ini import build_creds

logger = deploy_logging.get_logger(__name__)


def get_filtered_permission_sets(creds, pattern=None):
    cmd = ["looker-cli", "api", "role", "all_permission_sets"]
    try:
        result = run_cli_command(
            cmd,
            text=True,
            creds=creds
        )
    except OSError as e:
        logger.error(f"looker-cli command not found or execution failed: {e}")
        raise RuntimeError(f"looker-cli command not found or execution failed. Please ensure it is installed and in your PATH. Error: {e}") from e
    except LookerCLIError as e:
        logger.error(f"looker-cli failed to get permission sets: {e.stderr}")
        raise

    if not result.stdout.strip():
        return []

    try:
        parsed = json.loads(result.stdout, object_hook=lambda d: SimpleNamespace(**d))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from looker-cli: {e}")
        raise RuntimeError(f"Failed to parse JSON from looker-cli: {e}") from e

    if isinstance(parsed, list):
        permission_sets = parsed
    elif isinstance(parsed, SimpleNamespace):
        permission_sets = [parsed]
    else:
        logger.error(f"Unexpected JSON structure returned from looker-cli: {parsed}")
        raise RuntimeError(f"Unexpected JSON structure returned from looker-cli: {parsed}")

    logger.debug(
        "Permission Sets pulled",
        extra={
            "permission_sets_names": [getattr(i, "name", "Unknown") for i in permission_sets]
        }
    )

    permission_sets = [i for i in permission_sets if not getattr(i, "built_in", False)]

    if pattern:
        try:
            compiled_pattern = re.compile(pattern)
        except re.error as e:
            logger.error(f"Invalid regular expression pattern '{pattern}': {e}")
            raise RuntimeError(f"Invalid regular expression pattern '{pattern}': {e}") from e
        permission_sets = [i for i in permission_sets
                           if getattr(i, "name", None) is not None and compiled_pattern.search(str(getattr(i, "name")))]
        logger.debug(
            "Permission Sets filtered",
            extra={
                "filtered_permission_sets": [getattr(i, "name", "Unknown") for i in permission_sets],
                "pattern": pattern
            }
        )

    return permission_sets


def write_permission_sets(permission_sets, target_creds, pattern=None, allow_delete=None):

    target_permission_sets = get_filtered_permission_sets(target_creds, pattern)

    valid_target_permission_sets = []
    for target_ps in target_permission_sets:
        name = getattr(target_ps, "name", None)
        if name is None or not isinstance(name, str):
            logger.warning("Target permission set is missing 'name' attribute or it is not a string. Skipping.")
            continue
        valid_target_permission_sets.append(target_ps)

    valid_source_permission_sets = []
    for permission_set in permission_sets:
        name = getattr(permission_set, "name", None)
        if name is None or not isinstance(name, str):
            logger.warning("Source permission set is missing 'name' attribute or it is not a string. Skipping.")
            continue
        valid_source_permission_sets.append(permission_set)

    deduped_source_dict = {}
    for ps in valid_source_permission_sets:
        deduped_source_dict[ps.name] = ps
    valid_source_permission_sets = list(deduped_source_dict.values())

    for permission_set in valid_source_permission_sets:
        payload = {}
        if hasattr(permission_set, "name"):
            payload["name"] = permission_set.name
        if hasattr(permission_set, "permissions"):
            payload["permissions"] = permission_set.permissions

        try:
            serialized_payload = json.dumps(payload)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize payload for permission set '{getattr(permission_set, 'name', 'Unknown')}': {e}. Skipping.")
            continue

        matched_permission_set = match_by_key(valid_target_permission_sets,
                                              permission_set, "name")

        if matched_permission_set:
            permission_set_exists = True
        else:
            permission_set_exists = False

        if not permission_set_exists:
            logger.debug("No Permission Set found. Creating...")
            logger.debug("Deploying Permission Set",
                          extra={"permission_set": permission_set.name})
            cmd = ["looker-cli", "api", "role", "create_permission_set", "-"]
            try:
                run_cli_command(
                    cmd,
                    input=serialized_payload,
                    creds=target_creds,
                    text=True
                )
                logger.info("Deployment complete",
                            extra={"permission_set": permission_set.name})
            except OSError as e:
                logger.error(f"looker-cli command not found or execution failed: {e}")
                raise RuntimeError(f"looker-cli command not found or execution failed. Please ensure it is installed and in your PATH. Error: {e}") from e
            except LookerCLIError as e:
                logger.error(f"looker-cli failed to create permission set: {e.stderr}")
                raise
        else:
            logger.debug("Existing permission set found. Updating...")
            logger.debug("Deploying Permission Set",
                          extra={"permission_set": permission_set.name})
            target_id = getattr(matched_permission_set, "id", None)
            if target_id is None:
                logger.error(f"Target permission set '{matched_permission_set.name}' is missing an 'id'. Skipping update.")
                continue

            cmd = ["looker-cli", "api", "role", "update_permission_set", str(target_id), "-"]
            try:
                run_cli_command(
                    cmd,
                    input=serialized_payload,
                    creds=target_creds,
                    text=True
                )
                logger.info("Deployment complete",
                            extra={"permission_set": permission_set.name})
            except OSError as e:
                logger.error(f"looker-cli command not found or execution failed: {e}")
                raise RuntimeError(f"looker-cli command not found or execution failed. Please ensure it is installed and in your PATH. Error: {e}") from e
            except LookerCLIError as e:
                logger.error(f"looker-cli failed to update permission set: {e.stderr}")
                raise

    if allow_delete:
        matched_source_names = set()
        for target_permission_set in valid_target_permission_sets:
            matched_permission_set = match_by_key(valid_source_permission_sets,
                                                  target_permission_set,
                                                  "name")

            should_delete = False
            if matched_permission_set:
                if matched_permission_set.name not in matched_source_names:
                    matched_source_names.add(matched_permission_set.name)
                else:
                    should_delete = True
            else:
                should_delete = True

            if should_delete:
                logger.debug("No Source Permission Set found or duplicate target. Deleting...")
                logger.debug("Deleting Permission Set",
                             extra={"permission_set":
                                    target_permission_set.name})
                target_id = getattr(target_permission_set, "id", None)
                if target_id is None:
                    logger.error(f"Target permission set '{target_permission_set.name}' is missing an 'id'. Skipping delete.")
                    continue

                cmd = ["looker-cli", "api", "role", "delete_permission_set", str(target_id)]
                try:
                    run_cli_command(
                        cmd,
                        creds=target_creds,
                        text=True
                    )
                    logger.info("Delete complete",
                                extra={"permission_set":
                                       target_permission_set.name})
                except OSError as e:
                    logger.error(f"looker-cli command not found or execution failed: {e}")
                    raise RuntimeError(f"looker-cli command not found or execution failed. Please ensure it is installed and in your PATH. Error: {e}") from e
                except LookerCLIError as e:
                    logger.error(f"looker-cli failed to delete permission set: {e.stderr}")
                    raise


def send_permission_sets(source_creds, target_creds, pattern=None, allow_delete=None):
    permission_sets = get_filtered_permission_sets(source_creds, pattern)
    write_permission_sets(permission_sets, target_creds, pattern, allow_delete)


def main(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        source_creds = build_creds(args.ini, args.source)
        for t in args.target:
            target_creds = build_creds(args.ini, t)
            send_permission_sets(source_creds, target_creds, args.pattern, args.delete)
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e
