import requests
import argparse
import oyaml as yaml
from requests import ConnectionError
from utils import deploy_logging
from utils import parse_ini

logger = deploy_logging.get_logger(__name__)
webhooks = parse_ini.read_ini("./looker.ini")["Webhooks"]


def get_secret(target):
    logger.info("Fetching secret", extra={"target": target})
    secret = webhooks[f"looker_{target.lower()}_deploy_secret"]
    return {"X-Looker-Deploy-Secret": secret}


def parse_hub_endpoints(config):
    instances = config["instances"]
    if config.get("hub_deploy_exclude"):
        logger.info("Detected exclude list", extra={"excluded": config.get("hub_deploy_exclude")})
        excludes = config.get("hub_deploy_exclude")
        endpoints = [i["endpoint"] for i in instances if i["name"] not in excludes]
    else:
        endpoints = [i["endpoint"] for i in instances]

    logger.info("Parsed endpoints", extra={"endpoints": endpoints})
    return endpoints


def parse_spoke_config(spoke_name, config):
    spoke_config = [i for i in config["instances"] if i["name"] == spoke_name][0]
    logger.info("Parsed spoke config", extra={"config": spoke_config})

    return spoke_config


def parse_hub_excludes(config, arg=None):
    if arg and type(config.get("hub_deploy_exclude")) == list:
        config["hub_deploy_exclude"].append(args.hub_exclude)
    elif args.hub_exclude:
        config["hub_deploy_exclude"] = args.hub_exclude


def deploy_code(project, endpoint, header):
    deploy_url = "/".join(
        [
            endpoint,
            "webhooks",
            "projects",
            project,
            "deploy"
        ]
    )

    logger.info("Deploying", extra={"project": project, "deploy_url": deploy_url})

    try:
        r = requests.get(deploy_url, headers=header)
        assert r.status_code == 200, "Bad response code"
    except ConnectionError as e:
        logger.error("URL Not Found - check %s's config endpoint for typos?", project)
        raise e
    except AssertionError as e:
        if r.status_code == 500:
            logger.error("Bad authorization attempt - check environment variable settings for webhook deploy secret")
            raise e
        else:
            logger.error("Unknown Error: %s", str(r.json()))
            raise e
    results = r.json()["operations"][0]["results"][0]
    logger.info("Deployment complete. Status: %s", results)
    return r.json()


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", action="store_true", help="flag to deploy hub project")
    parser.add_argument("--spoke", nargs='+', help="which spoke(s) to deploy")
    parser.add_argument("--hub-exclude", nargs="+", help="which projects should be ignored from hub deployment")
    args = parser.parse_args()

    with open("./code_config.yaml") as f:
        config = yaml.safe_load(f)

    if args.hub:
        project = config["hub_project"]
        target = "hub"

        parse_hub_excludes(config, args.hub_exclude)

        endpoints = parse_hub_endpoints(config)
        auth_header = get_secret(target)

        for endpoint in endpoints:
            logger.info("Deploying hub to %s", endpoint)
            deploy_code(project, endpoint, auth_header)

    if args.spoke:

        for i in args.spoke:
            try:
                spoke_config = parse_spoke_config(i, config)
            except IndexError:
                logger.error("Invalid name %s. Skipping...", i)
                continue

            project = spoke_config["spoke_project"]
            target = spoke_config["name"]
            endpoint = spoke_config["endpoint"]
            auth_header = get_secret(target)

            deploy_code(project, endpoint, auth_header)
