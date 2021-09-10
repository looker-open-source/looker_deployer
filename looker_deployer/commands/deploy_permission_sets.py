import logging
import re
from looker_sdk import models, error
import looker_sdk
from looker_deployer.utils import deploy_logging
from looker_deployer.utils import parse_ini
from looker_deployer.utils.get_client import get_client
# from looker_deployer.utils import match_by_key

logger = deploy_logging.get_logger(__name__)

def match_by_key(tuple_to_search,dictionary_to_match,key_to_match_on):
  matched = None
  
  for item in tuple_to_search:
    if getattr(item,key_to_match_on) == getattr(dictionary_to_match,key_to_match_on): 
      matched = item
      break
  
  return matched

def get_filtered_permission_sets(source_sdk, pattern=None):
  permission_sets = source_sdk.all_permission_sets()

  logger.debug(
    "Permission Sets pulled",
    extra={
      "permission_sets_names": [i.name for i in permission_sets]
    }
  )

  for permission_set in permission_sets:
    if permission_set.built_in:
      permission_sets.remove(permission_set)

  if pattern:
    compiled_pattern = re.compile(pattern)
    permission_sets = [i for i in permission_sets if compiled_pattern.search(i.name)]
    logger.debug(
      "Permission Sets filtered",
      extra={
        "filtered_permission_sets": [i.name for i in permission_sets],
        "pattern": pattern
      }
    )
  
  return permission_sets

def get_user_attribute_group_value(source_sdk,user_attribute):
  user_attribute_group_value = source_sdk.all_user_attribute_group_values(user_attribute.id)

  logger.debug(
    "User Attribute Group Value Pulled",
    extra ={
      "group_ids": [i.group_id for i in user_attribute_group_value]
    }
  )
  
  return user_attribute_group_value

def send_permission_sets(source_sdk,target_sdk,pattern):
  
  #INFO: Get All User Attirbutes From Source Instance
  permission_sets = get_filtered_permission_sets(source_sdk,pattern)
  target_permission_sets = get_filtered_permission_sets(target_sdk,pattern)

  #INFO: Start Loop of Create/Update on Target
  for permission_set in permission_sets:
    #INFO: Create user attribute
    new_permission_set = models.WritePermissionSet()
    new_permission_set.__dict__.update(permission_set.__dict__)
    
    #INFO: Test if user attribute is already in target
    matched_permission_set = match_by_key(target_permission_sets,permission_set,"name")
    
    if matched_permission_set:
      permission_set_exists = True
    else:
      permission_set_exists = False

    #INFO: Create or Update the User Attribute
    if not permission_set_exists:
      logger.debug("No Permission Set found. Creating...")
      logger.debug("Deploying Permission Set", extra={"permission_set": permission_set.name})
      matched_permission_set = target_sdk.create_permission_set(body=new_permission_set)
      logger.info("Deployment complete", extra={"permission_set": new_permission_set.name})
    else:
      logger.debug("Existing permission set found. Updating...")
      logger.debug("Deploying Permission Set", extra={"permission_set": new_permission_set.name})
      matched_permission_set = target_sdk.update_permission_set(matched_permission_set.id, new_permission_set)
      logger.info("Deployment complete", extra={"permission_set": new_permission_set.name})

def main(args):

  if args.debug:
    logger.setLevel(logging.DEBUG)
  
  source_sdk = get_client(args.ini, args.source)

  for t in args.target:
    target_sdk = get_client(args.ini, t)
    send_permission_sets(source_sdk,target_sdk,args.pattern)