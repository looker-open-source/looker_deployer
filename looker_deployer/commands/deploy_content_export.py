import os
import subprocess
import logging
from pathlib import Path
from looker_deployer.utils import deploy_logging
from looker_deployer.commands.deploy_content import get_gzr_creds


logger = deploy_logging.get_logger(__name__)


def export_spaces(env, ini, path, debug=False):
    host, port, client_id, client_secret, verify_ssl = get_gzr_creds(ini, env)

    gzr_command = [
        "gzr",
        "space",
        "export",
        "1",
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


def recurse_folders(folder_id, folder_list, sdk):
    space = sdk.space(str(folder_id))
    folder_list.append(space.name)
    if space.parent_id:
        recurse_folders(space.parent_id, folder_list)


def send_export(export_spaces, local_target, sdk):
    for s in export_spaces:
        # create local directory

        # generate the list of folders
        folder_list = []
        recurse_folders(s, folder_list, sdk)
        folder_list.reverse()

    pass


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("ini file", extra={"ini": args.ini})

    for folder in args.folders:
        assert folder.startswith("Shared"), "Export folder paths MUST begin with 'Shared'"
    logger.info(
        "Exporting content",
        extra={"env": args.env, "folders": args.folders, "local_target": args.local_target}
    )
    export_spaces(args.env, args.ini, args.export, args.debug)
