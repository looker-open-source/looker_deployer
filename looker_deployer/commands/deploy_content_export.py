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
import subprocess
import logging
from pathlib import Path
from looker_deployer.utils import deploy_logging
from looker_deployer.commands.deploy_content import get_gzr_creds
from looker_deployer.utils.get_client import get_client


logger = deploy_logging.get_logger(__name__)


def export_spaces(folder_id, env, ini, path, debug=False):
    host, port, client_id, client_secret, verify_ssl = get_gzr_creds(ini, env)

    gzr_command = [
        "gzr",
        "space",
        "export",
        folder_id,
        "--dir",
        path,
        "--host",
        host,
        "--port",
        port,
        "--client-id",
        client_id,
        "--client-secret",
        client_secret
    ]

    # config parser returns a string - easier to parse that than convert to a bool
    if verify_ssl == "False":
        gzr_command.append("--no-verify-ssl")
    if debug:
        gzr_command.append("--debug")

    # if we're running on windows we need to appropriately call the command-line arg"
    if os.name == "nt":
        win_exec = ["cmd.exe", "/c"]
        gzr_command = win_exec + gzr_command

    subprocess.run(gzr_command)


def export_content(content_type, content_id, env, ini, path, debug=False):
    host, port, client_id, client_secret, verify_ssl = get_gzr_creds(ini, env)

    gzr_command = [
        "gzr",
        content_type,
        "cat",
        content_id,
        "--host",
        host,
        "--port",
        port,
        "--client-id",
        client_id,
        "--client-secret",
        client_secret
    ]

    # config parser returns a string - easier to parse that than convert to a bool
    if verify_ssl == "False":
        gzr_command.append("--no-verify-ssl")
    if debug:
        gzr_command.append("--debug")

    # if we're running on windows we need to appropriately call the command-line arg"
    if os.name == "nt":
        win_exec = ["cmd.exe", "/c"]
        gzr_command = win_exec + gzr_command

    filename = Path(path) / f"{content_type}_{content_id}.json"
    with open(filename, "w") as outfile:
        subprocess.run(gzr_command, stdout=outfile)


def recurse_folders(folder_id, folder_list, sdk, debug=False):
    space = sdk.folder(str(folder_id))
    folder_list.append(space.name)
    logger.debug(
        "recursive folder crawl status",
        extra={"current_id": folder_id, "folder_name": space.name, "current_list": folder_list}
    )
    if space.parent_id:
        logger.debug("going for recursion", extra={"parent_id": space.parent_id})
        recurse_folders(space.parent_id, folder_list, sdk, debug)

    return folder_list


def send_export(
    sdk, env, ini, local_target, folders=None, dashboards=None, looks=None, debug=False
):
    for fid in folders or []:

        # generate the list of folders
        folder_list = []
        folder_list = recurse_folders(fid, folder_list, sdk, debug)
        # list is generated in reverse order, so we have to correct
        folder_list.reverse()
        logger.debug("folder_list", extra={"folder_id": fid, "list": folder_list})

        # create the target directory. Parent is called b/c the final directory is created during export
        path_string = "/".join([local_target] + folder_list)
        path = Path(path_string).parent
        path.mkdir(parents=True, exist_ok=True)

        # export the folder
        export_spaces(fid, env, ini, str(path), debug)

    for did in dashboards or []:

        logger.debug("dashboard_list", extra={"dashboards": dashboards})

        # create the target directory
        path = Path(local_target)
        path.mkdir(parents=True, exist_ok=True)

        # export the dashboard
        export_content("dashboard", did, env, ini, str(path), debug)

    for lid in looks or []:

        logger.debug("look_list", extra={"looks": looks})

        # create the target directory
        path = Path(local_target)
        path.mkdir(parents=True, exist_ok=True)

        # export the look
        export_content("look", lid, env, ini, str(path), debug)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("ini file", extra={"ini": args.ini})

    logger.info(
        "Exporting content",
        extra={"env": args.env, "folders": args.folders, "dashboards": args.dashboards, "looks": args.looks, "local_target": args.local_target}
    )
    sdk = get_client(args.ini, args.env)
    send_export(
        sdk,
        args.env,
        args.ini,
        args.local_target,
        args.folders,
        args.dashboards,
        args.looks,
        args.debug
    )
