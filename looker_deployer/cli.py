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

import argparse
from looker_deployer.commands import deploy_boards, deploy_code, deploy_connections
from looker_deployer.commands import deploy_content, deploy_content_export
from looker_deployer.commands import deploy_permission_sets, deploy_model_sets, deploy_roles, deploy_groups, deploy_group_in_group, deploy_role_to_group, deploy_user_attributes
from looker_deployer import version as pkg

loc = "looker.ini"


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--version", action="store_true", help="print version and exit"),
    subparsers = parser.add_subparsers()
    setup_board_subparser(subparsers)
    setup_code_subparser(subparsers)
    setup_connections_subparser(subparsers)
    setup_content_subparser(subparsers)
    setup_permission_sets_subparser(subparsers)
    setup_model_sets_subparser(subparsers)
    setup_roles_subparser(subparsers)
    setup_groups_subparser(subparsers)
    setup_group_in_group_subparser(subparsers)
    setup_role_to_group_subparser(subparsers)
    setup_user_attributes_subparser(subparsers)
    args = parser.parse_args()
    if args.version:
        print(pkg.__version__)
        parser.exit(0)
    else:
        try:
            args.func(args)
        except AttributeError:
            parser.print_help()
            parser.exit(1)


def setup_board_subparser(subparsers):
    boards_subparser = subparsers.add_parser("boards")
    boards_subparser.add_argument("--source", required=True, help="which environment to source the board from")
    boards_subparser.add_argument("--target", required=True, nargs="+", help="which target environment(s) to deploy to")
    boards_subparser.add_argument("--board", required=True, help="which board to deploy")
    boards_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    boards_subparser.add_argument(
        "--allow-partial",
        action="store_true",
        help="allow partial deployment of board content if not all content is present on target instance?"
    )
    boards_subparser.add_argument(
        "--title-change",
        help="if updating title, the old title to replace in target environments"
    )

    boards_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    boards_subparser.set_defaults(func=deploy_boards.main)


def setup_code_subparser(subparsers):
    code_subparser = subparsers.add_parser("code")
    code_subparser.add_argument("--hub", action="store_true", help="flag to deploy hub project")
    code_subparser.add_argument("--spoke", nargs='+', help="which spoke(s) to deploy")
    code_subparser.add_argument("--hub-exclude", nargs="+", help="which projects should be ignored from hub deployment")
    code_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    code_subparser.set_defaults(func=deploy_code.main)


def setup_connections_subparser(subparsers):
    connections_subparser = subparsers.add_parser("connections")
    connections_subparser.add_argument("--source", required=True, help="which environment to source the board from")
    connections_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    connections_subparser.add_argument(
        "--target",
        required=True,
        nargs="+",
        help="which target environment(s) to deploy to"
    )
    connections_subparser.add_argument("--pattern", help="regex pattern to filter which connections are deployed")
    connections_subparser.add_argument(
        "--include-password",
        action="store_true",
        help="should passwords be set from the ini file?"
    )
    connections_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    connections_subparser.set_defaults(func=deploy_connections.main)


def setup_content_subparser(subparsers):
    content_subparser = subparsers.add_parser("content")
    import_export_subparsers = content_subparser.add_subparsers()
    export_subparser = import_export_subparsers.add_parser("export")
    import_subparser = import_export_subparsers.add_parser("import")

    export_subparser.add_argument("--env", required=True, help="What environment to deploy to")
    export_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    export_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    export_subparser.add_argument("--folders", nargs="+", required=True, help="What folders to export content from")
    export_subparser.add_argument("--local-target", required=True, help="Local directory to store content")
    export_subparser.set_defaults(func=deploy_content_export.main)

    import_subparser.add_argument("--env", required=True, help="What environment to deploy to")
    import_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    import_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    import_subparser.add_argument("--recursive", action="store_true", help="Should folders deploy recursively")
    import_subparser.add_argument("--target-folder", help="override the default target folder with a custom path")
    content_group = import_subparser.add_mutually_exclusive_group(required=True)
    content_group.add_argument("--folders", nargs="+", help="Folders to fully deploy")
    content_group.add_argument("--dashboards", nargs="+", help="Dashboards to deploy")
    content_group.add_argument("--looks", nargs="+", help="Looks to deploy")
    import_subparser.set_defaults(func=deploy_content.main)


