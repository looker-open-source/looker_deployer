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
      "groups_name": [i.name for i in groups]
    }
  )

  for group in groups:
    if group.externally_managed:
      groups.remove(group)

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

def get_user_attribute_group_value(source_sdk,user_attribute):
  user_attribute_group_value = source_sdk.all_user_attribute_group_values(user_attribute.id)

  logger.debug(
    "User Attribute Groups in Group Value Pulled",
    extra ={
      "group_ids": [i.group_id for i in user_attribute_group_value]
    }
  )
  
  return user_attribute_group_value

def send_groups_in_group(source_sdk,target_sdk,pattern):
  
  #INFO: Get all groups from source and target instances that match pattern for name
  groups = get_filtered_groups(source_sdk,pattern)
  target_groups = get_filtered_groups(target_sdk,pattern=None)

  #INFO: Start Loop of Create/Update on Target
  for group in groups:
    matched_group = match_by_key(target_groups,group,"name")
    groups_in_group = source_sdk.all_group_groups(group.id)
    target_groups_in_group = target_sdk.all_group_groups(matched_group.id)

    #INFO: Need to loop through the groups in group to identify target group ID
    for i, nested_group in enumerate(groups_in_group):
      target_nested_group = match_by_key(target_groups,nested_group,"name")

      if target_nested_group:
        nested_group.id = target_nested_group.id
        groups_in_group[i] = nested_group
      else:
        groups_in_group.remove(nested_group)
    
    #INFO: If groups in groups between instances is different, we need to either delete or create
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
      except:
        in_source = False
      
      try:
        target_group_ids.index(group_id)
      except:
        in_target = False
      
      if in_source and not in_target:
        logger.debug("No Groups in Group found. Creating...")
        logger.debug("Deploying Groups in Group", extra={"group_name": group.name,"group_group_id":group_id})
        target_sdk.add_group_group(group_id=matched_group.id,body=models.GroupIdForGroupInclusion(group_id=group_id))
        logger.debug("Deployment Complete", extra={"group_name": group.name,"group_group_id":group_id})
        
      elif not in_source and in_target:
        logger.debug("Extra Groups in Group found. Deleting...")
        logger.debug("Removing Groups in Group", extra={"group_name": group.name,"group_group_id":group_id})
        target_sdk.delete_group_from_group(group_id=matched_group.id,deleting_group_id=group_id)
        logger.debug("Deployment Complete", extra={"group_name": group.name,"group_group_id":group_id})


def main():
  ini =  '/Users/adamminton/Documents/credentials/looker.ini'
  source_sdk = looker_sdk.init31(ini,section='version218')
  target_sdk = looker_sdk.init31(ini,section='version2110')
  pattern = '^testing_'
  #pattern = None
  debug = True

  if debug:
    logger.setLevel(logging.DEBUG)

  send_groups_in_group(source_sdk,target_sdk,pattern)

main()