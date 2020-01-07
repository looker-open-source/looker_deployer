import networkx as nx
import os
import re
import subprocess
import argparse
from utils import deploy_logging
from looker_sdk import client, models


logger = deploy_logging.get_logger(__name__)


def get_client(ini, env):
    sdk = client.setup(config_file=ini, section=env)
    return sdk


def get_space_ids_from_name(space_name, sdk):
    if space_name == "Shared":
        return [1]
    space_list = sdk.search_spaces(name=space_name)
    id_list = [i.id for i in space_list]

    return id_list


def create_or_return_space(space_name, parent_id, sdk):

    try:
        target_id = get_space_ids_from_name(space_name, sdk)
        logger.debug("Space ID from name", extra={"id": target_id})
        assert len(target_id) == 1
    except AssertionError as e:
        if len(target_id) > 1:
            logger.error("More than one Space found with that name", extra={"space_ids": target_id})
            raise e
        else:
            logger.warning("No spaces found. Creating space now")
            new_space = models.Space(name=space_name, parent_id=parent_id)
            res = sdk.create_space(new_space)
            return res.id

    logger.info("Found Space ID", extra={"id": target_id})
    return target_id[0]


def build_directory_graph(root_dir):
    dg = nx.DiGraph()
    for p, d, f in os.walk(root_dir):
        cleaned = p.rstrip(os.path.sep)
        endpoint = cleaned.rpartition(os.path.sep)[2]

        space_file = [i for i in f if re.search("^Space", i)][0]
        look_files = [i for i in f if re.search("^Look", i)]
        dash_files = [i for i in f if re.search("^Dashboard", i)]

        edge_tups = [(endpoint, i) for i in d]
        dg.add_edges_from(edge_tups)
        dg.add_node(endpoint, space=space_file, looks=look_files, dashboards=dash_files, path=p)

    return dg


def parse_content_path(path):
    path = path.rstrip(os.path.sep)
    first, sep, content_file = path.rpartition(os.path.sep)
    content_space = first.rpartition(os.path.sep)[2]
    ref = {
        "content_space": content_space,
        "content_file": content_file
    }

    logger.debug("Parsed content path", extra={"ref": ref})
    return ref


def import_content(content_type, content_json, space_id, host):
    logger.info("Deploying content", extra={"type": content_type, "source_file": content_json, "space_id": space_id})

    assert content_type in ["dashboard", "look"], "Unsupported Content Type"

    subprocess.call([
            "gzr",
            content_type,
            "import",
            content_json,
            space_id,
            "--host",
            host,
            "--force"
    ])


def deploy_space(space, dg, sdk):
    if space == "Shared":
        space_id = 1
    else:
        space_parent = get_space_ids_from_name(list(dg.predecessors(space))[0], sdk)
        space_id = create_or_return_space(space, space_parent, sdk)

    return space_id


def deploy_content(content_type, content_list, dg, root_dir, sdk, host):
    for c in content_list:
        parsed = parse_content_path(c)
        host_space = parsed["content_space"]
        spaces_to_process = nx.shortest_path(dg, root_dir, host_space)

        for space in spaces_to_process:
            space_id = deploy_space(space, dg, sdk)

            if space == host_space:
                # deploy the content
                import_content(content_type, c, space_id, host)


def main(root_dir, sdk, host, spaces=None, dashboards=None, looks=None):
    dg = build_directory_graph(root_dir)
    root = parse_content_path(root_dir)["content_file"]
    logger.debug("Parsed root", extra={"root": root})

    if spaces:
        logger.debug("Deploying spaces", extra={"spaces": spaces})
        for s in spaces:
            parsed_space = parse_content_path(s)["content_file"]
            logger.debug("Working on space", extra={"space": s, "parsed_space": parsed_space})
            spaces_to_process = nx.shortest_path(dg, root, parsed_space)
            logger.debug("Shortest path found", extra={"spaces_to_process": spaces_to_process})

            for space in spaces_to_process:
                space_id = deploy_space(space, dg, sdk)

                if space == parsed_space:
                    path = dg.nodes[parsed_space]["path"]
                    # deploy looks
                    for look in dg.nodes[parsed_space]["looks"]:
                        look_path = os.path.join(path, look)
                        import_content("look", look_path, space_id, host)
                    # deploy dashboards
                    for dash in dg.nodes[parsed_space]["dashboards"]:
                        dash_path = os.path.join(path, dash)
                        import_content("dashboard", dash_path, space_id, host)

    if dashboards:
        deploy_content("dashboard", dashboards, dg, root, sdk, host)
    if looks:
        deploy_content("look", looks, dg, root, sdk, host)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", help="Path to the root Shared directory")
    parser.add_argument("--env", help="What environment to deploy to")
    parser.add_argument("--host", help="gzr host to use")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--spaces", nargs="+", help="Spaces to fully deploy")
    group.add_argument("--dashboards", nargs="+", help="Dashboards to deploy")
    group.add_argument("--looks", nargs="+", help="Looks to deploy")
    args = parser.parse_args()

    sdk = get_client("looker.ini", args.env)

    main(args.root, sdk, args.host, args.spaces, args.dashboards, args.looks)
