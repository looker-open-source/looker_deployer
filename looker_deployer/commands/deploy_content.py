# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import subprocess
import logging
import tempfile
import shutil
import threading
import json
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
from looker_deployer.utils import deploy_logging
from looker_deployer.utils import parse_ini
from looker_deployer.utils.get_client import get_client
from looker_sdk import models40 as models


logger = deploy_logging.get_logger(__name__)

def alert_cleanup(sdk):
    logger.debug("cleaning up orphaned alerts")
    disabled_alerts = sdk.search_alerts(disabled="true")
    for alert in disabled_alerts:
        if alert['disabled_reason'] == "Dashboard element has been removed.":
            sdk.delete_alert(alert['id'])
            logger.info("Alert removed", extra={"alert title": alert['custom_title'], "owner": alert['owner_display_name']})


def get_space_ids_from_name(space_name, parent_id, sdk):
    if (space_name == "Shared" and parent_id == "0"):
        return ["1"]
    elif (space_name == "Embed Groups" and parent_id == "0"):
        return sdk.search_folders(name=space_name, parent_id=None)[0].id
    elif (space_name == "Users" and parent_id == "0"):
        return sdk.search_folders(name=space_name, parent_id=None)[0].id
    elif (space_name == "Embed Users" and parent_id == "0"):
        return sdk.search_folders(name=space_name, parent_id=None)[0].id
    logger.debug("space info", extra={"space_name": space_name, "parent_id": parent_id})
    space_list = sdk.search_folders(name=space_name, parent_id=parent_id)
    id_list = [i.id for i in space_list]

    return id_list


def create_or_return_space(space_name, parent_id, sdk):

    try:
        target_id = get_space_ids_from_name(space_name, parent_id, sdk)
        if len(target_id) == 0 and "/" in space_name:
            # If the folder name contains slashes then also check if it was previously imported with
            # the slashes replaced with division slashes (Unicode character 2215) prior to PR #153.
            target_id = get_space_ids_from_name(space_name.replace("/", "\u2215"), parent_id, sdk)
        logger.debug("Space ID from name", extra={"id": target_id})
        assert len(target_id) == 1
    except AssertionError as e:
        if len(target_id) > 1:
            logger.error("More than one Space found with that parent/name", extra={"space_ids": target_id})
            raise e
        elif (parent_id == '2' and len(target_id) == 0):
            logger.warning("Cannot create folder in Users.  Add the User first, then import their content", extra={"folder": space_name, "target_id": len(target_id)})
            raise e
        else:
            logger.warning("No folders found. Creating folder now")
            new_space = models.CreateFolder(name=space_name, parent_id=parent_id)
            res = sdk.create_folder(new_space)
            return res.id

    logger.info("Found Space ID", extra={"id": target_id})
    return target_id[0]


def get_gzr_creds(ini, env):
    ini = parse_ini.read_ini(ini)
    env_record = ini[env]
    host, port = env_record["base_url"].replace("https://", "").split(":")
    client_id = env_record["client_id"]
    client_secret = env_record["client_secret"]
    verify_ssl = env_record["verify_ssl"]

    return (host, port, client_id, client_secret, verify_ssl)


