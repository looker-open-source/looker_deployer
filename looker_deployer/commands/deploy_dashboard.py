import json
import logging
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.get_client import get_client
from typing import Optional, cast
from looker_sdk import models40 as mdls
from looker_sdk.rtl import transport

logger = deploy_logging.get_logger(__name__)


def import_dashboard_from_lookml(
    self,
    body: mdls.WriteDashboardLookml,
    transport_options: Optional[transport.TransportOptions] = None,
) -> mdls.DashboardLookml:
    """Import Dashboard from LookML"""
    response = cast(
        mdls.DashboardLookml,
        self.post(
            path="/dashboards/lookml",
            structure=mdls.DashboardLookml,
            body=body,
            transport_options=transport_options
        )
    )
    return response


def dashboard_import(sdk, folder_id, file_name):

    # INFO: Open File contain lookml of dashboard
    with open(file_name, "r") as f:
        dashboard_yaml = json.load(f)
        print("Loaded File")
    # INFO: Deploy Dashboard to folder ID and dashboard definition
    dashboard = import_dashboard_from_lookml(sdk, body=mdls.WriteDashboardLookml(folder_id=folder_id, lookml=dashboard_yaml['lookml']))
    print(dashboard)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("ini file", extra={"ini": args.ini})
    sdk = get_client(args.ini, args.env)

    dashboard_import(
        sdk,
        args.folder_id,
        args.file_name
    )
