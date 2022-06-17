import json
import logging
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.get_client import get_client


logger = deploy_logging.get_logger(__name__)


def dashboard_export(sdk, dashboard_identifier):

    # INFO: Lookup dashboard info to obtain ID/slug
    dashboard = sdk.dashboard(dashboard_id=dashboard_identifier, fields="id,slug,title")

    # INFO: Take dashboard ID and get the YAML string for a UDD
    dashboard_yaml = sdk.dashboard_lookml(dashboard_id=dashboard.id)

    # INFO: Write dashboard YAML to a json file
    # INFO: Going to advocate for a flag to toggle between gazer name or slug (slug is better for programmatic storage)
    # gazer_name = f"Dashboard_{dashboard.id}_{dashboard.title}.json"
    looker_deploy_name = f"{dashboard.slug}.json"

    with open(looker_deploy_name, "w") as f:
        f.write(json.dumps(dashboard_yaml.__dict__))


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("ini file", extra={"ini": args.ini})
    sdk = get_client(args.ini, args.env)

    dashboard_export(
        sdk,
        args.dashboard_identifier
    )