def import_content(content_type, content_json, space_id, env, ini, debug=False):
    assert content_type in ["dashboard", "look"], "Unsupported Content Type"
    host, port, client_id, client_secret, verify_ssl = get_gzr_creds(ini, env)

    logger.info(
        "Deploying content",
        extra={
            "content_type": content_type,
            "source_file": content_json,
            "folder_id": space_id,
            "host": host,
            "port": port,
            "verify_ssl": verify_ssl,
            "active_thread": threading.get_ident()
        }
    )

    gzr_command = [
        "gzr",
        content_type,
        "import",
        content_json,
        space_id,
        "--host",
        host,
        "--port",
        port,
        "--client-id",
        client_id,
        "--client-secret",
        client_secret,
        "--force"
    ]

    # config parser returns a string - easier to parse that than convert to a bool
    if verify_ssl == "False":
        gzr_command.append("--no-verify-ssl")
    if debug:
        gzr_command.append("--debug")

    # if we're running on windows we need to appropriately call the command-line arg"
    if os.name == "nt":
        win_exec = ["cmd.exe", "/c"]
        gzr_command = win_exec + gzr_command

    is_new_dash = "false"
    existing_dash_alerts = []
    existing_elements_w_alerts = []

    if content_type == "dashboard":  ## only run for dashboards, looks can't have alerts
        sdk = get_client(ini, env)  ## should we update the function def and pass sdk?
        with open(content_json) as file:
            json_dash = json.load(file)
        existing_dash = sdk.search_dashboards(slug=json_dash['slug'])  ## search with slug first, fall back to name + folder
        if len(existing_dash) < 1:
            existing_dash = sdk.search_dashboards(title=json_dash['title'],folder_id=space_id)
            if len(existing_dash) < 1:
                is_new_dash = "true"
        if is_new_dash == "false": ## if it's an existing dashboard, save the alerts and elements
            for element in existing_dash[0]['dashboard_elements']:
                start = len(existing_dash_alerts)
                alerts = list(filter(lambda alert: str(alert['dashboard_element_id']) == str(element['id']), enabled_alerts))
                if len(alerts) > 0:
                    existing_dash_alerts.extend(alerts)
                if len(existing_dash_alerts) > start:
                    if element not in existing_elements_w_alerts:
                        existing_elements_w_alerts.append(element)


    #logger.debug("space info", extra={"space_name": space_name, "parent_id": parent_id})
    update_fields = {}
    update_fields['owner_id'] = sdk.me()['id'] #get id of current user
    update_fields['is_disabled'] = "true"
    update_fields['disabled_reason'] = "dashboard update"
    if len(existing_dash_alerts) > 0:
        for alert in existing_dash_alerts:
            if alert['id'] != update_fields['owner_id']:
                sdk.update_alert_field(alert['id'], update_fields) #update old alert to current user to prevent errors when deleting

    subprocess.run(gzr_command)

    
    if is_new_dash == "false" and content_type == "dashboard" and len(existing_dash_alerts) > 0:  ## get the new dashboard
        updated_dash = sdk.search_dashboards(slug=json_dash['slug'])
        if len(updated_dash) < 1:
            updated_dash = sdk.search_dashboards(title=json_dash['title'],folder_id=space_id)
        old_to_new_ids = {}
        for element in existing_elements_w_alerts:  ## match old element ids to new element ids
            updated_dash_element = list(filter(lambda item: item['title'] == element['title'] and item['query_id'] == element['query_id'], updated_dash[0]['dashboard_elements']))
            if len(updated_dash_element) == 1:  ## what should we do if more than one match?
                old_to_new_ids[element['id']] = updated_dash_element[0]['id']
        for alert in existing_dash_alerts:  ## create new alerts
            logger.debug('processing alert for element', extra={"element_id": alert['dashboard_element_id']})
            new_alert = {}
            update_owner = {} #alerts are assigned to creator, need to update after
            update_owner['owner_id'] = alert['owner_id']
            for key in alert.keys():
                new_alert[key] = alert[key]
            new_alert['applied_dashboard_filters'] = []
            new_filter = {}
            for old_filter in alert['applied_dashboard_filters']:
                new_filter = old_filter.__dict__
                if new_filter['filter_value'] == 'None':
                    new_filter['filter_value'] = ""
                new_alert['applied_dashboard_filters'].append(new_filter)
            if alert['dashboard_element_id'] in old_to_new_ids.keys():
                logger.debug("creating alert", extra={"old_element_id": alert['dashboard_element_id'], "new_element_id": old_to_new_ids[alert['dashboard_element_id']]})
                new_alert['dashboard_element_id'] = old_to_new_ids[alert['dashboard_element_id']]
                try:
                    created_alert = sdk.create_alert(new_alert)
                    sdk.update_alert_field(created_alert['id'], update_owner) #update new alert to correct owner
                    sdk.delete_alert(alert['id'])
                except Exception as e:
                    print(e)
        

def build_spaces(spaces, sdk):
    # seeding initial value of parent id to Shared
    # We use a list to aid in debugging should values not drain properly"
    id_tracker = ["0"]

    for space in spaces:
        # Gazer replaces slashes in folder names with division slashes (Unicode character 2215), so undo that.
        space = space.replace("\u2215", "/")

        logger.debug("parent_id to use", extra={"id_tracker": id_tracker})
        # Pull last value from id_tracker
        space_parent = id_tracker.pop()

        logger.debug("data for folder creation", extra={"folder": space, "folder_parent": space_parent})
        space_id = create_or_return_space(space, space_parent, sdk)

        # Add new id to id_tracker
        id_tracker.append(space_id)
        logger.debug("parent_id_tracker updated", extra={"parent_id_tracker": id_tracker})

    # We need the final value of the id_tracker so we know what id to deploy content to
    return id_tracker[0]


def deploy_space(s, sdk, env, ini, recursive, target_base, debug=False):

    logger.debug("working folder", extra={"working_folder": s})

    # grab the relevant files for deployment
    space_files = [f for f in os.listdir(s) if os.path.isfile(os.path.join(s, f))]
    space_children = [os.path.join(s, d) + os.sep for d in os.listdir(s) if os.path.isdir(os.path.join(s, d))]
    look_files = [os.path.join(s, i) for i in space_files if re.search("^Look", i)]
    dash_files = [os.path.join(s, i) for i in space_files if re.search("^Dashboard", i)]
    logger.debug("files to process", extra={"looks": look_files, "dashboards": dash_files})

    # cut down directory to looker-specific paths
    a, b, c = s.partition(target_base)
    c = c.rpartition(os.sep)[0]
    logger.debug("partition components", extra={"a": a, "b": b, "c": c})

    # turn into a list of spaces to process
    spaces_to_process = "".join([b, c]).split(os.sep)
    logger.debug("folders to process", extra={"folders": spaces_to_process})

    # The final value of id_tracker in build_spaces must be the targeted space id
    space_id = build_spaces(spaces_to_process, sdk)
    logger.debug("target folder id", extra={"folder_id": space_id})

    # deploy looks
    logger.debug("running looks", extra={"looks": look_files})
    with ThreadPoolExecutor(max_workers=3) as pool:
        pool.map(
            import_content,
            repeat("look"),
            look_files,
            repeat(space_id),
            repeat(env),
            repeat(ini),
            repeat(debug)
        )
    # deploy dashboards
    logger.debug("running dashboards", extra={"dashboards": dash_files})
    with ThreadPoolExecutor(max_workers=3) as pool:
        pool.map(
            import_content,
            repeat("dashboard"),
            dash_files,
            repeat(space_id),
            repeat(env),
            repeat(ini),
            repeat(debug)
        )

    # go for recursion
    if recursive and space_children:
        logger.info("Attemting Recursion of children folders", extra={"children_folders": space_children})
        for child in space_children:
            deploy_space(child, sdk, env, ini, recursive, target_base, debug)
    else:
        logger.info("No Recursion specified or empty child list", extra={"children_folders": space_children})


