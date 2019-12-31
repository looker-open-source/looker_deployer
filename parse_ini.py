import configparser
import deploy_logging

logger = deploy_logging.get_logger(__name__)


def read_ini(ini="./looker.ini"):
    logger.info("Reading config file", extra={"file": ini})

    config = configparser.ConfigParser()
    config.read(ini)

    return config