def setup_permission_sets_subparser(subparsers):
    permission_sets_subparser = subparsers.add_parser("permission_sets")
    permission_sets_subparser.add_argument("--source", required=True, help="which environment to source the permission sets from")
    permission_sets_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    permission_sets_subparser.add_argument("--target", nargs="+", required=True, help="which target environment(s) to deploy to")
    permission_sets_subparser.add_argument("--pattern", help="regex pattern to filter which permission sets are deployed")
    permission_sets_subparser.add_argument("--delete", action="store_true", help="enables the ability for explicit deletes of permission sets in target")
    permission_sets_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    permission_sets_subparser.set_defaults(func=deploy_permission_sets.main)


def setup_model_sets_subparser(subparsers):
    model_sets_subparser = subparsers.add_parser("model_sets")
    model_sets_subparser.add_argument("--source", required=True, help="which environment to source the model sets from")
    model_sets_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    model_sets_subparser.add_argument("--target", nargs="+", required=True, help="which target environment(s) to deploy to")
    model_sets_subparser.add_argument("--pattern", help="regex pattern to filter which model sets are deployed")
    model_sets_subparser.add_argument("--delete", action="store_true", help="enables the ability for explicit deletes of model sets in target")
    model_sets_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    model_sets_subparser.set_defaults(func=deploy_model_sets.main)


def setup_roles_subparser(subparsers):
    roles_subparser = subparsers.add_parser("roles")
    roles_subparser.add_argument("--source", required=True, help="which environment to source the roles from")
    roles_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    roles_subparser.add_argument("--target", nargs="+", required=True, help="which target environment(s) to deploy to")
    roles_subparser.add_argument("--pattern", help="regex pattern to filter which roles are deployed")
    roles_subparser.add_argument("--delete", action="store_true", help="enables the ability for explicit deletes of roles in target")
    roles_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    roles_subparser.set_defaults(func=deploy_roles.main)


def setup_groups_subparser(subparsers):
    groups_subparser = subparsers.add_parser("groups")
    groups_subparser.add_argument("--source", required=True, help="which environment to source the groups from")
    groups_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    groups_subparser.add_argument("--target", nargs="+", required=True, help="which target environment(s) to deploy to")
    groups_subparser.add_argument("--pattern", help="regex pattern to filter which groups are deployed")
    groups_subparser.add_argument("--delete", action="store_true", help="enables the ability for explicit deletes of groups in target")
    groups_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    groups_subparser.set_defaults(func=deploy_groups.main)


def setup_group_in_group_subparser(subparsers):
    group_in_group_subparser = subparsers.add_parser("group_in_group")
    group_in_group_subparser.add_argument("--source", required=True, help="which environment to source the group in group from")
    group_in_group_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    group_in_group_subparser.add_argument("--target", nargs="+", required=True, help="which target environment(s) to deploy to")
    group_in_group_subparser.add_argument("--pattern", help="regex pattern to filter which group in group are deployed")
    group_in_group_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    group_in_group_subparser.set_defaults(func=deploy_group_in_group.main)


def setup_role_to_group_subparser(subparsers):
    role_to_group_subparser = subparsers.add_parser("role_to_group")
    role_to_group_subparser.add_argument("--source", required=True, help="which environment to source the role to groups from")
    role_to_group_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    role_to_group_subparser.add_argument("--target", nargs="+", required=True, help="which target environment(s) to deploy to")
    role_to_group_subparser.add_argument("--pattern", help="regex pattern to filter which role to groups are deployed")
    role_to_group_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    role_to_group_subparser.set_defaults(func=deploy_role_to_group.main)


def setup_user_attributes_subparser(subparsers):
    user_attributes_subparser = subparsers.add_parser("user_attributes")
    user_attributes_subparser.add_argument("--source", required=True, help="which environment to source the user attributess from")
    user_attributes_subparser.add_argument("--ini", default=loc, help="ini file to parse for credentials")
    user_attributes_subparser.add_argument("--target", nargs="+", required=True, help="which target environment(s) to deploy to")
    user_attributes_subparser.add_argument("--pattern", help="regex pattern to filter which user attributess are deployed")
    user_attributes_subparser.add_argument("--delete", action="store_true", help="enables the ability for explicit deletes of user attributes in target")
    user_attributes_subparser.add_argument("--debug", action="store_true", help="set logger to debug for more verbosity")
    user_attributes_subparser.set_defaults(func=deploy_user_attributes.main)
