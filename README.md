Looker Deployer
===============

![badge](https://github.com/JCPistell/looker_deployer/workflows/python_application/badge.svg)


## Intro

Looker Deployer (aka 'ldeploy') is a command line tool to help move Looker objects across instances. This includes Content
(Looks, Dashboards, entire Spaces, etc.), Boards and Connections.

## Requirements

In order for these commands to correctly work a few assumptions/requirements are needed for your environment:

>- **Python** Looker Deployer requires Python 3.6+
>- **Gazer** The content deployment command makes use of [gzr](https://github.com/looker-open-source/gzr) to automate content deployment, so you will need to have that
>installed and configured properly. Gazer requires an up-to-date version of ruby.

### Authentication and Configuration

Looker Deployer makes use of the [Looker SDK](https://github.com/looker-open-source/sdk-codegen/tree/master/python) to
communicate with your Looker instances. A `looker.ini` file is required to provide authentication. By default the tool
looks for this file in your working directory but if it is named differently or in a different location you can make use
of the `--ini` argument to specify its location. Here's an example ini file:

```
[dev]
base_url=https://looker-dev.company.com:19999
client_id=abc
client_secret=xyz
verify_ssl=True

[prod]
base_url=https://looker-prod.company.com:19999
client_id=abc
client_secret=xyz
verify_ssl=True
```

## Installation

Looker Deployer is on PyPi! - You can install it with `pip install looker-deployer`.

### Dockerfile

This repo includes a Dockerfile that can be used to containerize Deployer. It includes all dependencies, such as Gazer.
To build, clone this repo, cd into it, and execute a `docker build` command. For example:

```
docker build -t looker_deployer .
```

There are also pre-built images available on [Dockerhub](https://hub.docker.com/r/jcpistell/looker_deployer)

As noted above, a `looker.ini` file is required for API authentication. You will have to either volume-map the ini file
when you run the container, or (recommended) build an image from this one that "burns" a relevant ini file into the
container. You could create a directory containing a Dockerfile and a looker.ini file. The Dockerfile would contain:

```
FROM jcpistell/looker_deployer:latest
COPY looker.ini /
```

Build the image and your config will be available from within the container:

```
docker build -t ldeploy .
```

## Usage

The tool is invoked with the `ldeploy` command, followed by the relevant sub-command. The available sub-commands
are: `boards`, `code`, `connections`, and `content`.

Each sub-command can be configured with its relevant arguments, which can be reviewed with the `-h` or `--help`
argument. For example:

`ldeploy content -h`

## Content Deployment

This command makes use of `gazer` to either pull content from your dev Looker instance to a directory structure on your
local machine or deploy content from said directory structure to a specified Looker instance. The command can work for
specific sets of Looks or Dashboards or can work on entire folders - and will correctly create any folder it doesn't find
in the target instance.

All content deployment tasks begin by exporting a representation of your development environment's content folder tree
to local disk. This is done with the `--export` command. This tree is then used in subsequent import commands to import
dashboards, looks, or entire folder trees to another instance.

The command accepts the following arguments:

```
usage: ldeploy content [-h] --env ENV [--ini INI] [--debug] [--recursive]
                       [--target-folder TARGET_FOLDER]
                       (--folders FOLDERS [FOLDERS ...] | --dashboards DASHBOARDS [DASHBOARDS ...] | --looks LOOKS [LOOKS ...] | --export EXPORT)

optional arguments:
  -h, --help            show this help message and exit
  --env ENV             What environment to deploy to
  --ini INI             ini file to parse for credentials
  --debug               set logger to debug for more verbosity
  --recursive           Should folders deploy recursively
  --target-folder TARGET_FOLDER
                        override the default target folder with a custom path
  --folders FOLDERS [FOLDERS ...]
                        Folders to fully deploy
  --dashboards DASHBOARDS [DASHBOARDS ...]
                        Dashboards to deploy
  --looks LOOKS [LOOKS ...]
                        Looks to deploy
  --export EXPORT       pull content from dev
```

### Examples:

- `ldeploy content --env Dev --export ~/foo/bar/` <- exports the Shared folder and all sub-folders to the
  directory location `~/foo/bar/`
- `ldeploy content --env prod --folders ~/foo/bar/Shared/Public` <- deploys every piece of content in
  `Shared/Public` to the prod instance
- `ldeploy content --env prod --folders ~/foo/bar/Shared/Public --recursive --target-folder Shared/FromDev/Public` <- deploys every piece of content in
  `Shared/Public` and all child folders to the prod instance in the `Shared/FromDev/Public` folder.
- `ldeploy content --env Prod --dashboards ~/foo/bar/Shared/Public/Dashboard_1.json
  ~/foo/bar/Shared/Restricted/Dashboard_2.json` <- deploys `Dashboard1` and `Dashboard2` to their respective folders in
  the Prod instance

## Board Deployment

This command allows for the deployment of boards/homepages across instances. It attempts to resolve differences in
dashboard/look ids across instances and confirms that the content is present before building the new board. Boards are
matched by title - updating an existing board will result in the rebuilding of the relevant sections and items to
prevent issues with attempting to match via title. If needing to update a board title, make use of the `title-change`
parameter to allow the command to find the old title. The command accepts the following arguments:

```
usage: ldeploy boards [-h] --source SOURCE --target TARGET [TARGET ...]
                      --board BOARD [--ini INI] [--title-change TITLE_CHANGE]
                      [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --source SOURCE       which environment to source the board from
  --target TARGET [TARGET ...]
                        which target environment(s) to deploy to
  --board BOARD         which board to deploy
  --ini INI             ini file to parse for credentials
  --title-change TITLE_CHANGE
                        if updating title, the old title to replace in target
                        environments
  --debug               set logger to debug for more verbosity
```

### Examples:

- `ldeploy boards --source dev --target prod --board 'My Cool Board'` <- deploys the board 'My Cool Board' from
  dev to prod
- `ldeploy boards --source dev --target prod_1 prod_2 --board 'My Updated Title Board' --title-change 'My Cool
  Board'` <- This deploys a board whose title has been changed from 'My Cool Board' to 'My Updated Title Board' from dev
  to two instances: prod_1 and prod_2


## Connections Deployment

This command allows for the migration of database connections across instances. For security purposes, Looker's API does
not transmit password credentials, so this command allows for the injection of these credentials from the `.ini` file.

The command accepts the following arguments:

```
usage: ldeploy connections [-h] --source SOURCE [--ini INI] --target TARGET
                           [TARGET ...] [--pattern PATTERN]
                           [--include-password] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --source SOURCE       which environment to source the board from
  --ini INI             ini file to parse for credentials
  --target TARGET [TARGET ...]
                        which target environment(s) to deploy to
  --pattern PATTERN     regex pattern to filter which connections are deployed
  --include-password    should passwords be set from the ini file?
  --debug               set logger to debug for more verbosity
```

### Examples:

- `ldeploy connections --source dev --target prod` <- This will deploy all connections in the dev instance to the prod
  instance. No credentials will be included and would need to be manually added from the Looker UI.
- `ldeploy connections --source dev --target prod --pattern ^bigquery --include-password` <- This will deploy all
  connections that begin with `bigquery` from dev to prod and attempt to inject passwords included in the `.ini` file.

## Code Deployment

This command will manage deployments of hub/spoke LookML code from the current Github master branch to the relevant production instance(s). This
is accomplished by sending a `GET` request to each instances deploy endpoint and authenticating it with the webhook
secret.

An overview of the relevant architecture (click to embiggen):

![diagram](https://www.lucidchart.com/publicSegments/view/d214e83b-6d02-4dd3-a072-31760bd3b3d9/image.png)

In order to use the code deployment tool, a `code_config.yaml` file is required. This file requires a list of instances - one
for each client production instance. This list must include the name (used to refer to that instance in the commands),
  the endpoint, and the name of that instances spoke project. In addition, the config file requires an entry for the
common hub project and can optionally include a list of names to instance names to exclude from hub deployments. Here's
an example config:

```
instances:
  - name: calvin
    endpoint: https://looker-dev.company.com
    spoke_project: powered_by_spoke_ck
  - name: levis
    endpoint: https://looker-dev.company.com
    spoke_project: powered_by_spoke_lv

hub_project: powered_by_hub
```

The command accepts the following arguments:

```
usage: ldeploy code [-h] [--hub] [--spoke SPOKE [SPOKE ...]]
                    [--hub-exclude HUB_EXCLUDE [HUB_EXCLUDE ...]] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --hub                 flag to deploy hub project
  --spoke SPOKE [SPOKE ...]
                        which spoke(s) to deploy
  --hub-exclude HUB_EXCLUDE [HUB_EXCLUDE ...]
                        which projects should be ignored from hub deployment
  --debug               set logger to debug for more verbosity
```

### Examples:

- `ldeploy code --hub` <- This will deploy the hub project to all production instances
- `ldeploy code --spoke foo` <- This will deploy the spoke project named "foo" to the relevant instance
- `ldeploy code --hub --spoke foo bar --hub-exclude bar --debug` <- This will deploy the hub project to all
  instances except `bar` and then deploy the spoke projects `foo` and `bar` to their respective instances

## Development

This project makes use of `pipenv` to manage dependencies. Follow the [installation
instructions](https://pipenv-fork.readthedocs.io/en/latest/index.html). It is recommended to use [pyenv](https://github.com/pyenv/pyenv#installation) to manage installing python versions.

Once `pipenv` has been installed, clone this repo, `cd` into it, and invoke `pipenv install --ignore-pipfile`
