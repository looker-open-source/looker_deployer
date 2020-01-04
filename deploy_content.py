import os
from operator import itemgetter
from utils import deploy_logging
from looker_sdk import client, models


logger = deploy_logging.get_logger(__name__)


def get_client(ini, env):
    sdk = client.setup(config_file=ini, section=env)
    return sdk


def get_space_ids_from_name(space_name, sdk):
    space_list = sdk.search_spaces(name=space_name)
    id_list = [i.id for i in space_list]

    return id_list


def create_or_return_space(space_name, parent_id, sdk):

    try:
        target_id = get_space_ids_from_name(space_name, sdk)
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

    return target_id[0]


def directory_walker_thing(root_dir, space_list=None, recursive=True):

    dirs_list = []
    for p, d, f in os.walk(root_dir):
        dirs_list.append(p.split(os.path.sep))

    filtered_list = []
    if space_list and recursive:
        for d in dirs_list:
            if set(space_list) & set(d):
                filtered_list.append(d)
    elif space_list:
        for s in space_list:
            for d in dirs_list:
                if d[-1] == s:
                    filtered_list.append(d)
    else:
        filtered_list = dirs_list

    space_dirs = []
    for f in filtered_list:
        for i, j in enumerate(f):
            if i == 0 or j == "":
                continue
            space_dirs.append({"space_name": j, "parent": f[i-1], "rank": len(f)})
            sorted_list = sorted(space_dirs, key=itemgetter("rank"))
            final_list = [i for n, i in enumerate(sorted_list) if i not in sorted_list[n + 1:]]

    return final_list
