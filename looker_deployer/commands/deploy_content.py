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
import re
from looker_deployer.utils.cli import run_cli_command
from looker_deployer.utils.exceptions import LookerCLIError
import logging
import json
import tempfile
import configparser  # noqa: F401
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.parse_ini import build_creds


logger = deploy_logging.get_logger(__name__)


def get_space_ids_from_name(space_name, parent_id, creds, debug=False):

    def search_folders(name, p_id):
        command = ["looker-cli", "api", "folder", "search_folders", "--name", name]
        if p_id is not None:
            command.extend(["--parent_id", str(p_id)])
        try:
            res = run_cli_command(command, creds=creds, check=True, capture_output=True, text=True)
            return json.loads(res.stdout)
        except LookerCLIError as e:
            logger.error("looker-cli folder search failed", extra={"stdout": e.stdout, "stderr": e.stderr})
            raise
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON from looker-cli folder search", extra={"error": str(e), "output": res.stdout if 'res' in locals() else None})
            raise

    if (space_name == "Shared" and parent_id == "0"):
        return ["1"]
    elif (space_name == "Embed Groups" and parent_id == "0"):
        return [str(search_folders(space_name, None)[0]["id"])]
    elif (space_name == "Users" and parent_id == "0"):
        return [str(search_folders(space_name, None)[0]["id"])]
    elif (space_name == "Embed Users" and parent_id == "0"):
        return [str(search_folders(space_name, None)[0]["id"])]
    logger.debug("space info", extra={"space_name": space_name, "parent_id": parent_id})
    space_list = search_folders(space_name, parent_id)
    id_list = [str(i["id"]) for i in space_list]

    return id_list


def create_or_return_space(space_name, parent_id, creds, debug=False):
    try:
        target_id = get_space_ids_from_name(space_name, parent_id, creds, debug)
        if len(target_id) == 0 and "/" in space_name:
            # If the folder name contains slashes then also check if it was previously imported with
            # the slashes replaced with division slashes (Unicode character 2215) prior to PR #153.
            target_id = get_space_ids_from_name(space_name.replace("/", "\u2215"), parent_id, creds, debug)
        logger.debug("Space ID from name", extra={"id": target_id})
        assert len(target_id) == 1
    except AssertionError as e:
        if len(target_id) > 1:
            logger.error("More than one Space found with that parent/name", extra={"space_ids": target_id})
            raise e
        elif (parent_id == '2' and len(target_id) == 0):
            logger.warning("Cannot create folder in Users.  Add the User first, then import their content", extra={"folder": space_name, "target_id": len(target_id)})
            raise e
        else:
            logger.warning("No folders found. Creating folder now")
            body = {
                "name": space_name,
                "parent_id": str(parent_id)
            }
            command = ["looker-cli", "api", "folder", "create_folder", "-"]
            try:
                res = run_cli_command(
                    command,
                    input=json.dumps(body),
                    creds=creds,
                    check=True,
                    capture_output=True,
                    text=True
                )
                res_json = json.loads(res.stdout)
                return str(res_json["id"])
            except LookerCLIError as e:
                logger.error("looker-cli api folder create_folder failed", extra={"stdout": e.stdout, "stderr": e.stderr})
                raise
            except (json.JSONDecodeError, KeyError) as e:
                logger.error("Failed to parse JSON response or ID from looker-cli api folder create_folder", extra={"error": str(e), "output": res.stdout if 'res' in locals() else None})
                raise

    logger.info("Found Space ID", extra={"id": target_id})
    return str(target_id[0])


def import_content(content_type, content_json, space_id, creds, debug=False):
    assert content_type in ["dashboard", "look"], "Unsupported Content Type"

    logger.info(
        "Deploying content",
        extra={
            "content_type": content_type,
            "source_file": content_json,
            "folder_id": space_id,
            "active_thread": threading.get_ident()
        }
    )

    command = [
        "looker-cli",
        content_type,
        "import",
        content_json,
        str(space_id),
        "--force"
    ]

    try:
        run_cli_command(command, creds=creds, check=True, capture_output=True, text=True)
    except LookerCLIError as e:
        logger.error("looker-cli import failed", extra={"stdout": e.stdout, "stderr": e.stderr})
        raise


