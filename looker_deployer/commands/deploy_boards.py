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

import json
import logging
import subprocess  # noqa: F401
from types import SimpleNamespace
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.cli import run_cli_command as run_subprocess_command
from looker_deployer.utils.parse_ini import build_creds
from looker_deployer.utils.exceptions import LookerCLIError

logger = deploy_logging.get_logger(__name__)


class MultipleAssetsFoundError(Exception):
    """Exception raised if multiple assets are found"""

    def __init__(self, asset_name, message="Found multiple entries for asset. Please remove duplicates"):
        self.asset_name = asset_name
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.asset_name} -> {self.message}"


class TargetContentNotFound(Exception):
    """Exception raised if content is not found in target instance"""

    def __init__(self, missing_dashes, missing_looks, message="Content not found in target instance."):
        self.missing_dashes = missing_dashes
        self.missing_looks = missing_looks
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} -> dashes: {self.missing_dashes}, looks: {self.missing_looks}"


def run_cli_command(creds, args, input_str=None):
    cmd = ["looker-cli"] + args
    logger.debug("Running CLI command", extra={"cmd": cmd})
    result = run_subprocess_command(cmd, creds=creds, text=True, input=input_str)

    stdout = result.stdout.strip()
    if stdout:
        try:
            return json.loads(stdout, object_hook=lambda d: SimpleNamespace(**d))
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse CLI output as JSON. Raw output: {stdout}") from e

    if any(x in args for x in ["search", "list", "all_boards"]):
        return []
    return None


def match_dashboard_id(source_dashboard_id, source_creds, target_creds):
    source = run_cli_command(source_creds, ["api", "dashboard", "dashboard", str(source_dashboard_id)])
    logger.debug("Attempting dashboard match", extra={"title": source.title, "slug": source.slug, "id": source.id})
    target_dash = run_cli_command(target_creds, ["api", "dashboard", "search_dashboards", "-"], input_str=json.dumps({"slug": source.slug}))

    if len(target_dash) > 1:
        raise MultipleAssetsFoundError(source.title)

    assert len(target_dash) == 1, f"Could not find dashboard {source.title} in target env. Has it been deployed?"

    target_id = target_dash[0].id
    logger.debug("Found dashboard", extra={"id": target_id})

    return target_id


def match_look_id(source_look_id, source_creds, target_creds):
    source = run_cli_command(source_creds, ["api", "look", "look", str(source_look_id)])
    logger.debug("Attempting look match", extra={"title": source.title, "id": source.id})
    target_look = run_cli_command(target_creds, ["api", "look", "search_looks", "-"], input_str=json.dumps({"title": source.title}))

    if len(target_look) > 1:
        raise MultipleAssetsFoundError(source.title)

    assert len(target_look) == 1, f"Could not find look {source.title} in target env. Has it been deployed?"

    target_id = target_look[0].id
    logger.debug("Found look", extra={"id": target_id})

    return target_id


def return_board(board_name, source_creds):
    logger.debug("Searching boards", extra={"title": board_name})
    boards = run_cli_command(source_creds, ["api", "board", "all_boards"])
    board_list = [b for b in boards if getattr(b, "title", None) == board_name]

    if len(board_list) > 1:
        raise MultipleAssetsFoundError(board_name)

    assert len(board_list) == 1, "Could not find board! Double check available titles and try again."

    logger.debug("Found board", extra={"board": board_list})
    return board_list[0]


def create_or_update_board(source_board_object, target_creds, title_override=None):
    search_title = title_override or source_board_object.title
    boards = run_cli_command(target_creds, ["api", "board", "all_boards"])
    search_res = [b for b in boards if getattr(b, "title", None) == search_title]

    assert len(search_res) < 2, "More than one board found! Refine your search or remove duplicate names."

    try:
        assert len(search_res) == 1

    except AssertionError:
        logger.info(
            "No pre-existing board found. Creating new board in target environment",
            extra={"title": search_title}
        )

        payload = {"title": source_board_object.title}
        if getattr(source_board_object, "description", None):
            payload["description"] = source_board_object.description

        resp = run_cli_command(target_creds, ["api", "board", "create_board", "-"], input_str=json.dumps(payload))
        logger.info("Board created", extra={"id": resp.id})
        return resp.id

    logger.info(
        "Found board in target instance. Updating and rebuilding content",
        extra={"title": search_title}
    )

    target_board = search_res[0]

    # Clear out existing sections
    section_list = [i.id for i in getattr(target_board, "board_sections", [])]
    logger.debug("Found sections to clear", extra={"section_list": section_list})

    for section in section_list:
        logger.debug("Clearing section for refresh", extra={"section_id": section})
        run_cli_command(target_creds, ["api", "board", "delete_board_section", str(section)])

    # Update
    payload = {"title": source_board_object.title}
    if getattr(source_board_object, "description", None):
        payload["description"] = source_board_object.description

    resp = run_cli_command(target_creds, ["api", "board", "update_board", str(target_board.id), "-"], input_str=json.dumps(payload))
    logger.info("Board updated", extra={"id": resp.id})
    return resp.id


