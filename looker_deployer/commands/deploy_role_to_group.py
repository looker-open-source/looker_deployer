import logging
import re
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.get_client import get_client
from looker_deployer.utils.match_by_key import match_by_key

logger = deploy_logging.get_logger(__name__)


def get_filtered_roles(source_sdk, pattern=None):
    roles = source_sdk.all_roles()

    logger.debug(
        "Roles pulled",
        extra={
            "role_names": [i.name for i in roles]
        }
    )

    if pattern:
        compiled_pattern = re.compile(pattern)
        roles = [i for i in roles if compiled_pattern.search(i.name)]
        logger.debug(
            "Rolesfiltered",
            extra={
                "filtered_roles": [i.name for i in roles],
                "pattern": pattern
            }
        )

    return roles


def write_role_to_group(source_sdk, target_sdk, pattern=None):

    # INFO: Get all roles and groups information
    roles = get_filtered_roles(source_sdk, pattern)
    target_roles = get_filtered_roles(target_sdk, pattern)
    target_groups = target_sdk.all_groups()

    # INFO: Start Loop of Update on Target
    for role in roles:
        matched_role = match_by_key(target_roles, role, "name")
        role_groups = source_sdk.role_groups(role.id)

        # INFO: Need to loop through the role groups and find
        # corresponding target group match
        for i, role_group in enumerate(role_groups):
            target_group = match_by_key(target_groups, role_group, "name")

            if target_group:
                role_group.id = target_group.id
                role_groups[i] = role_group
            else:
                role_groups.remove(role_group)

        # INFO: Perform update to target role group
        groups_for_update = [i.id for i in role_groups]
        logger.debug("Updating Role Group. Updating...")
        logger.debug("Deploying Role Group",
                     extra={"role_name": role.name,
                            "group_ids": groups_for_update})
        target_sdk.set_role_groups(role_id=matched_role.id,
                                   body=groups_for_update)
        logger.info("Deployment Complete",
                    extra={"role_name": role.name,
                           "group_ids": groups_for_update})


def main(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)

    source_sdk = get_client(args.ini, args.source)

    for t in args.target:
        target_sdk = get_client(args.ini, t)
        write_role_to_group(source_sdk, target_sdk, args.pattern)