def build_spaces(spaces, creds, debug=False):
    # seeding initial value of parent id to Shared
    # We use a list to aid in debugging should values not drain properly"
    id_tracker = ["0"]

    for space in spaces:
        # Gazer replaces slashes in folder names with division slashes (Unicode character 2215), so undo that.
        space = space.replace("\u2215", "/")

        logger.debug("parent_id to use", extra={"id_tracker": id_tracker})
        # Pull last value from id_tracker
        space_parent = id_tracker.pop()

        logger.debug("data for folder creation", extra={"folder": space, "folder_parent": space_parent})
        space_id = create_or_return_space(space, space_parent, creds, debug)

        # Add new id to id_tracker
        id_tracker.append(space_id)
        logger.debug("parent_id_tracker updated", extra={"parent_id_tracker": id_tracker})

    # We need the final value of the id_tracker so we know what id to deploy content to
    return id_tracker[0]


def deploy_space(s, creds, recursive, target_base, debug=False):

    # Normalize slashes manually to support simulated Windows tests on Linux
    s = s.replace("/", os.sep).replace("\\", os.sep)
    if not s.endswith(os.sep):
        s += os.sep

    logger.debug("working folder", extra={"working_folder": s})

    # grab the relevant files for deployment
    space_files = [f for f in os.listdir(s) if os.path.isfile(os.path.join(s, f))]
    space_children = [os.path.join(s, d) + os.sep for d in os.listdir(s) if os.path.isdir(os.path.join(s, d))]
    look_files = [os.path.join(s, i) for i in space_files if re.search("^Look", i)]
    dash_files = [os.path.join(s, i) for i in space_files if re.search("^Dashboard", i)]
    logger.debug("files to process", extra={"looks": look_files, "dashboards": dash_files})

    # cut down directory to looker-specific paths
    a, b, c = s.partition(target_base)
    c = c.rpartition(os.sep)[0]
    logger.debug("partition components", extra={"a": a, "b": b, "c": c})

    # turn into a list of spaces to process
    spaces_to_process = "".join([b, c]).split(os.sep)
    # Strip Folder_ID_ prefix from folder names (added by looker-cli export)
    spaces_to_process = [re.sub(r"^Folder_\d+_", "", x) for x in spaces_to_process if x]
    logger.debug("folders to process", extra={"folders": spaces_to_process})

    # The final value of id_tracker in build_spaces must be the targeted space id
    space_id = build_spaces(spaces_to_process, creds, debug)
    logger.debug("target folder id", extra={"folder_id": space_id})

    # deploy looks
    logger.debug("running looks", extra={"looks": look_files})
    with ThreadPoolExecutor(max_workers=3) as pool:
        pool.map(
            import_content,
            repeat("look"),
            look_files,
            repeat(space_id),
            repeat(creds),
            repeat(debug)
        )
    # deploy dashboards
    logger.debug("running dashboards", extra={"dashboards": dash_files})
    with ThreadPoolExecutor(max_workers=3) as pool:
        pool.map(
            import_content,
            repeat("dashboard"),
            dash_files,
            repeat(space_id),
            repeat(creds),
            repeat(debug)
        )

    # go for recursion
    if recursive and space_children:
        logger.info("Attemting Recursion of children folders", extra={"children_folders": space_children})
        for child in space_children:
            deploy_space(child, creds, recursive, target_base, debug)
    else:
        logger.info("No Recursion specified or empty child list", extra={"children_folders": space_children})


