import logging
import re
from looker_sdk import models
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.get_client import get_client
from looker_deployer.utils.match_by_key import match_by_key

logger = deploy_logging.get_logger(__name__)


def get_filtered_groups(source_sdk, pattern=None):
    groups = source_sdk.all_groups()

    logger.debug(
        "Groups pulled",
        extra={
            "groups_names": [i.name for i in groups]
        }
    )

    groups = [i for i in groups if not i.externally_managed]

    if pattern:
        compiled_pattern = re.compile(pattern)
        groups = [i for i in groups if compiled_pattern.search(i.name)]
        logger.debug(
            "Groups filtered",
            extra={
                "filtered_groups": [i.name for i in groups],
                "pattern": pattern
            }
        )

    return groups


def write_groups(groups, target_sdk, pattern=None, allow_delete=None):

    # INFO: Get all groups from target instances that match pattern for name
    target_groups = get_filtered_groups(target_sdk, pattern)

    # INFO: Start Loop of Create/Update on Target
    for group in groups:
        # INFO: Create Group
        new_group = models.WriteGroup()
        new_group.__dict__.update(group.__dict__)

        # INFO: Test if group is already in target
        matched_group = match_by_key(target_groups, group, "name")

        if matched_group:
            group_exists = True
        else:
            group_exists = False

        # INFO: Create or Update the Group
        if not group_exists:
            logger.debug("No Group found. Creating...")
            logger.debug("Deploying Group", extra={"group": group.name})
            matched_group = target_sdk.create_group(new_group)
            logger.info("Deployment complete", extra={"group": new_group.name})
        else:
            logger.debug("Existing Group found. Updating...")
            logger.debug("Deploying Group", extra={"group": new_group.name})
            matched_group = target_sdk.update_group(matched_group.id,
                                                    new_group)
            logger.info("Deployment complete", extra={"group": new_group.name})

    # INFO: Delete missing groups that are not in the source
    if allow_delete:
        for target_group in target_groups:

            # INFO: Test if model set is already in target
            matched_group = match_by_key(groups, target_group, "name")

            if not matched_group:
                logger.debug("No Source Group found. Deleting...")
                logger.debug("Deleting Group", extra={"group":
                             target_group.name})
                target_sdk.delete_group(target_group.id)
                logger.info("Delete complete", extra={"group":
                            target_group.name})


def send_groups(source_sdk, target_sdk, pattern=None, allow_delete=None):
    # INFO: Get all groups from source instance
    groups = get_filtered_groups(source_sdk, pattern)
    write_groups(groups, target_sdk, pattern, allow_delete)


def main(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)

    source_sdk = get_client(args.ini, args.source)

    for t in args.target:
        target_sdk = get_client(args.ini, t)
        send_groups(source_sdk, target_sdk, args.pattern, args.delete)