def deploy_content(content_type, content, sdk, env, ini, target_base, debug=False):
    # extract directory path
    dirs = content.rpartition(os.sep)[0] + os.sep

    # cut down directory to looker-specific paths
    a, b, c = dirs.partition(target_base)
    c = c.rpartition(os.sep)[0]  # strip trailing slash

    # turn into a list of spaces to process
    spaces_to_process = "".join([b, c]).split(os.sep)

    # The final value of id_tracker in build_spaces must be the targeted space id
    space_id = build_spaces(spaces_to_process, sdk)

    import_content(content_type, content, space_id, env, ini, debug)


def send_content(
    sdk, env, ini, target_folder=None, spaces=None, dashboards=None, looks=None, recursive=False, debug=False, target_base=None
):

    if spaces:
        logger.debug("Deploying folders", extra={"folders": spaces})
        # Loop through spaces
        for s in spaces:
            logger.debug("working folder", extra={"working_folder": s})
            # Check for a target space override
            if target_folder:
                logger.info("target folder override found", extra={"target_folder": target_folder})
                # In order for recursion to continue to work properly, the actual directory needs to be updated
                # Create a temporary directory to contain updated space. Context block will auto-clean when done
                with tempfile.TemporaryDirectory() as d:
                    updated_space = os.path.join(d, target_folder)
                    # copy the source space directory tree to target space override
                    shutil.copytree(s, updated_space)
                    # kick off the job from the new space
                    deploy_space(updated_space, sdk, env, ini, recursive, target_base, debug)
            # If no target space override, kick off job normally
            else:
                deploy_space(s, sdk, env, ini, recursive, target_base, debug)
    if dashboards:
        logger.debug("Deploying dashboards", extra={"dashboards": dashboards})
        for dash in dashboards:
            logger.debug("working dashboard", extra={"dashboard": dash})
            # Check for target space override
            if target_folder:
                logger.info("target folder override found", extra={"target_folder": target_folder})
                # In order for recursion to continue to work properly, the actual directory needs to be updated
                # Create a temporary directory to contain updated space. Context block will auto-clean when done
                with tempfile.TemporaryDirectory() as d:
                    # copy the dashboard file to target space override
                    target_dir = os.path.join(d, target_folder)
                    os.makedirs(target_dir)
                    shutil.copy(dash, target_dir)
                    new_dash_path = [os.path.join(target_dir, f) for f in os.listdir(target_dir)][0]
                    # kick off the job from the new space
                    deploy_content("dashboard", new_dash_path, sdk, env, ini, target_base, debug)
            else:
                deploy_content("dashboard", dash, sdk, env, ini, target_base, debug)
    if looks:
        logger.debug("Deploying looks", extra={"looks": looks})
        for look in looks:
            logger.debug("working look", extra={"look": look})
            # Check for target space override
            if target_folder:
                logger.info("target folder override found", extra={"target_folder": target_folder})
                # In order for recursion to continue to work properly, the actual directory needs to be updated
                # Create a temporary directory to contain updated space. Context block will auto-clean when done
                with tempfile.TemporaryDirectory() as d:
                    # copy the look file to target space override
                    target_dir = os.path.join(d, target_folder)
                    os.makedirs(target_dir)
                    shutil.copy(look, target_dir)
                    new_look_path = [os.path.join(target_dir, f) for f in os.listdir(target_dir)][0]
                    # kick off the job from the new space
                    deploy_content("look", new_look_path, sdk, env, ini, target_base, debug)
            else:
                deploy_content("look", look, sdk, env, ini, target_base, debug)


def main(args):

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("ini file", extra={"ini": args.ini})

    if args.target_folder:
        # Make sure trailing sep is in place
        if not args.target_folder.endswith(os.sep):
            args.target_folder += os.sep
        args.target_base = args.target_folder.split('/')[0]
    else:
        args.target_base = 'Shared'

    sdk = get_client(args.ini, args.env)
    global enabled_alerts
    enabled_alerts = sdk.search_alerts(disabled="false", all_owners=True)
    send_content(
        sdk,
        args.env,
        args.ini,
        args.target_folder,
        args.folders,
        args.dashboards,
        args.looks,
        args.recursive,
        args.debug,
        args.target_base
    )

    alert_cleanup(sdk)

