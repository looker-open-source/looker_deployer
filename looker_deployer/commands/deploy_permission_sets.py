import logging
import re
from looker_sdk import models
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.get_client import get_client
from looker_deployer.utils.match_by_key import match_by_key

logger = deploy_logging.get_logger(__name__)


def get_filtered_permission_sets(source_sdk, pattern=None):
    permission_sets = source_sdk.all_permission_sets()

    logger.debug(
        "Permission Sets pulled",
        extra={
            "permission_sets_names": [i.name for i in permission_sets]
        }
    )

    permission_sets = [i for i in permission_sets if not i.built_in]

    if pattern:
        compiled_pattern = re.compile(pattern)
        permission_sets = [i for i in permission_sets
                           if compiled_pattern.search(i.name)]
        logger.debug(
            "Permission Sets filtered",
            extra={
                "filtered_permission_sets": [i.name for i in permission_sets],
                "pattern": pattern
            }
        )

    return permission_sets


def write_permission_sets(permission_sets, target_sdk, pattern=None,
                          allow_delete=None):

    # INFO: Get all permission sets from target instances that match pattern
    target_permission_sets = get_filtered_permission_sets(target_sdk, pattern)

    # INFO: Start Loop of Create/Update on Target
    for permission_set in permission_sets:
        # INFO: Create permission set
        new_permission_set = models.WritePermissionSet()
        new_permission_set.__dict__.update(permission_set.__dict__)

        # INFO: Test if permission set is already in target
        matched_permission_set = match_by_key(target_permission_sets,
                                              permission_set, "name")

        if matched_permission_set:
            permission_set_exists = True
        else:
            permission_set_exists = False

        # INFO: Create or Update the permission set
        if not permission_set_exists:
            logger.debug("No Permission Set found. Creating...")
            logger.debug("Deploying Permission Set",
                         extra={"permission_set": permission_set.name})
            matched_permission_set = target_sdk.create_permission_set(
                new_permission_set)
            logger.info("Deployment complete",
                        extra={"permission_set": new_permission_set.name})
        else:
            logger.debug("Existing permission set found. Updating...")
            logger.debug("Deploying Permission Set",
                         extra={"permission_set": new_permission_set.name})
            matched_permission_set = target_sdk.update_permission_set(
                matched_permission_set.id,
                new_permission_set)
            logger.info("Deployment complete",
                        extra={"permission_set": new_permission_set.name})

    # INFO:    Delete missing permission sets that are not in source
    if allow_delete:
        for target_permission_set in target_permission_sets:

            # INFO:    Test if model set is already in target
            matched_permission_set = match_by_key(permission_sets,
                                                  target_permission_set,
                                                  "name")

            if not matched_permission_set:
                logger.debug("No Source Permission Set found. Deleting...")
                logger.debug("Deleting Permission Set",
                             extra={"permission_set":
                                    target_permission_set.name})
                target_sdk.delete_permission_set(target_permission_set.id)
                logger.info("Delete complete",
                            extra={"permission_set":
                                   target_permission_set.name})


def send_permission_sets(source_sdk, target_sdk,
                         pattern=None, allow_delete=None):
    # INFO:    Get all permissions sets from source instance
    permission_sets = get_filtered_permission_sets(source_sdk, pattern)
    write_permission_sets(permission_sets, target_sdk, pattern, allow_delete)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    source_sdk = get_client(args.ini, args.source)

    for t in args.target:
        target_sdk = get_client(args.ini, t)
        send_permission_sets(source_sdk, target_sdk, args.pattern, args.delete)
