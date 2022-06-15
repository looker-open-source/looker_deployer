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

from setuptools import setup
from looker_deployer import version as pkg

NAME = "looker_deployer"
VERSION = pkg.__version__
REQUIRES = ["looker-sdk>=21.18.0", "oyaml", "python-json-logger"]

setup(
    author="Looker Open Source",
    author_email="looker-open-source@google.com",
    description="A Looker Deployment Tool",
    install_requires=REQUIRES,
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    keywords=["Looker Deployer"],
    license="Apache License 2.0",
    name=NAME,
    packages=["looker_deployer", "looker_deployer/commands", "looker_deployer/utils"],
    entry_points={"console_scripts": ["ldeploy=looker_deployer.cli:main"]},
    python_requires=">=3.6.0, <=3.9.13",
    version=VERSION
)
