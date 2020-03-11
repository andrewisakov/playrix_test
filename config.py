import os
import sys
import yaml
import datetime


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

REPO_CONF = CONFIG.get('repo', {})
REPO = REPO_CONF.get('name')
OWNER = REPO_CONF.get('owner')
BRANCH = REPO_CONF.get('branch', 'master')
MAX_COMMITERS = REPO_CONF.get('max_commiters', 30)
ISSUE_AGE = datetime.timedelta(days=REPO_CONF.get('issue_age', 14))
PULL_AGE = datetime.timedelta(days=REPO_CONF.get('pull_age', 30))
