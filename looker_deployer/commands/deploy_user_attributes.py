import logging
import re
from looker_sdk import models
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.get_client import get_client
from looker_deployer.utils.match_by_key import match_by_key

logger = deploy_logging.get_logger(__name__)


def get_filtered_user_attributes(source_sdk, pattern=None):
    user_attributes = source_sdk.all_user_attributes()

    logger.debug(
        "User Attributes pulled",
        extra={
            "user_attribute_names": [i.name for i in user_attributes]
        }
    )

    user_attributes = [i for i in user_attributes if not i.is_system]

    if pattern:
        compiled_pattern = re.compile(pattern)
        user_attributes = [i for i in user_attributes
                           if compiled_pattern.search(i.name)]

    logger.debug(
        "User Attributes filtered",
        extra={
            "filtered_user_attributes": [i.name for i in user_attributes],
            "pattern": pattern
        }
    )

    return user_attributes


def get_user_attribute_group_value(source_sdk, user_attribute):
    user_attribute_group_value = \
        source_sdk.all_user_attribute_group_values(user_attribute.id)

    logger.debug("User Attribute Group Value Pulled", extra={
        "group_ids": [i.group_id for i in user_attribute_group_value]
    })

    return user_attribute_group_value


def match_user_attributes(source_user_attribute, target_user_attributes):
    matched_user_attribute = None

    for target_user_attribute in target_user_attributes:
        if source_user_attribute.name == target_user_attribute.name:
            matched_user_attribute = target_user_attribute

    return matched_user_attribute


def add_group_name_information(source_sdk, list_to_update):
    for i, item in enumerate(list_to_update):
        item_group_name = source_sdk.group(group_id=item.group_id)
        item.name = item_group_name.name
        list_to_update[i] = item
    return list_to_update


def write_user_attributes(source_sdk, target_sdk,
                          pattern=None, allow_delete=None):

    # INFO: Get All User Attirbutes From Source Instance
    user_attributes = get_filtered_user_attributes(source_sdk, pattern)
    target_user_attributes = get_filtered_user_attributes(target_sdk, pattern)
    target_groups = target_sdk.all_groups()

    # INFO: Start Loop of Create/Update User Attribute on Target
    # and Update Group Values if set
    for user_attribute in user_attributes:
        # INFO: Create user attribute
        new_user_attribute = models.WriteUserAttribute()
        new_user_attribute.__dict__.update(user_attribute.__dict__)

        # INFO: Test if user attribute is already in target
        matched_user_attribute = match_user_attributes(user_attribute,
                                                       target_user_attributes)
        if matched_user_attribute:
            user_attribute_exists = True
        else:
            user_attribute_exists = False

        # INFO: Create or Update the User Attribute
        if not user_attribute_exists:
            logger.debug("No User Attribute found. Creating...")
            logger.debug("Deploying User Attribute",
                         extra={"user_attribute": new_user_attribute.name})
            matched_user_attribute = target_sdk.create_user_attribute(new_user_attribute)
            logger.info("Deployment complete",
                        extra={"user_attribute": new_user_attribute.name})
        else:
            logger.debug("Existing user attribute found. Updating...")
            logger.debug("Deploying User Attribute",
                         extra={"user_attribute": new_user_attribute.name})
            matched_user_attribute = target_sdk.update_user_attribute(
                matched_user_attribute.id,
                new_user_attribute)
            logger.info("Deployment complete",
                        extra={"user_attribute": new_user_attribute.name})
        # INFO: Set group values for user attribute
        user_attribute_group_values = get_user_attribute_group_value(
            source_sdk, user_attribute)
        user_attribute_group_values = add_group_name_information(
            source_sdk, user_attribute_group_values)
        # INFO: Need to loop through the group values in a user attribute to
        # determine matching group
        for i, user_attribute_group_value in enumerate(
                user_attribute_group_values):
            target_group = match_by_key(
                target_groups, user_attribute_group_value, "name")
            if target_group:
                user_attribute_group_value.group_id = target_group.id
                user_attribute_group_values[i] = user_attribute_group_value
            else:
                user_attribute_group_values.remove(user_attribute_group_value)

        if user_attribute_group_values:
            target_sdk.set_user_attribute_group_values(
                user_attribute_id=matched_user_attribute.id,
                body=user_attribute_group_values)

    # INFO: Delete missing users attirbutes that are not in source
    if allow_delete:
        for target_user_attribute in target_user_attributes:

            # INFO: Test if user attribute is already in target
            matched_user_attribute = match_by_key(
                user_attributes, target_user_attribute, "name")

            if not matched_user_attribute:
                logger.debug("No Source User Attribute found. Deleting...")
                logger.debug("Deleting User Attribute",
                             extra={"user_attribute":
                                    target_user_attribute.name})
                target_sdk.delete_user_attribute(target_user_attribute.id)
                logger.info("Delete complete",
                            extra={"user_attribute":
                                   target_user_attribute.name})


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    source_sdk = get_client(args.ini, args.source)

    for t in args.target:
        target_sdk = get_client(args.ini, t)
        write_user_attributes(source_sdk, target_sdk,
                              args.pattern, args.delete)
