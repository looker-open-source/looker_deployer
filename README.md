Looker Deployer
===============

![badge](https://github.com/JCPistell/looker_deployer/workflows/python_application/badge.svg)


## Intro

The two included scripts (`code_deploy.py` and `content_deploy.py`) manage deployment tasks for Looker instances that
follow a multi-stage development process utilizing hub-spoke models and a single repo per project.

An overview (click to embiggen):

![diagram](https://www.lucidchart.com/publicSegments/view/d214e83b-6d02-4dd3-a072-31760bd3b3d9/image.png)

## Installation

This project makes use of `pipenv` to manage dependencies. Follow the [installation
instructions](https://pipenv-fork.readthedocs.io/en/latest/index.html). It is recommended to use [pyenv](https://github.com/pyenv/pyenv#installation) to manage installing python versions.

Once `pipenv` has been installed, simply clone the repo and `pipenv install --ignore-pipfile`. Note that if you want to do development
work on the scripts you will probably want to invoke `pipenv install --ignore-pipfile --dev` to install testing packages.

## Looker Environment Requirements

In order for these scripts to correctly work a few assumptions/requirements are needed for your Looker environments:

>- **Webhooks:** The webhook deploy secret for each hub project across all instances must be the same
>- **Space Names:** All space names must be unique
>- **Gazer** The content deployment script makes use of [gzr](https://github.com/looker-open-source/gzr) to automate content deployment, so you will need to have that
>installed and configured properly.


## Configuration

Two configuration files are required. The first is the `code_config.yaml`. This file requires a list of instances - one
for each client production instance. This list must include the name (used to refer to that instance in the commands),
  the endpoint, and the name of that instances spoke project. In addition, the config file requires an entry for the
common hub project and can optionally include a list of names to instance names to exclude from hub deployments. An
example config file is provided

The other configuration is the `looker.ini` file which contains all the credentials. This file is included in the
.gitignore and extreme caution should be taken in safeguarding the credentials that are stored therein. This file should
include api credentials for each instance as well as webhook secrets. An dummy example is provided.

## Executing the scripts

The scripts are designed to run within the relevant `pipenv` virtual environment that was created during setup. You can
spawn a new shell with the virtualenv activated by navigating to this directory and executing `pipenv shell`. Once the
shell is up you can execute the relevant script by executing `python <script-name> <ARGS>`

Alternatively, you can simply execute `pipenv run <script-name> <ARGS>` or simply activate the relevant virtualenv
however you wish.


## Code Deployment Script

This script will deploy LookML code from the current Github master branch to the relevant production instance(s). This
is accomplished by sending a `GET` request to each instances deploy endpoint and authenticating it with the webhook
secret. The script accepts the following arguments:

```
  -h, --help            show this help message and exit
  --hub                 flag to deploy hub project
  --spoke SPOKE [SPOKE ...]
                        which spoke(s) to deploy
  --hub-exclude HUB_EXCLUDE [HUB_EXCLUDE ...]
                        which projects should be ignored from hub deployment
  --debug               set logger to debug for more verbosity
```

### Examples:

- `python deploy_code.py --hub` <- This will deploy the hub project to all production instances
- `python deploy_code.py --spoke foo` <- This will deploy the spoke project named "foo" to the relevant instance
- `python deploy_code.py --hub --spoke foo bar --hub-exclude bar --debug` <- This will deploy the hub project to all
  instances except `bar` and then deploy the spoke projects `foo` and `bar` to their respective instances

## Content Deployment Script

This script makes use of `gazer` to either pull content from your dev Looker instance to a directory structure on your
local machine or deploy content from said directory structure to a specified Looker instance. The script can work for
specific sets of Looks or Dashboards or can work on entire spaces - and will correctly create any space it doesn't find
in the target instance. The script accepts the following arguments:

```
  -h, --help            show this help message and exit
  --env ENV             What environment to deploy to
  --ini INI             ini file to parse for credentials
  --debug               set logger to debug for more verbosity
  --spaces SPACES [SPACES ...]
                        Spaces to fully deploy
  --dashboards DASHBOARDS [DASHBOARDS ...]
                        Dashboards to deploy
  --looks LOOKS [LOOKS ...]
                        Looks to deploy
  --export EXPORT       pull content from dev
```

### Examples:

- `python deploy_content.py --env Dev --export ~/foo/bar/` <- exports the Shared space and all sub-spaces to the file
  location `~/foo/bar/`
- `python deploy_content.py --env Test --spaces ~/foo/bar/Shared/Public` <- deploys every piece of content in
  `Shared/Public` to the Test instance
- `python deploy_content.py --env Prod --dashboards ~/foo/bar/Shared/Public/Dashboard_1.json
  ~/foo/bar/Shared/Restricted/Dashboard_2.json` <- deploys `Dashboard1` and `Dashboard2` to their respective spaces in
  the Prod instance

## Board Deployment Script

This script allows for the deployment of boards/homepages across instances. It attempts to resolve differences in
dashboard/look ids across instances and confirms that the content is present before building the new board. Boards are
matched by title - updating an existing board will result in the rebuilding of the relevant sections and items to
prevent issues with attempting to match via title. If needing to update a board title, make use of the `title-change`
parameter to allow the script to find the old title. The script accepts the following arguments:

```
usage: deploy_boards.py [-h] --source SOURCE --target TARGET [TARGET ...]
                        --board BOARD [--ini INI]
                        [--title-change TITLE_CHANGE] [--debug]

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

- `python deploy_board.py --source dev --target prod --board 'My Cool Board'` <- deploys the board 'My Cool Board' from
  dev to prod
- `python deploy_board.py --source dev --target prod_1 prod_2 --board 'My Updated Title Board' --title-change 'My Cool
  Board'` <- This deploys a board whose title has been changed from 'My Cool Board' to 'My Updated Title Board' from dev
  to two instances: prod_1 and prod_2

## Development

These scripts are intended as an accelerator and will require some further development to tune to your workflow. To
install the required development dependencies you can execute `pipenv install --dev`. You can then add any relevant unit
tests to the `tests/` directory. Unit tests can be run by executing `python -m pytest` from the project root.

Note that this repo is configured to run linting and unit tests via [Github Actions](https://github.com/features/actions).
By default a build will run whenever a Pull Request is opened or a push is made to Master. You can find the relevant
config in the `.github` directory in the project root.
