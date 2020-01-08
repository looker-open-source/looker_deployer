Looker Deployer
===============

![badge](https://github.com/JCPistell/looker_deployer/workflows/python_application/badge.svg)


## Intro

The two included scripts (`code_deploy.py` and `content_deploy.py`) manage deployment tasks for Looker instances that
follow a multi-stage development process utilizing hub-spoke models and a single repo per project.

An overview (click to embiggen)

![diagram](https://www.lucidchart.com/publicSegments/view/d214e83b-6d02-4dd3-a072-31760bd3b3d9/image.png)

## Installation

This project makes use of `pipenv` to manage dependencies. Follow the [installation
instructions](https://pipenv-fork.readthedocs.io/en/latest/index.html). It is recommended to use
[pyenv](https://github.com/pyenv/pyenv#installation) to manage installing python versions.

Once `pipenv` has been installed, simply clone the repo and `pipenv install`. Note that if you want to do development
work on the scripts you will probably want to invoke `pipenv install --dev` to install testing packages.

## Looker Environment Requirements

In order for these scripts to correctly work a few assumptions/requirements are needed for your Looker environments:

>**Webhooks:** The webhook deploy secret for each hub project across all instances must be the same
>**Space Names:** All space names must be unique
