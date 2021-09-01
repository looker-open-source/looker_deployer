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

def get_filtered_groups(source_sdk, pattern=None):
  groups = source_sdk.all_groups()

  logger.debug(
    "Groups pulled",
    extra={
      "groups_names": [i.name for i in groups]
    }
  )

  for group in groups:
    if group.externally_managed:
      groups.remove(group)

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

def get_user_attribute_group_value(source_sdk,user_attribute):
  user_attribute_group_value = source_sdk.all_user_attribute_group_values(user_attribute.id)

  logger.debug(
    "User Attribute Group Value Pulled",
    extra ={
      "group_ids": [i.group_id for i in user_attribute_group_value]
    }
  )
  
  return user_attribute_group_value

def send_groups(source_sdk,target_sdk,pattern):
  
  #INFO: Get all groups from source and target instances that match pattern for name
  groups = get_filtered_groups(source_sdk,pattern)
  target_groups = get_filtered_groups(target_sdk,pattern)

  #INFO: Start Loop of Create/Update on Target
  for group in groups:
    #INFO: Create Group
    new_group = models.WriteGroup()
    new_group.__dict__.update(group.__dict__)

    #INFO: Test if group is already in target
    matched_group = match_by_key(target_groups,group,"name")
    
    if matched_group:
      group_exists = True
    else:
      group_exists = False

    #INFO: Create or Update the User Attribute
    if not group_exists:
      logger.debug("No Group found. Creating...")
      logger.debug("Deploying Group", extra={"group": group.name})
      matched_group = target_sdk.create_group(body=new_group)
      logger.info("Deployment complete", extra={"group": new_group.name})
    else:
      logger.debug("Existing Group found. Updating...")
      logger.debug("Deploying Group", extra={"group": new_group.name})
      matched_group = target_sdk.update_group(matched_group.id, new_group)
      logger.info("Deployment complete", extra={"group": new_group.name})

def main():
  ini =  '/Users/adamminton/Documents/credentials/looker.ini'
  source_sdk = looker_sdk.init31(ini,section='version218')
  target_sdk = looker_sdk.init31(ini,section='version2110')
  pattern = '^testing_'
  #pattern = None
  debug = True

  if debug:
    logger.setLevel(logging.DEBUG)

  send_groups(source_sdk,target_sdk,pattern)

main()