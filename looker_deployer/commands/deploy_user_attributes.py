import logging
import re
from looker_sdk import models, error
import looker_sdk
from looker_sdk.sdk.api31.models import UserAttribute
from looker_deployer.utils import deploy_logging
from looker_deployer.utils import parse_ini
from looker_deployer.utils.get_client import get_client

logger = deploy_logging.get_logger(__name__)

def get_filtered_user_attributes(source_sdk, pattern=None):
  user_attributes = source_sdk.all_user_attributes()

  logger.debug(
    "User Attributes pulled",
    extra={
      "user_attribute_names": [i.name for i in user_attributes]
    }
  )

  for user_attribute in user_attributes:
    if user_attribute.is_system:
      user_attributes.remove(user_attribute)

  if pattern:
    compiled_pattern = re.compile(pattern)
    user_attributes = [i for i in user_attributes if compiled_pattern.search(i.name)]
    logger.debug(
      "User Attributes filtered",
      extra={
        "filtered_user_attributes": [i.name for i in user_attributes],
        "pattern": pattern
      }
    )
  
  return user_attributes

def get_user_attribute_group_value(source_sdk,user_attribute):
  user_attribute_group_value = source_sdk.all_user_attribute_group_values(user_attribute.id)

  logger.debug(
    "User Attribute Group Value Pulled",
    extra ={
      "group_ids": [i.group_id for i in user_attribute_group_value]
    }
  )
  
  return user_attribute_group_value

def match_user_attributes(source_user_attribute,target_user_attributes):
  matched_user_attribute = None
  
  for target_user_attribute in target_user_attributes:
    if source_user_attribute.name == target_user_attribute.name:
      matched_user_attribute = target_user_attribute
  
  return matched_user_attribute


def send_user_attributes(source_sdk,target_sdk,pattern):
  
  #INFO: Get All User Attirbutes From Source Instance
  user_attributes = get_filtered_user_attributes(source_sdk,pattern)
  target_user_attributes = get_filtered_user_attributes(target_sdk,pattern)
  print(user_attributes)

  #INFO: Start Loop of Create/Update User Attribute on Target and Update Group Values if set
  for user_attribute in user_attributes:
    #INFO: Create user attribute
    new_user_attribute = models.WriteUserAttribute()
    new_user_attribute.__dict__.update(user_attribute.__dict__)
    
    #INFO: Test if user attribute is already in target
    matched_user_attribute = match_user_attributes(user_attribute,target_user_attributes)
    if matched_user_attribute:
      user_attribute_exists = True
    else:
      user_attribute_exists = False

    #INFO: Create or Update the User Attribute
    if not user_attribute_exists:
      logger.debug("No User Attribute found. Creating...")
      logger.debug("Deploying User Attribute", extra={"user_attribute": new_user_attribute.name})
      matched_user_attribute = target_sdk.create_user_attribute(body=new_user_attribute)
      logger.info("Deployment complete", extra={"user_attribute": new_user_attribute.name})
    else:
      logger.debug("Existing user attribute found. Updating...")
      logger.debug("Deploying User Attribute", extra={"user_attribute": new_user_attribute.name})
      matched_user_attribute = target_sdk.update_user_attribute(matched_user_attribute.id, new_user_attribute)
      logger.info("Deployment complete", extra={"user_attribute": new_user_attribute.name})
    #INFO: Set group values for user attribute
    #INFO: Need to test if overwrite not
    #BUG: Will probably need to reject group ids that are not in the target to ensure it doesn't fail
    user_attribute_group_value = get_user_attribute_group_value(source_sdk,user_attribute)
    target_sdk.set_user_attribute_group_values(matched_user_attribute.id,user_attribute_group_value)

def main():
  ini =  '/Users/adamminton/Documents/credentials/looker.ini'
  source_sdk = looker_sdk.init31(ini,section='version218')
  target_sdk = looker_sdk.init31(ini,section='version2110')
  pattern = '^testingme'
  debug = True

  if debug:
    logger.setLevel(logging.DEBUG)

  send_user_attributes(source_sdk,target_sdk,pattern)

main()