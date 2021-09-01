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

def get_filtered_roles(source_sdk, pattern=None):
  roles = source_sdk.all_roles()

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

def get_user_attribute_group_value(source_sdk,user_attribute):
  user_attribute_group_value = source_sdk.all_user_attribute_group_values(user_attribute.id)

  logger.debug(
    "User Attribute Group Value Pulled",
    extra ={
      "group_ids": [i.group_id for i in user_attribute_group_value]
    }
  )
  
  return user_attribute_group_value

def send_roles(source_sdk,target_sdk,pattern):
  
  #INFO: Get all roles from source and target instances that match pattern for name
  roles = get_filtered_roles(source_sdk,pattern)
  target_roles = get_filtered_roles(target_sdk,pattern)

  #INFO: Get all permission sets and models from target instances
  #source_permission_sets = source_sdk.all_permission_sets()
  #source_model_sets = source_sdk.all_model_sets()
  target_permission_sets = target_sdk.all_permission_sets()
  target_model_sets = target_sdk.all_model_sets()

  #INFO: Start Loop of Create/Update on Target
  for role in roles:
    #INFO: Create Role
    new_role = models.WriteRole()
    new_role.__dict__.update(role.__dict__)
    
    #INFO: For the role being created or updated, need to swap the permission set and model set ids
    matched_permission_set = match_by_key(target_permission_sets,role.permission_set,"name")
    matched_model_set = match_by_key(target_model_sets,role.model_set,"name")
    new_role.permission_set_id = matched_permission_set.id
    new_role.model_set_id = matched_model_set.id

    #INFO: Test if role is already in target
    matched_role = match_by_key(target_roles,role,"name")
    
    if matched_role:
      role_exists = True
    else:
      role_exists = False

    #INFO: Create or Update the User Attribute
    if not role_exists:
      logger.debug("No Role found. Creating...")
      logger.debug("Deploying Role", extra={"role": role.name})
      matched_role = target_sdk.create_role(body=new_role)
      logger.info("Deployment complete", extra={"role": new_role.name})
    else:
      logger.debug("Existing Role found. Updating...")
      logger.debug("Deploying Role", extra={"role": new_role.name})
      matched_role = target_sdk.update_role(matched_role.id, new_role)
      logger.info("Deployment complete", extra={"role": new_role.name})

def main():
  ini =  '/Users/adamminton/Documents/credentials/looker.ini'
  source_sdk = looker_sdk.init31(ini,section='version218')
  target_sdk = looker_sdk.init31(ini,section='version2110')
  pattern = '^testing_'
  #pattern = None
  debug = True

  if debug:
    logger.setLevel(logging.DEBUG)

  send_roles(source_sdk,target_sdk,pattern)

main()