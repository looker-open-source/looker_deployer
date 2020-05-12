from setuptools import setup
from looker_deployer import __version__ as pkg

NAME = "looker_deployer"
VERSION = pkg.__version__
REQUIRES = ["looker-sdk==0.1.3b7", "oyaml", "python-json-logger"]

setup(
    author="Colin Pistell",
    author_email="colin.pistell@looker.com",
    description="A Looker Deployment Tool",
    install_requires=REQUIRES,
    name=NAME,
    packages=["looker_deployer", "looker_deployer/commands", "looker_deployer/utils"],
    entry_points={"console_scripts": ["looker_deployer=looker_deployer.cli:main"]},
    python_requires=">=3.7.0, <3.8",
    version=VERSION
)