def deploy_content(content_type, content, creds, target_base, debug=False):
    # extract directory path
    dirs = content.rpartition(os.sep)[0] + os.sep

    # cut down directory to looker-specific paths
    a, b, c = dirs.partition(target_base)
    c = c.rpartition(os.sep)[0]  # strip trailing slash

    # turn into a list of spaces to process
    spaces_to_process = "".join([b, c]).split(os.sep)

    # The final value of id_tracker in build_spaces must be the targeted space id
    space_id = build_spaces(spaces_to_process, creds, debug)

    import_content(content_type, content, space_id, creds, debug)


def send_content(
    creds, target_folder=None, spaces=None, dashboards=None, looks=None, recursive=False, debug=False, target_base=None
):

    if spaces:
        logger.debug("Deploying folders", extra={"folders": spaces})
        # Loop through spaces
        for s in spaces:
            logger.debug("working folder", extra={"working_folder": s})
            # Check for a target space override
            if target_folder:
                logger.info("target folder override found", extra={"target_folder": target_folder})
                # In order for recursion to continue to work properly, the actual directory needs to be updated
                # Create a temporary directory to contain updated space. Context block will auto-clean when done
                with tempfile.TemporaryDirectory() as d:
                    updated_space = os.path.join(d, target_folder)
                    # copy the source space directory tree to target space override
                    shutil.copytree(s, updated_space)
                    # kick off the job from the new space
                    deploy_space(updated_space, creds, recursive, target_base, debug)
            # If no target space override, kick off job normally
            else:
                deploy_space(s, creds, recursive, target_base, debug)
    if dashboards:
        logger.debug("Deploying dashboards", extra={"dashboards": dashboards})
        for dash in dashboards:
            logger.debug("working dashboard", extra={"dashboard": dash})
            # Check for target space override
            if target_folder:
                logger.info("target folder override found", extra={"target_folder": target_folder})
                # In order for recursion to continue to work properly, the actual directory needs to be updated
                # Create a temporary directory to contain updated space. Context block will auto-clean when done
                with tempfile.TemporaryDirectory() as d:
                    # copy the dashboard file to target space override
                    target_dir = os.path.join(d, target_folder)
                    os.makedirs(target_dir)
                    shutil.copy(dash, target_dir)
                    new_dash_path = [os.path.join(target_dir, f) for f in os.listdir(target_dir)][0]
                    # kick off the job from the new space
                    deploy_content("dashboard", new_dash_path, creds, target_base, debug)
            else:
                deploy_content("dashboard", dash, creds, target_base, debug)
    if looks:
        logger.debug("Deploying looks", extra={"looks": looks})
        for look in looks:
            logger.debug("working look", extra={"look": look})
            # Check for target space override
            if target_folder:
                logger.info("target folder override found", extra={"target_folder": target_folder})
                # In order for recursion to continue to work properly, the actual directory needs to be updated
                # Create a temporary directory to contain updated space. Context block will auto-clean when done
                with tempfile.TemporaryDirectory() as d:
                    # copy the look file to target space override
                    target_dir = os.path.join(d, target_folder)
                    os.makedirs(target_dir)
                    shutil.copy(look, target_dir)
                    new_look_path = [os.path.join(target_dir, f) for f in os.listdir(target_dir)][0]
                    # kick off the job from the new space
                    deploy_content("look", new_look_path, creds, target_base, debug)
            else:
                deploy_content("look", look, creds, target_base, debug)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("ini file", extra={"ini": args.ini})

    if args.target_folder:
        # Make sure trailing sep is in place
        if not args.target_folder.endswith(os.sep):
            args.target_folder += os.sep
        args.target_base = args.target_folder.split('/')[0]
    else:
        args.target_base = 'Shared'

    try:
        creds = build_creds(args.ini, args.env)
        send_content(
            creds,
            args.target_folder,
            args.folders,
            args.dashboards,
            args.looks,
            args.recursive,
            args.debug,
            args.target_base
        )
    except LookerCLIError as e:
        logger.error("Deployment failed", extra={"error": str(e)})
        raise RuntimeError("Deployment failed due to CLI error") from e
