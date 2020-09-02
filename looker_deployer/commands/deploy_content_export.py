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


def recurse_folders(folder_id, folder_list, sdk, debug=False):
    space = sdk.space(str(folder_id))
    folder_list.append(space.name)
    if space.parent_id:
        recurse_folders(space.parent_id, folder_list)


def send_export(folder_ids, local_target, env, ini, sdk, debug=False):
    for fid in folder_ids:

        # generate the list of folders
        folder_list = []
        recurse_folders(fid, folder_list, sdk)
        # list is generated in reverse order, so we have to correct
        folder_list.reverse()

        # create the target directory. Parent is called b/c the final directory is created during export
        path = Path([local_target] + folder_list).parent
        path.mkdir(parents=True, exist_ok=True)

        # export the folder
        export_spaces(fid, env, ini, str(path), debug)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("ini file", extra={"ini": args.ini})

    logger.info(
        "Exporting content",
        extra={"env": args.env, "folders": args.folders, "local_target": args.local_target}
    )
    sdk = get_client(args.ini, args.env)
    send_export(args.folders, args.local_target, args.env, args.ini, sdk, args.debug)
