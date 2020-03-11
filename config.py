import os
import sys
import yaml


SERVICE_ROOT_DIR = os.path.dirname(__file__)
sys.path.append(SERVICE_ROOT_DIR)

CONFIG = yaml.safe_load(open(os.path.join(SERVICE_ROOT_DIR, 'config.yaml')))

API = CONFIG.get('api')
HOST = API.get('host')

COMMIT = API.get('commit')
PULL_REQUEST = API.get('pull_request')
ISSUE = API.get('issue')

LOGIN = CONFIG.get('authenticate', {}).get('login')
PASSWORD = CONFIG.get('authenticate', {}).get('password')

REPO = CONFIG.get('repo', {}).get('name')
OWNER = CONFIG.get('repo', {}).get('owner')
BRANCH = CONFIG.get('repo', {}).get('branch', 'master')
