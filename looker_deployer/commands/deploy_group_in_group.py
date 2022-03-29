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
            "groups_name": [i.name for i in groups]
        }
    )

    groups = [i for i in groups if not i.externally_managed]

    if pattern:
        compiled_pattern = re.compile(pattern)
        groups = [i for i in groups if compiled_pattern.search(i.name)]
        logger.debug(
            "Groups in Group filtered",
            extra={
                "filtered_groups": [i.name for i in groups],
                "pattern": pattern
            }
        )

    return groups


def write_groups_in_group(source_sdk, target_sdk, pattern=None):  # noqa: C901

    # INFO: Get all groups from source and target instances that match pattern
    # for name
    groups = get_filtered_groups(source_sdk, pattern)
    target_groups = get_filtered_groups(target_sdk, pattern=None)

    # INFO: Start Loop of Create/Update on Target
    for group in groups:
        matched_group = match_by_key(target_groups, group, "name")
        logger.debug("Group Matched " + matched_group.name)
        groups_in_group = source_sdk.all_group_groups(group.id)
        target_groups_in_group = target_sdk.all_group_groups(matched_group.id)

        # INFO: Need to loop through the groups in group to identify
        # target group ID
        for i, nested_group in enumerate(groups_in_group):
            target_nested_group = match_by_key(target_groups, nested_group,
                                               "name")

            if target_nested_group:
                nested_group.id = target_nested_group.id
                groups_in_group[i] = nested_group
            else:
                groups_in_group.remove(nested_group)

        # INFO: If groups in groups between instances is different, we need to
        # either delete or create
        source_group_ids = []
        for nested_group in groups_in_group:
            source_group_ids.append(nested_group.id)

        target_group_ids = []
        for nested_group in target_groups_in_group:
            target_group_ids.append(nested_group.id)

        all_group_ids = list(set().union(source_group_ids, target_group_ids))

        for group_id in all_group_ids:
            in_source = True
            in_target = True
            try:
                source_group_ids.index(group_id)
            except Exception:
                in_source = False

            try:
                target_group_ids.index(group_id)
            except Exception:
                in_target = False

            if in_source and not in_target:
                logger.debug("No Groups in Group found. Creating...")
                logger.debug("Deploying Groups in Group",
                             extra={"group_name": group.name,
                                    "group_group_id": group_id})
                target_sdk.add_group_group(group_id=matched_group.id,
                                           body=models.GroupIdForGroupInclusion
                                           (group_id=group_id))
                logger.info("Deployment Complete",
                            extra={"group_name": group.name,
                                   "group_group_id": group_id})

            elif not in_source and in_target:
                logger.debug("Extra Groups in Group found. Deleting...")
                logger.debug("Removing Groups in Group",
                             extra={"group_name": group.name,
                                    "group_group_id": group_id})
                target_sdk.delete_group_from_group(group_id=matched_group.id,
                                                   deleting_group_id=group_id)
                logger.info("Deployment Complete",
                            extra={"group_name": group.name,
                                   "group_group_id": group_id})


def main(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)

    source_sdk = get_client(args.ini, args.source)

    for t in args.target:
        target_sdk = get_client(args.ini, t)
        write_groups_in_group(source_sdk, target_sdk, args.pattern)
