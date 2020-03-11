import sys
import datetime
import asyncio
import aiohttp
import argparse
import pprint
from utils import get_value
from config import (
    HOST, COMMIT, ISSUE, PULL_REQUEST,
    LOGIN, PASSWORD, REPO, OWNER, BRANCH
)


OLD_PULL_REQUEST = 30
OLD_ISSUE = 14


parser = argparse.ArgumentParser(description='Playrix github analyzer.')
parser.add_argument('--pull', type=bool, help='pull requests', default=False)
parser.add_argument('--issues', type=bool, help='issues', default=False)
parser.add_argument('--old', type=bool, help='old pull/isues', default=False)
parser.add_argument('--commits', const=True, default=False,
                    help='commit activity', action='store_const')
parser.add_argument('--output', help='output file')
parser.add_argument('--host', help='github host', default=HOST, required=True)
parser.add_argument('--repo', type=str, help='repo name',
                    default=REPO, required=True)
parser.add_argument('--owner', type=str, default=OWNER,
                    help='repo owner', required=True)
parser.add_argument('--login', type=str, default=LOGIN)
parser.add_argument('--password', type=str, default=PASSWORD)
parser.add_argument('--branch', type=str, default=BRANCH, help='repo branch')
parser.add_argument('--from', type=str, dest='from_date',
                    default=datetime.date(datetime.MINYEAR, 1, 1), help='from date YYYY-MM-DD')
parser.add_argument('--since', type=str, dest='since_date',
                    default=datetime.date(datetime.MAXYEAR, 12, 31), help='since date YYYY-MM-DD')
args = parser.parse_args()


async def reduce_commit(commit):
    # Разбор коммита
    result = {}
    for k, v in COMMIT.items():
        result[k] = get_value(v, commit)
    return result


async def reduce_issue(issue):
    # Разбор issue
    result = {}
    for k, v in ISSUE.items():
        result[k] = get_value(v, issue)
    return result


async def reduce_pull_request(pull_request):
    # Разбор pull_request
    result = {}

    for k, v in PULL_REQUEST.items():
        result[k] = get_value(v, pull_request)
    return result


async def fetch(url, headers=None):
    auth = aiohttp.BasicAuth(login=args.login,
                             password=args.password, encoding='utf-8')

    async with aiohttp.ClientSession(auth=auth) as session:
        async with session.get(url, headers=headers) as response:
            return await response.json()


async def get_issues():
    url = f'https://api.{args.host}/repos/{args.owner}/{args.repo}/issues'
    all_issues = await fetch(url)
    issues = {}
    for issue in all_issues:
        number = issue['number']
        issues[number] = await reduce_issue(issue)
        del issues[number]['number']

    return issues


async def get_poll_requests(commit_sha):
    # Оказывается, есть способ вытянуть PR для коммита (если есть)
    url = f'https://api.{args.host}/repos/{args.owner}/{args.repo}/commits/{commit_sha}/pulls'
    pull_requests = await fetch(url, headers={'Accept': 'application/vnd.github.groot-preview+json'})
    result = []
    for pull_request in pull_requests:
        result.append(await reduce_pull_request(pull_request))
    return {commit_sha: result}


async def get_commits():
    # Вытянуть коммиты для ветки args.branch
    url = f'https://api.{args.host}/repos/{args.owner}/{args.repo}/commits'
    data = {'type': 'commits', 'data': []}
    branch_commits = await fetch(url)
    # pprint.pprint(branch_commits)
    commits = {}
    for commit in branch_commits:
        sha = commit.get('sha')
        commits[sha] = await reduce_commit(commit)
    return commits


print(args)

loop = asyncio.get_event_loop()
loop.set_debug(True)
futures = [get_issues(), get_commits()]

if args.from_date:
    pass

if args.since_date:
    pass

if args.output and futures:
    sys.stdout = open(args.output, 'w')

if futures:
    futures = asyncio.gather(*futures, loop=loop)
    issues, commits = loop.run_until_complete(futures)
    futures = [get_poll_requests(commit) for commit in commits.keys()]
    futures = asyncio.gather(*futures, loop=loop)
    pull_requests = loop.run_until_complete(futures)
    pprint.pprint(commits)
    pprint.pprint(issues)
    pprint.pprint(pull_requests)
else:
    print('Nothing do!')
