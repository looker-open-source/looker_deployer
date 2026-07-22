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

import os  # noqa: F401
import subprocess
import logging
import json
import shutil
from pathlib import Path
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.cli import run_cli_command
from looker_deployer.utils.exceptions import LookerCLIError
from looker_deployer.utils.parse_ini import build_creds


logger = deploy_logging.get_logger(__name__)


def export_spaces(folder_id, creds, path, debug=False):

    command = [
        "looker-cli",
        "folder",
        "export",
        str(folder_id),
        "--dir",
        path
    ]

    try:
        run_cli_command(command, creds=creds, check=True, capture_output=True, text=True)
    except LookerCLIError as e:
        logger.error("looker-cli folder export failed", extra={"stdout": e.stdout, "stderr": e.stderr})
        raise


def export_content(content_type, content_id, creds, path, debug=False):

    command = [
        "looker-cli",
        content_type,
        "cat",
        str(content_id)
    ]

    filename = Path(path) / f"{content_type}_{content_id}.json"
    try:
        with open(filename, "w") as outfile:
            # We still need to pass stderr=subprocess.PIPE if we want to capture it,
            # but run_cli_command now defaults to capture_output=True if stdout/stderr are not set.
            # Here stdout is set to outfile, so capture_output won't be set by default.
            # We explicitly pass stderr=subprocess.PIPE to capture errors.
            run_cli_command(command, stdout=outfile, stderr=subprocess.PIPE, creds=creds, check=True, text=True)
    except LookerCLIError as e:
        logger.error(f"looker-cli {content_type} cat failed", extra={"stdout": e.stdout, "stderr": e.stderr})
        raise


def recurse_folders(folder_id, folder_list, creds, debug=False):
    command = ["looker-cli", "folder", "cat", str(folder_id)]

    try:
        result = run_cli_command(command, creds=creds, check=True, capture_output=True, text=True)
        space = json.loads(result.stdout)

        folder_list.append(space["name"])
        logger.debug(
            "recursive folder crawl status",
            extra={"current_id": folder_id, "folder_name": space["name"], "current_list": folder_list}
        )
        if space.get("parent_id"):
            logger.debug("going for recursion", extra={"parent_id": space["parent_id"]})
            recurse_folders(space["parent_id"], folder_list, creds, debug)
    except LookerCLIError as e:
        logger.error(
            "Failed to retrieve folder information",
            extra={
                "stdout": e.stdout,
                "stderr": e.stderr,
                "folder_id": folder_id,
                "error": str(e)
            }
        )
        raise
    except json.JSONDecodeError as e:
        logger.error("Failed to parse folder information", extra={"folder_id": folder_id, "error": str(e)})
        raise

    return folder_list


def send_export(
    creds, local_target, folders=None, dashboards=None, looks=None, debug=False
):
    for fid in folders or []:

        # generate the list of folders
        folder_list = []
        folder_list = recurse_folders(fid, folder_list, creds, debug)
        # list is generated in reverse order, so we have to correct
        folder_list.reverse()
        logger.debug("folder_list", extra={"folder_id": fid, "list": folder_list})

        # create the target directory. Parent is called b/c the final directory is created during export
        path_string = "/".join([local_target] + folder_list)
        path = Path(path_string).parent
        path.mkdir(parents=True, exist_ok=True)

        # export the folder
        export_spaces(fid, creds, str(path), debug)

        # Rename Folder_<fid>_<name> to <name>
        folder_name = folder_list[-1]
        created_path = Path(path) / f"Folder_{fid}_{folder_name}"
        target_path = Path(path) / folder_name

        if target_path.exists():
            logger.warning(f"Target directory {target_path} already exists. Overwriting.")
            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()

        if created_path.exists() and created_path.is_dir():
            created_path.rename(target_path)
            logger.debug(f"Renamed exported folder {created_path} to {target_path}")

    for did in dashboards or []:

        logger.debug("dashboard_list", extra={"dashboards": dashboards})

        # create the target directory
        path = Path(local_target)
        path.mkdir(parents=True, exist_ok=True)

        # export the dashboard
        export_content("dashboard", did, creds, str(path), debug)

    for lid in looks or []:

        logger.debug("look_list", extra={"looks": looks})

        # create the target directory
        path = Path(local_target)
        path.mkdir(parents=True, exist_ok=True)

        # export the look
        export_content("look", lid, creds, str(path), debug)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("ini file", extra={"ini": args.ini})

    logger.info(
        "Exporting content",
        extra={"env": args.env, "folders": args.folders, "dashboards": args.dashboards, "looks": args.looks, "local_target": args.local_target}
    )
    try:
        creds = build_creds(args.ini, args.env)
        send_export(
            creds,
            args.local_target,
            args.folders,
            args.dashboards,
            args.looks,
            args.debug
        )
    except LookerCLIError as e:
        logger.error("Export failed", extra={"error": str(e)})
        raise RuntimeError("Export failed due to CLI error") from e
