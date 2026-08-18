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
import os  # noqa: F401
import subprocess  # noqa: F401
import json
import configparser  # noqa: F401
from types import SimpleNamespace
from looker_deployer.utils import deploy_logging
from looker_deployer.utils import parse_ini  # noqa: F401
from looker_deployer.utils.cli import run_cli_command
from looker_deployer.utils.match_by_key import match_by_key
from looker_deployer.utils.parse_ini import build_creds
from looker_deployer.utils.exceptions import LookerCLIError

logger = deploy_logging.get_logger(__name__)


def run_cli(cmd, creds, **kwargs):
    full_cmd = ["looker-cli"] + cmd

    # Default to capture_output and text if not specified, but allow override
    if "capture_output" not in kwargs and "stdout" not in kwargs:
        kwargs["capture_output"] = True
    if "text" not in kwargs:
        kwargs["text"] = True

    result = run_cli_command(
        full_cmd,
        creds=creds,
        check=True,
        **kwargs
    )
    return result.stdout


def get_filtered_user_attributes(creds, pattern=None):
    stdout = run_cli(["api", "userattribute", "all_user_attributes"], creds)
    user_attributes = json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))

    logger.debug(
        "User Attributes pulled",
        extra={
            "user_attribute_names": [i.name for i in user_attributes]
        }
    )

    user_attributes = [i for i in user_attributes if not i.is_system]

    if pattern:
        compiled_pattern = re.compile(pattern)
        user_attributes = [i for i in user_attributes
                           if compiled_pattern.search(i.name)]

    logger.debug(
        "User Attributes filtered",
        extra={
            "filtered_user_attributes": [i.name for i in user_attributes],
            "pattern": pattern
        }
    )

    return user_attributes


def get_user_attribute_group_value(creds, user_attribute):
    stdout = run_cli(
        ["api", "userattribute", "all_user_attribute_group_values", str(user_attribute.id)],
        creds
    )
    user_attribute_group_value = json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))

    logger.debug("User Attribute Group Value Pulled", extra={
        "group_ids": [i.group_id for i in user_attribute_group_value]
    })

    return user_attribute_group_value


def add_group_name_information(list_to_update, group_lookup):
    for i, item in enumerate(list_to_update):
        gid = item.group_id
        name = group_lookup.get(gid)
        if name is None:
            name = group_lookup.get(str(gid))
        if name is None:
            try:
                name = group_lookup.get(int(gid))
            except (ValueError, TypeError):
                pass
        item.name = name
        list_to_update[i] = item
    return list_to_update


def write_user_attributes(source_creds, target_creds,
                          pattern=None, allow_delete=None):

    user_attributes = get_filtered_user_attributes(source_creds, pattern)
    target_user_attributes = get_filtered_user_attributes(target_creds, pattern)

    stdout = run_cli(["api", "group", "all_groups"], target_creds)
    target_groups = json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))

    stdout_source = run_cli(["api", "group", "all_groups"], source_creds)
    source_groups = json.loads(stdout_source, object_hook=lambda d: SimpleNamespace(**d))
    source_group_lookup = {g.id: g.name for g in source_groups}

    for user_attribute in user_attributes:
        payload = {
            "name": user_attribute.name,
            "label": user_attribute.label,
            "type": user_attribute.type,
            "default_value": getattr(user_attribute, "default_value", None),
            "value_is_hidden": getattr(user_attribute, "value_is_hidden", False),
            "user_can_view": getattr(user_attribute, "user_can_view", False),
            "user_can_edit": getattr(user_attribute, "user_can_edit", False)
        }

        matched_user_attribute = match_by_key(target_user_attributes, user_attribute, "name")
        if matched_user_attribute:
            user_attribute_exists = True
        else:
            user_attribute_exists = False

        if not user_attribute_exists:
            logger.debug("No User Attribute found. Creating...")
            logger.debug("Deploying User Attribute",
                         extra={"user_attribute": payload["name"]})
            stdout = run_cli(
                ["api", "userattribute", "create_user_attribute", "-"],
                target_creds,
                input=json.dumps(payload)
            )
            matched_user_attribute = json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))
            logger.info("Deployment complete",
                        extra={"user_attribute": payload["name"]})
        else:
            logger.debug("Existing user attribute found. Updating...")
            logger.debug("Deploying User Attribute",
                         extra={"user_attribute": payload["name"]})
            stdout = run_cli(
                ["api", "userattribute", "update_user_attribute", str(matched_user_attribute.id), "-"],
                target_creds,
                input=json.dumps(payload)
            )
            matched_user_attribute = json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))
            logger.info("Deployment complete",
                        extra={"user_attribute": payload["name"]})

        user_attribute_group_values = get_user_attribute_group_value(
            source_creds, user_attribute)
        user_attribute_group_values = add_group_name_information(
            user_attribute_group_values, source_group_lookup)

        desired_target_group_values_dict = {}
        for gv in user_attribute_group_values:
            target_group = match_by_key(target_groups, gv, "name")
            if target_group:
                payload_item = {
                    "group_id": str(target_group.id),
                    "value": getattr(gv, "value", None)
                }
                if hasattr(gv, "value_is_hidden"):
                    payload_item["value_is_hidden"] = gv.value_is_hidden
                desired_target_group_values_dict[str(target_group.id)] = payload_item
        desired_target_group_values = list(desired_target_group_values_dict.values())

        logger.debug(f"Setting group attribute values for user attribute {matched_user_attribute.name}")
        run_cli(
            ["api", "userattribute", "set_user_attribute_group_values", str(matched_user_attribute.id), "-"],
            target_creds,
            input=json.dumps(desired_target_group_values)
        )

    if allow_delete:
        for target_user_attribute in target_user_attributes:

            matched_user_attribute = match_by_key(
                user_attributes, target_user_attribute, "name")

            if not matched_user_attribute:
                logger.debug("No Source User Attribute found. Deleting...")
                logger.debug("Deleting User Attribute",
                             extra={"user_attribute":
                                    target_user_attribute.name})
                run_cli(
                    ["api", "userattribute", "delete_user_attribute", str(target_user_attribute.id)],
                    target_creds
                )
                logger.info("Delete complete",
                            extra={"user_attribute":
                                   target_user_attribute.name})


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        source_creds = build_creds(args.ini, args.source)

        for t in args.target:
            target_creds = build_creds(args.ini, t)
            write_user_attributes(source_creds, target_creds,
                                  args.pattern, args.delete)
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e
