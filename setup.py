from setuptools import setup
from looker_deployer import __version__ as pkg

NAME = "looker_deployer"
VERSION = pkg.__version__
REQUIRES = ["looker-sdk==0.1.3b14", "oyaml", "python-json-logger"]

setup(
    author="Colin Pistell",
    author_email="colin.pistell@looker.com",
    description="A Looker Deployment Tool",
    install_requires=REQUIRES,
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    keywords=["Looker Deployer"],
    license="MIT",
    name=NAME,
    packages=["looker_deployer", "looker_deployer/commands", "looker_deployer/utils"],
    entry_points={"console_scripts": ["ldeploy=looker_deployer.cli:main"]},
    python_requires=">=3.6.0, <3.9",
    version=VERSION
)
