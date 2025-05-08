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

API_KEY = os.getenv('API_KEY')
API_CONTEXT_EDR = os.getenv('API_CONTEXT_EDR')
BASE_URL = os.getenv('BASE_URL')
