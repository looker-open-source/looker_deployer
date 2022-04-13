import logging
import re
from looker_sdk import models
from looker_deployer.utils import deploy_logging
from looker_deployer.utils.get_client import get_client
from looker_deployer.utils.match_by_key import match_by_key

logger = deploy_logging.get_logger(__name__)


def get_filtered_model_sets(source_sdk, pattern=None):
    model_sets = source_sdk.all_model_sets()

    logger.debug(
        "Model Sets pulled",
        extra={
            "model_sets_names": [i.name for i in model_sets]
        }
    )

    model_sets = [i for i in model_sets if not i.built_in]

    if pattern:
        compiled_pattern = re.compile(pattern)
        model_sets = [i for i in model_sets if compiled_pattern.search(i.name)]
        logger.debug(
            "Model Sets filtered",
            extra={
                "filtered_model_sets": [i.name for i in model_sets],
                "pattern": pattern
            }
        )

    return model_sets


def write_model_sets(model_sets, target_sdk, pattern=None, allow_delete=None):

    # INFO: Get filtered model sets from target Instance
    target_model_sets = get_filtered_model_sets(target_sdk, pattern)

    # INFO: Start Loop of Create/Update on Target
    for model_set in model_sets:
        # INFO: Create model set
        new_model_set = models.WriteModelSet()
        new_model_set.__dict__.update(model_set.__dict__)

        # INFO: Test if model set is already in target
        matched_model_set = match_by_key(target_model_sets, model_set, "name")

        if matched_model_set:
            model_set_exists = True
        else:
            model_set_exists = False

        # INFO: Create or Update the Model Set
        if not model_set_exists:
            logger.debug("No Model Set found. Creating...")
            logger.debug("Deploying Model Set",
                         extra={"model_set": model_set.name})
            matched_model_set = target_sdk.create_model_set(new_model_set)
            logger.info("Deployment complete",
                        extra={"model_set": new_model_set.name})
        else:
            logger.debug("Existing model set found. Updating...")
            logger.debug("Deploying Model Set",
                         extra={"model_set": new_model_set.name})
            matched_model_set = target_sdk.update_model_set(
                matched_model_set.id, new_model_set)
            logger.info("Deployment complete",
                        extra={"model_set": new_model_set.name})

    # INFO: Delete missing model sets that are not in source
    if allow_delete:
        for target_model_set in target_model_sets:

            # INFO: Test if model set is already in target
            matched_model_set = match_by_key(model_sets, target_model_set,
                                             "name")

            if not matched_model_set:
                logger.debug("No Source Model Set found. Deleting...")
                logger.debug("Deleting Model Set",
                             extra={"model_set": target_model_set.name})
                target_sdk.delete_model_set(target_model_set.id)
                logger.info("Delete complete",
                            extra={"model_set": target_model_set.name})


def send_model_sets(source_sdk, target_sdk, pattern=None, allow_delete=None):
    # INFO: Get all model sets from source instance
    model_sets = get_filtered_model_sets(source_sdk, pattern)
    write_model_sets(model_sets, target_sdk, pattern, allow_delete)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    source_sdk = get_client(args.ini, args.source)

    for t in args.target:
        target_sdk = get_client(args.ini, t)
        send_model_sets(source_sdk, target_sdk, args.pattern, args.delete)
