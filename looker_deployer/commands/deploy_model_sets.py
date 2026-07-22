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
from looker_deployer.utils.cli import run_cli_command
from types import SimpleNamespace
import os  # noqa: F401
import configparser  # noqa: F401
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.match_by_key import match_by_key
from looker_deployer.utils.exceptions import LookerCLIError
from looker_deployer.utils.parse_ini import build_creds

logger = deploy_logging.get_logger(__name__)


def get_filtered_model_sets(creds, pattern=None):
    cmd = ["looker-cli", "api", "role", "all_model_sets"]
    try:
        result = run_cli_command(
            cmd,
            text=True,
            creds=creds
        )
    except FileNotFoundError as e:
        logger.error(f"looker-cli command not found: {e}")
        raise RuntimeError("looker-cli command not found. Please ensure it is installed and in your PATH.") from e
    except LookerCLIError as e:
        logger.error(f"looker-cli failed to get model sets: {e.stderr}")
        raise

    if not result.stdout.strip():
        return []

    try:
        parsed = json.loads(result.stdout, object_hook=lambda d: SimpleNamespace(**d))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from looker-cli: {e}")
        raise RuntimeError(f"Failed to parse JSON from looker-cli: {e}") from e

    if isinstance(parsed, list):
        model_sets = parsed
    elif isinstance(parsed, SimpleNamespace):
        model_sets = [parsed]
    else:
        logger.error(f"Unexpected JSON structure returned from looker-cli: {parsed}")
        raise RuntimeError(f"Unexpected JSON structure returned from looker-cli: {parsed}")

    logger.debug(
        "Model Sets pulled",
        extra={
            "model_sets_names": [getattr(i, "name", "Unknown") for i in model_sets]
        }
    )

    model_sets = [i for i in model_sets if not getattr(i, "built_in", False)]

    if pattern:
        try:
            compiled_pattern = re.compile(pattern)
        except re.error as e:
            logger.error(f"Invalid regular expression pattern '{pattern}': {e}")
            raise RuntimeError(f"Invalid regular expression pattern '{pattern}': {e}") from e
        model_sets = [i for i in model_sets
                      if getattr(i, "name", None) is not None and compiled_pattern.search(str(getattr(i, "name")))]
        logger.debug(
            "Model Sets filtered",
            extra={
                "filtered_model_sets": [getattr(i, "name", "Unknown") for i in model_sets],
                "pattern": pattern
            }
        )

    return model_sets


def write_model_sets(model_sets, target_creds, pattern=None, allow_delete=None):

    target_model_sets = get_filtered_model_sets(target_creds, pattern)

    valid_target_model_sets = []
    for target_ms in target_model_sets:
        if getattr(target_ms, "name", None) is None:
            logger.warning("Target model set is missing 'name' attribute. Skipping.")
            continue
        valid_target_model_sets.append(target_ms)

    valid_source_model_sets = []
    for model_set in model_sets:
        if getattr(model_set, "name", None) is None:
            logger.warning("Source model set is missing 'name' attribute. Skipping.")
            continue
        valid_source_model_sets.append(model_set)

    for model_set in valid_source_model_sets:
        payload = {}
        if hasattr(model_set, "name"):
            payload["name"] = model_set.name
        if hasattr(model_set, "models"):
            payload["models"] = model_set.models

        matched_model_set = match_by_key(valid_target_model_sets,
                                         model_set, "name")

        if matched_model_set:
            model_set_exists = True
        else:
            model_set_exists = False

        if not model_set_exists:
            logger.debug("No Model Set found. Creating...")
            logger.debug("Deploying Model Set",
                          extra={"model_set": model_set.name})
            cmd = ["looker-cli", "api", "role", "create_model_set", "-"]
            try:
                run_cli_command(
                    cmd,
                    input=json.dumps(payload),
                    creds=target_creds,
                    text=True
                )
                logger.info("Deployment complete",
                            extra={"model_set": model_set.name})
            except LookerCLIError as e:
                logger.error(f"looker-cli failed to create model set: {e.stderr}")
                raise
        else:
            logger.debug("Existing model set found. Updating...")
            logger.debug("Deploying Model Set",
                          extra={"model_set": model_set.name})
            target_id = getattr(matched_model_set, "id", None)
            if target_id is None:
                logger.error(f"Target model set '{matched_model_set.name}' is missing an 'id'. Skipping update.")
                continue

            cmd = ["looker-cli", "api", "role", "update_model_set", str(target_id), "-"]
            try:
                run_cli_command(
                    cmd,
                    input=json.dumps(payload),
                    creds=target_creds,
                    text=True
                )
                logger.info("Deployment complete",
                            extra={"model_set": model_set.name})
            except LookerCLIError as e:
                logger.error(f"looker-cli failed to update model set: {e.stderr}")
                raise

    if allow_delete:
        for target_model_set in valid_target_model_sets:
            matched_model_set = match_by_key(valid_source_model_sets,
                                             target_model_set,
                                             "name")

            if not matched_model_set:
                logger.debug("No Source Model Set found. Deleting...")
                logger.debug("Deleting Model Set",
                             extra={"model_set":
                                    target_model_set.name})
                target_id = getattr(target_model_set, "id", None)
                if target_id is None:
                    logger.error(f"Target model set '{target_model_set.name}' is missing an 'id'. Skipping delete.")
                    continue

                cmd = ["looker-cli", "api", "role", "delete_model_set", str(target_id)]
                try:
                    run_cli_command(
                        cmd,
                        creds=target_creds,
                        text=True
                    )
                    logger.info("Delete complete",
                                extra={"model_set":
                                       target_model_set.name})
                except LookerCLIError as e:
                    logger.error(f"looker-cli failed to delete model set: {e.stderr}")
                    raise


def send_model_sets(source_creds, target_creds, pattern=None, allow_delete=None):
    model_sets = get_filtered_model_sets(source_creds, pattern)
    write_model_sets(model_sets, target_creds, pattern, allow_delete)


def main(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        source_creds = build_creds(args.ini, args.source)
        for t in args.target:
            target_creds = build_creds(args.ini, t)
            send_model_sets(source_creds, target_creds, args.pattern, args.delete)
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e
