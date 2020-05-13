import logging
import re
from looker_sdk import client, error
from looker_deployer.utils import deploy_logging
from looker_deployer.utils import parse_ini

logger = deploy_logging.get_logger(__name__)


def get_client(ini, env):
    sdk = client.setup(config_file=ini, section=env)
    return sdk


def get_filtered_connections(source_sdk, pattern=None):
    connections = source_sdk.all_connections()

    logger.debug(
        "Connections pulled",
        extra={
            "connection_names": [i.name for i in connections]
        }
    )

    if pattern:
        compiled_pattern = re.compile(pattern)
        connections = [i for i in connections if compiled_pattern.search(i.name)]
        logger.debug(
            "Connections filtered",
            extra={
                "filtered_connections": [i.name for i in connections],
                "pattern": pattern
            }
        )

    return connections


def write_connections(connections, target_sdk, db_config=None):
    for conn in connections:
        conn_exists = True
        try:
            target_sdk.connection(conn.name)
        except error.SDKError:
            conn_exists = False

        if db_config:
            logger.debug("Attempting password update", extra={"connection": conn.name})
            db_pass = db_config[conn.name]
            conn.password = db_pass

        if not conn_exists:
            logger.debug("No existing connection found. Creating...")
            logger.info("Deploying connection", extra={"connection": conn.name})
            target_sdk.create_connection(conn)
            logger.info("Deployment complete", extra={"connection": conn.name})
        else:
            logger.debug("Existing connection found. Updating...")
            logger.info("Deploying connection", extra={"connection": conn.name})
            target_sdk.update_connection(conn.name, conn)
            logger.info("Deployment complete", extra={"connection": conn.name})


def send_connections(source_sdk, target_sdk, pattern=None, db_config=None):
    connections = get_filtered_connections(source_sdk, pattern)
    write_connections(connections, target_sdk, db_config)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.include_password:
        db_config = parse_ini.read_ini(args.ini)["Databases"]
    else:
        db_config = None

    source_sdk = get_client(args.ini, args.source)

    for t in args.target:
        target_sdk = get_client(args.ini, t)

        send_connections(source_sdk, target_sdk, args.pattern, db_config)
