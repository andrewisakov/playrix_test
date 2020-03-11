import sys
from collections import defaultdict
import datetime
import asyncio
import aiohttp
import argparse
import pprint
import dateutil.parser
from utils import get_value
from config import (
    HOST, COMMIT, ISSUE, PULL_REQUEST,
    LOGIN, PASSWORD, REPO, OWNER, BRANCH,
    MAX_COMMITERS, ISSUE_AGE, PULL_AGE,
)


OLD_PULL_REQUEST = 30
OLD_ISSUE = 14


parser = argparse.ArgumentParser(description='Playrix github analyzer.')
parser.add_argument('--pull', help='pull requests',
                    default=False, action='store_const', const=True)
parser.add_argument('--issues', help='issues', default=False,
                    action='store_const', const=True)
parser.add_argument('--old', help='old pull/isues',
                    default=False, action='store_const', const=True)
parser.add_argument('--commits', const=True, default=False,
                    help='commit activity', action='store_const')
parser.add_argument('--output', help='output file')
parser.add_argument('--host', help='github host', default=HOST)
parser.add_argument('--repo', type=str, help='repo name',
                    default=REPO)
parser.add_argument('--owner', type=str, default=OWNER,
                    help='repo owner')
parser.add_argument('--login', type=str, default=LOGIN)
parser.add_argument('--password', type=str, default=PASSWORD)
parser.add_argument('--branch', type=str, default=BRANCH, help='repo branch')
parser.add_argument('--from', type=str, dest='from_date',
                    default=dateutil.parser.parse('1-1-1T0:0:0Z'),
                    help='from date YYYY-MM-DDTHH:MM:SSZ')
parser.add_argument('--since', type=str, dest='since_date',
                    default=dateutil.parser.parse('9999-12-31T23:59:59Z'),
                    help='since date YYYY-MM-DDTHH:MM:SSZ')
parser.add_argument('--max-commiters', type=int,
                    default=MAX_COMMITERS, help='max commiters count')
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


def check_period(created_at, closed_at):
    is_old = (args.since_date - created_at > PULL_AGE)
    if closed_at and (closed_at < args.since_date):
        is_old = (closed_at - created_at > PULL_AGE)

    closed = closed_at and (closed_at <= args.since_date)
    return is_old, closed


async def get_issues():
    url = f'https://api.{args.host}/repos/{args.owner}/{args.repo}/issues'
    all_issues = await fetch(url)
    issues = {}
    for issue in all_issues:
        number = issue['number']
        issues[number] = await reduce_issue(issue)
        del issues[number]['number']
        issues[number]['created_at'] = dateutil.parser.parse(
            issues[number]['created_at'])
        issues[number]['closed_at'] = dateutil.parser.parse(
            issues[number]['closed_at']) if issues[number]['closed_at'] else None
        if (issues[number]['created_at'] > args.since_date) or (issues[number]['closed_at'] and issues[number]['closed_at'] < args.from_date):
            # Не вписываемся заданный интервал
            del issues[number]
            continue

        issues[number]['is_old'], issues[number]['closed'] = check_period(
            issues[number]['created_at'], issues[number]['closed_at'])
    return issues


async def get_poll_requests(commit_sha):
    # Оказывается, есть способ вытянуть PR для коммита (если есть)
    url = f'https://api.{args.host}/repos/{args.owner}/{args.repo}/commits/{commit_sha}/pulls'
    pull_requests = await fetch(url, headers={'Accept': 'application/vnd.github.groot-preview+json'})
    result = []
    for pull_request in pull_requests:
        pr = await reduce_pull_request(pull_request)
        pr['created_at'] = dateutil.parser.parse(pr['created_at'])
        pr['closed_at'] = dateutil.parser.parse(
            pr['closed_at']) if pr['closed_at'] else None

        if (pr['created_at'] > args.since_date) or (pr['closed_at'] and pr['closed_at'] < args.from_date):
            # Не вписываемся заданный интервал
            continue

        pr['is_old'], pr['closed'] = check_period(
            pr['created_at'], pr['closed_at'])
        result.append(pr)
    return {commit_sha: result}


async def get_commits():
    # Вытянуть коммиты для ветки args.branch
    url = f'https://api.{args.host}/repos/{args.owner}/{args.repo}/commits'
    data = {'type': 'commits', 'data': []}
    branch_commits = await fetch(url)
    # pprint.pprint(branch_commits)
    commits = {}
    activity = defaultdict(int)
    for commit in branch_commits:
        sha = commit.get('sha')
        commits[sha] = await reduce_commit(commit)
        del commits[sha]['id']
        commits[sha]['date'] = dateutil.parser.parse(commits[sha]['date'])
        if not(args.from_date <= commits[sha]['date'] <= args.since_date):
            del commits[sha]
            continue
        if len(activity) >= MAX_COMMITERS:
            break
        activity[commits[sha]['committer']] += 1
    return commits, activity


loop = asyncio.get_event_loop()
loop.set_debug(True)
futures = [get_issues(), get_commits()]

if isinstance(args.from_date, (str, )):
    args.from_date = dateutil.parser.parse(args.from_date)

if isinstance(args.since_date, (str, )):
    args.sine_date = dateutil.parser.parse(args.since_date)

if args.output and futures:
    # Можно и в файл :)
    sys.stdout = open(args.output, 'w')

futures = asyncio.gather(*futures, loop=loop)
issues, commits = loop.run_until_complete(futures)
commits, activity = commits
futures = [get_poll_requests(commit) for commit in commits.keys()]
futures = asyncio.gather(*futures, loop=loop)
pull_requests = loop.run_until_complete(futures)

if args.commits:
    for idx, committer in enumerate([(k, v) for k, v in activity.items()]):
        print('{:<3} {:<16} {:<4}'.format(idx, committer[0], committer[1]))

if args.pull:
    closed = 0
    opened = 0
    oldest = 0

    for pull_request in pull_requests:  # List
        for k, v in pull_request.items():  # Dict
            for c in v:
                if c['closed']:
                    closed += 1
                else:
                    opened += 1
                pldest = 1 if c['is_old'] else 0

    if args.old:
        print('Old pull requests: {:<5}'.format(oldest))
    else:
        print('{:<5} {:<5}'.format(opened, closed))

if args.issues:
    closed = 0
    opened = 0
    oldest = 0
    for _, issue in issues.items():  # Dict
        if issue['closed']:
            closed = +1
        else:
            opened = + 1

    if args.old:
        print('Old issues: {:<5}'.format(oldest))
    else:
        print('{:<5} {:<5}'.format(opened, closed))
