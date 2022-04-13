import logging
import re
from looker_sdk import models
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.get_client import get_client
from looker_deployer.utils.match_by_key import match_by_key

logger = deploy_logging.get_logger(__name__)


def get_filtered_roles(source_sdk, pattern=None):
    roles = source_sdk.all_roles()
    roles = [i for i in roles if not i.name == "Admin"]
    logger.debug(
        "Roles pulled",
        extra={
            "roles_names": [i.name for i in roles]
        }
    )

    if pattern:
        compiled_pattern = re.compile(pattern)
        roles = [i for i in roles if compiled_pattern.search(i.name)]
        logger.debug(
            "Roles filtered",
            extra={
                "filtered_roles": [i.name for i in roles],
                "pattern": pattern
            }
        )

    return roles


def write_roles(roles, target_sdk, pattern=None, allow_delete=None):

    # INFO: Get all roles from target instances that match pattern for name
    target_roles = get_filtered_roles(target_sdk, pattern)

    # INFO: Get all permission sets and models from target instances
    target_permission_sets = target_sdk.all_permission_sets()
    target_model_sets = target_sdk.all_model_sets()

    # INFO: Start Loop of Create/Update on Target
    for role in roles:
        # INFO: Create Role
        new_role = models.WriteRole()
        new_role.__dict__.update(role.__dict__)

        # INFO: For the role being created or updated, need to swap the
        # permission set and model set ids
        matched_permission_set = match_by_key(target_permission_sets,
                                              role.permission_set, "name")
        matched_model_set = match_by_key(target_model_sets,
                                         role.model_set, "name")
        new_role.permission_set_id = matched_permission_set.id
        new_role.model_set_id = matched_model_set.id

        # INFO: Test if role is already in target
        matched_role = match_by_key(target_roles, role, "name")

        if matched_role:
            role_exists = True
        else:
            role_exists = False

        # INFO: Create or Update the role
        if not role_exists:
            logger.debug("No Role found. Creating...")
            logger.debug("Deploying Role", extra={"role": role.name})
            matched_role = target_sdk.create_role(new_role)
            logger.info("Deployment complete", extra={"role": new_role.name})
        else:
            logger.debug("Existing Role found. Updating...")
            logger.debug("Deploying Role", extra={"role": new_role.name})
            matched_role = target_sdk.update_role(matched_role.id, new_role)
            logger.info("Deployment complete", extra={"role": new_role.name})

    # INFO: Delete missing roles that are not in the source
    if allow_delete:
        for target_role in target_roles:

            # INFO: Test if model set is already in target
            matched_role = match_by_key(roles, target_role, "name")

            if not matched_role:
                logger.debug("No Source Role found. Deleting...")
                logger.debug("Deleting Role", extra={"role": target_role.name})
                target_sdk.delete_role(target_role.id)
                logger.info("Delete complete",
                            extra={"role": target_role.name})


def send_roles(source_sdk, target_sdk, pattern=None, allow_delete=None):
    # INFO: Get all roles from source instance
    roles = get_filtered_roles(source_sdk, pattern)
    write_roles(roles, target_sdk, pattern, allow_delete)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    source_sdk = get_client(args.ini, args.source)

    for t in args.target:
        target_sdk = get_client(args.ini, t)
        send_roles(source_sdk, target_sdk, args.pattern, args.delete)
