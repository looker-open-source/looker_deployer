import os
import re
import subprocess
import argparse
import logging
from utils import deploy_logging
from utils import parse_ini
from looker_sdk import client, models


logger = deploy_logging.get_logger(__name__)


def get_client(ini, env):
    sdk = client.setup(config_file=ini, section=env)
    return sdk


def get_space_ids_from_name(space_name, parent_id, sdk):
    if (space_name == "Shared" and parent_id == "0"):
        return ["1"]
    space_list = sdk.search_spaces(name=space_name, parent_id=parent_id)
    id_list = [i.id for i in space_list]

    return id_list


def create_or_return_space(space_name, parent_id, sdk):

    try:
        target_id = get_space_ids_from_name(space_name, parent_id, sdk)
        logger.debug("Space ID from name", extra={"id": target_id})
        assert len(target_id) == 1
    except AssertionError as e:
        if len(target_id) > 1:
            logger.error("More than one Space found with that parent/name", extra={"space_ids": target_id})
            raise e
        else:
            logger.warning("No spaces found. Creating space now")
            new_space = models.Space(name=space_name, parent_id=parent_id)
            res = sdk.create_space(new_space)
            return res.id

    logger.info("Found Space ID", extra={"id": target_id})
    return target_id[0]


def parse_root(content, root="Shared"):
    a, b, c = content.partition(root)
    root_dir = "".join([a, b])
    logger.debug("Parsed root", extra={"content": content, "root_arg": root, "parsed_root": root_dir})

    return root_dir


def get_gzr_creds(ini, env):
    ini = parse_ini.read_ini(ini)
    env_record = ini[env]
    host = env_record["base_url"].lstrip("https://").split(":")[0]
    client_id = env_record["client_id"]
    client_secret = env_record["client_secret"]

    return (host, client_id, client_secret)


def export_spaces(env, ini, path):
    host, client_id, client_secret = get_gzr_creds(ini, env)

    subprocess.call([
        "gzr",
        "space",
        "export",
        "1",
        "--dir",
        path,
        "--host",
        host,
        "--client_id",
        client_id,
        "--client_secret",
        client_secret
    ])


def import_content(content_type, content_json, space_id, env, ini):
    assert content_type in ["dashboard", "look"], "Unsupported Content Type"
    host, client_id, client_secret = get_gzr_creds(ini, env)

    logger.info(
        "Deploying content",
        extra={
            "content_type": content_type,
            "source_file": content_json,
            "space_id": space_id,
            "host": host,
            "client_id": client_id
        }
    )

    subprocess.call([
        "gzr",
        content_type,
        "import",
        content_json,
        space_id,
        "--host",
        host,
        "--client_id",
        client_id,
        "--client-secret",
        client_secret,
        "--force"
    ])


def build_spaces(spaces):
    # seeding initial value of parent id to Shared
    id_tracker = ["0"]

    for space in spaces:
        logger.debug("parent_id to use", extra={"id_tracker": id_tracker})
        space_parent = id_tracker.pop()

        logger.debug("data for space creation", extra={"space": space, "space_parent": space_parent})
        space_id = create_or_return_space(space, space_parent, sdk)

        # Add new id to parent tracker
        id_tracker.append(space_id)
        logger.debug("parent_id_tracker updated", extra={"parent_id_tracker": id_tracker})

    return id_tracker[0]


def deploy_space(spaces, sdk, env, ini, recursive):

    logger.debug("Deploying spaces", extra={"spaces": spaces})
    for s in spaces:

        logger.debug("working space", extra={"working_space": s})

        # grab the relevant files for deployment
        space_files = [f for f in os.listdir(s) if os.path.isfile(os.path.join(s, f))]
        space_children = [os.path.join(s, d) + "/" for d in os.listdir(s) if os.path.isdir(os.path.join(s, d))]
        look_files = [os.path.join(s, i) for i in space_files if re.search("^Look", i)]
        dash_files = [os.path.join(s, i) for i in space_files if re.search("^Dashboard", i)]
        logger.debug("files to process", extra={"looks": look_files, "dashboards": dash_files})

        # cut down directory to looker-specific paths
        a, b, c = s.partition("Shared")  # Hard coded to Shared for now TODO: Change this!
        logger.debug("space components", extra={"a": a, "b": b, "c": c})
        c = c.rpartition(os.path.sep)[0]
        logger.debug("new c value", extra={"c": c})

        # turn into a list of spaces to process
        spaces_to_process = "".join([b, c]).split(os.path.sep)
        logger.debug("spaces to process", extra={"spaces": spaces_to_process})

        space_id = build_spaces(spaces_to_process)
        logger.debug("target space id", extra={"space_id": space_id})

        # deploy looks
        for look in look_files:
            import_content("look", look, space_id, env, ini)
        # deploy dashboards
        for dash in dash_files:
            import_content("dashboard", dash, space_id, env, ini)

        # go for recursion
        if recursive and space_children:
            logger.debug("Attemting Recursion of children spaces", extra={"children_spaces": space_children})
            for child in space_children:
                deploy_space([child], sdk, env, ini, recursive)
        else:
            logger.debug("No Recursion specified or empty child list", extra={"children_spaces": space_children})


def deploy_content(content_type, content_list, sdk, env, ini):
    for c in content_list:

        # extract directory path
        dirs = c.rpartition(os.path.sep)[0]

        # cut down directory to looker-specific paths
        a, b, c = dirs.partition("Shared")  # Hard coded to Shared for now TODO: Change this!
        c = c.rpartition(os.path.sep)[0]  # strip trailing slash

        # turn into a list of spaces to process
        spaces_to_process = "".join([b, c]).split(os.path.sep)

        space_id = build_spaces(spaces_to_process)

        import_content(content_type, c, space_id, env, ini)


def main(sdk, env, ini, spaces=None, dashboards=None, looks=None, recursive=False):

    if spaces:
        deploy_space(spaces, sdk, env, ini, recursive)
    if dashboards:
        deploy_content("dashboard", dashboards, sdk, env, ini)
    if looks:
        deploy_content("look", looks, sdk, env, ini)


if __name__ == "__main__":

    loc = os.path.join(os.path.dirname(os.path.realpath(__file__)), "looker.ini")

    parser = argparse.ArgumentParser()
    parser.add_argument("--env", help="What environment to deploy to")
    parser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    parser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    parser.add_argument("--recursive", action="store_true", help="Should spaces deploy recursively")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--spaces", nargs="+", help="Spaces to fully deploy")
    group.add_argument("--dashboards", nargs="+", help="Dashboards to deploy")
    group.add_argument("--looks", nargs="+", help="Looks to deploy")
    group.add_argument("--export", help="pull content from dev")
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("ini file", extra={"ini": args.ini})

    if args.export:
        logger.info("Pulling content from dev", extra={"env": args.env, "pull_location": args.export})
        export_spaces(args.env, args.ini, args.export)
    else:
        sdk = get_client(args.ini, args.env)
        main(sdk, args.env, args.ini, args.spaces, args.dashboards, args.looks, args.recursive)
