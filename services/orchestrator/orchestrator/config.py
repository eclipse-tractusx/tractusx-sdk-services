"""Application environment configuration
"""

import os

from dotenv import find_dotenv, load_dotenv


def find_env_file() -> str:
    """Find an env file

    First, the environment variable ENVFILE_PATH is considered. If it is set,
    its value will be used as a filename. 
    If it is not set, python-dotenv's find_dotenv will be used instead.
    """

    if 'ENVFILE_PATH' in os.environ:
        return os.environ('ENVFILE_PATH')

    return find_dotenv()


load_dotenv(find_env_file())

DT_PULL_SERVICE_ADDRESS = os.getenv('DT_PULL_SERVICE_ADDRESS')
SCHEMA_PATH = 'orchestrator/schema_files'
