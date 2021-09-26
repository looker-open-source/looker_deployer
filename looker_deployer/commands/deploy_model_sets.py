import logging
import re
from looker_sdk import models, error
import looker_sdk
from looker_deployer.utils import deploy_logging
from looker_deployer.utils import parse_ini
from looker_deployer.utils.get_client import get_client
from looker_deployer.utils import match_by_key

logger = deploy_logging.get_logger(__name__)

def get_filtered_model_sets(source_sdk, pattern=None):
  model_sets = source_sdk.all_model_sets()

  logger.debug(
    "Model Sets pulled",
    extra={
      "model_sets_names": [i.name for i in model_sets]
    }
  )

  for model_set in model_sets:
    if model_set.built_in:
      model_sets.remove(model_set)

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

def get_user_attribute_group_value(source_sdk,user_attribute):
  user_attribute_group_value = source_sdk.all_user_attribute_group_values(user_attribute.id)

  logger.debug(
    "User Attribute Group Value Pulled",
    extra ={
      "group_ids": [i.group_id for i in user_attribute_group_value]
    }
  )
  
  return user_attribute_group_value

def write_model_sets(model_sets,target_sdk,pattern=None):
  
  #INFO: Get filtered model sets from target Instance
  target_model_sets = get_filtered_model_sets(target_sdk,pattern)

  #INFO: Start Loop of Create/Update on Target
  for model_set in model_sets:
    #INFO: Create model set
    new_model_set = models.WriteModelSet()
    new_model_set.__dict__.update(model_set.__dict__)
    
    #INFO: Test if model set is already in target
    matched_model_set = match_by_key(target_model_sets,model_set,"name")
    
    if matched_model_set:
      model_set_exists = True
    else:
      model_set_exists = False

    #INFO: Create or Update the Model Set
    if not model_set_exists:
      logger.debug("No Model Set found. Creating...")
      logger.debug("Deploying Model Set", extra={"model_set": model_set.name})
      matched_model_set = target_sdk.create_model_set(new_model_set)
      logger.info("Deployment complete", extra={"model_set": new_model_set.name})
    else:
      logger.debug("Existing model set found. Updating...")
      logger.debug("Deploying Model Set", extra={"model_set": new_model_set.name})
      matched_model_set = target_sdk.update_model_set(matched_model_set.id, new_model_set)
      logger.info("Deployment complete", extra={"model_set": new_model_set.name})

def send_model_sets(source_sdk,target_sdk,pattern=None):
  model_sets = get_filtered_model_sets(source_sdk,pattern)
  write_model_sets(model_sets,target_sdk,pattern)

def main(args):
  if args.debug:
    logger.setLevel(logging.DEBUG)
  
  source_sdk = get_client(args.ini, args.source)

  for t in args.target:
    target_sdk = get_client(args.ini, t)
    send_model_sets(source_sdk,target_sdk,args.pattern)