def create_board_section(source_board_section_object, target_board_id, target_creds):
    payload = {
        "board_id": str(target_board_id),
        "title": source_board_section_object.title
    }
    if getattr(source_board_section_object, "description", None):
        payload["description"] = source_board_section_object.description

    logger.info("Creating Section", extra={"board_id": target_board_id, "section_title": source_board_section_object.title})
    resp = run_cli_command(target_creds, ["api", "board", "create_board_section", "-"], input_str=json.dumps(payload))
    logger.info("Section created", extra={"section_id": resp.id})
    return resp.id


def create_board_item(source_board_item_object, target_board_section_id, source_creds, target_creds):

    dashboard_id = None
    look_id = None

    if getattr(source_board_item_object, "dashboard_id", None):
        dashboard_id = match_dashboard_id(source_board_item_object.dashboard_id, source_creds, target_creds)
    if getattr(source_board_item_object, "look_id", None):
        look_id = match_look_id(source_board_item_object.look_id, source_creds, target_creds)

    payload = {"board_section_id": str(target_board_section_id)}

    if dashboard_id is not None:
        payload["dashboard_id"] = str(dashboard_id)
    if look_id is not None:
        payload["look_id"] = str(look_id)

    allowed_props = (
        "title",
        "description",
        "url",
        "custom_title",
        "custom_description",
        "custom_url",
        "order",
        "use_custom_image",
        "lookml_dashboard_id"
    )

    for prop in allowed_props:
        val = getattr(source_board_item_object, prop, None)
        if val is None:
            continue
        if isinstance(val, SimpleNamespace):
            payload[prop] = vars(val)
        else:
            payload[prop] = val

    url = getattr(source_board_item_object, "url", None)

    logger.info(
        "Creating item",
        extra={
            "section_id": target_board_section_id,
            "dashboard_id": dashboard_id,
            "look_id": look_id,
            "url": url
        }
    )
    resp = run_cli_command(target_creds, ["api", "board", "create_board_item", "-"], input_str=json.dumps(payload))
    logger.info("Item created", extra={"id": getattr(resp, "id", None)})

    return resp


def board_content_lists(board_object):
    dash_list = []
    look_list = []

    for i in getattr(board_object, "board_sections", []):
        for j in getattr(i, "board_items", []):
            if getattr(j, "dashboard_id", None):
                dash_list.append(j.dashboard_id)
            if getattr(j, "look_id", None):
                look_list.append(j.look_id)

    return (dash_list, look_list)


def audit_board_content(board_object, source_creds, target_creds):
    missing_dashes = []
    missing_looks = []

    dash_list, look_list = board_content_lists(board_object)

    for dash in dash_list:
        try:
            match_dashboard_id(dash, source_creds, target_creds)
        except AssertionError:
            dash_resp = run_cli_command(source_creds, ["dashboard", "get", "--id", str(dash)])
            missing_dashes.append({"dash_id": dash, "dash_title": getattr(dash_resp, "title", "Unknown")})

    for look in look_list:
        try:
            match_look_id(look, source_creds, target_creds)
        except AssertionError:
            look_resp = run_cli_command(source_creds, ["look", "get", "--id", str(look)])
            missing_looks.append({"look_id": look, "look_title": getattr(look_resp, "title", "Unknown")})

    return (missing_dashes, missing_looks)


def send_boards(board_name, source_creds, target_creds, title_override=None, allow_partial=False):
    source_board = return_board(board_name, source_creds)

    missing_dashes, missing_looks = audit_board_content(source_board, source_creds, target_creds)
    if not allow_partial and (missing_dashes or missing_looks):
        logger.error(
            "Missing Content. Make sure it's deployed or rerun with allow-partial flag.",
            extra={"missing_dashboards": missing_dashes, "missing_looks": missing_looks}
        )
        raise TargetContentNotFound(missing_dashes, missing_looks)
    elif missing_dashes or missing_looks:
        logger.warning(
            "Missing content warning.",
            extra={"missing_dashboards": missing_dashes, "missing_looks": missing_looks}
        )
    else:
        logger.info("All content accounted for!")

    target_board_id = create_or_update_board(source_board, target_creds, title_override)

    for section in getattr(source_board, "board_sections", []):
        target_section_id = create_board_section(section, target_board_id, target_creds)

        for item in getattr(section, "board_items", []):
            try:
                create_board_item(item, target_section_id, source_creds, target_creds)
            except AssertionError:
                if allow_partial:
                    logger.warning("Could not find content!", extra={"item": getattr(item, "title", "Unknown")})
                    pass
                else:
                    raise


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        source_creds = build_creds(args.ini, args.source)
        for t in args.target:
            target_creds = build_creds(args.ini, t)
            send_boards(args.board, source_creds, target_creds, args.title_change, args.allow_partial)
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e
