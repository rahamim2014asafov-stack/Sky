#!/usr/bin/env python3
"""Read-only GitHub bounty lead discovery. No payment or acceptance is assumed.

Security: only GitHub's public search/issues REST metadata is fetched. Never runs
external commands, downloads repository code, or follows instructions from issues.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = 'https://api.github.com/search/issues?'
DOLLAR = re.compile(r'(?<![\w])(?:\$\s*|USD\s*\$?\s*)([1-9]\d{0,5}(?:,\d{3})*(?:\.\d{1,2})?)(?![\d])|\b([1-9]\d{0,5}(?:,\d{3})*(?:\.\d{1,2})?)\s*USD\b', re.I)
NEGATIVE = re.compile(r'\b(?:not\s+(?:a\s+)?paid|unpaid|no\s+money|no\s+payment|not\s+redeemable|virtual\s+(?:coins?|credits?|tokens?))\b', re.I)
PROPOSAL = re.compile(r'\b(?:bounty\s+proposal|proposed\s+(?:bounty|reward)|suggested\s+(?:bounty|reward))\b', re.I)
MONEYWORDS = re.compile(r'\b(?:bounty|paid|pays|reward|funded|prize|payment|sponsor)\b', re.I)
MARKDOWN = re.compile(r'([\\`*_{}\[\]()<>|])')
# These are aggregators/mirrors that regularly carry duplicated or simulated jobs.
IGNORED_REPO_PARTS = ('/bounty-plaza', '/ai-research', '/awesome-agent-bounties', '/bountyscout')


def money_values(text: str) -> list[float]:
    values = []
    for match in DOLLAR.finditer(text):
        amount = float((match.group(1) or match.group(2)).replace(',', ''))
        if 5 <= amount <= 20000:
            values.append(amount)
    return values


def repo_of(issue: dict) -> str:
    api_url = issue.get('repository_url') or ''
    if '/repos/' in api_url:
        return api_url.rsplit('/repos/', 1)[-1]
    repo = issue.get('repository') or {}
    return repo.get('full_name') or ''


def candidate(issue: dict, now: datetime) -> dict | None:
    if issue.get('state') != 'open' or issue.get('pull_request'):
        return None
    url = issue.get('html_url') or ''
    if not url.startswith('https://github.com/'):
        return None
    repo = repo_of(issue)
    if not repo or any(p in repo.lower() for p in IGNORED_REPO_PARTS):
        return None
    title = issue.get('title') or ''
    body = issue.get('body') or ''
    sample = (title + '\n' + body[:4000])
    if NEGATIVE.search(sample):
        return None
    if not MONEYWORDS.search(sample):
        return None
    amounts = money_values(title) or money_values(body[:1200])
    if not amounts:
        return None
    advertised = max(amounts)
    comments = int(issue.get('comments') or 0)
    assigned = bool(issue.get('assignee') or issue.get('assignees'))
    proposed = bool(PROPOSAL.search(title + ' ' + body[:100]))
    try:
        updated = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
    except (KeyError, ValueError, TypeError):
        updated = now - timedelta(days=365)
    days = max(0, (now - updated).days)
    # Heuristic, NOT a probability of payout: penalize competition and uncertainty.
    score = round(min(advertised, 500) / 12 - math.log2(1 + comments) * 5
                  - min(days, 60) * 0.25 - (35 if assigned else 0)
                  - (30 if proposed else 0), 2)
    flags = []
    if comments >= 20: flags.append('high discussion/competition')
    if comments >= 100: flags.append('very crowded')
    if assigned: flags.append('already assigned')
    if proposed: flags.append('proposed reward only')
    if days > 30: flags.append('possibly stale')
    flags.append('funding/payment NOT verified')
    return {
        'url': url, 'repository': repo, 'number': issue.get('number'),
        'title': title, 'advertised_usd': advertised,
        'comments': comments, 'assigned': assigned, 'proposal_only': proposed,
        'last_updated_utc': updated.isoformat(), 'heuristic_score': score,
        'review_flags': flags, 'funding_verified': False, 'payment_received': False,
    }


def _fetch(url: str, token: str) -> dict:
    headers = {'Accept': 'application/vnd.github+json',
               'User-Agent': 'ReadOnlyBountyScout/2.0',
               'X-GitHub-Api-Version': '2022-11-28'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request(url, headers=headers), timeout=20) as response:
        return json.load(response)


def collect(now: datetime, days: int, per_page: int, token: str) -> tuple[list[dict], list[str]]:
    since = (now - timedelta(days=days)).date().isoformat()
    searches = [
        f'is:issue is:open label:bounty updated:>={since}',
        f'is:issue is:open label:"Help Wanted" "$" updated:>={since}',
        f'is:issue is:open in:title "bounty" "$" updated:>={since}',
    ]
    found: dict[str, dict] = {}
    errors = []
    for query in searches:
        url = API + urlencode({'q': query, 'sort': 'updated', 'order': 'desc', 'per_page': per_page})
        try:
            data = _fetch(url, token)
            for issue in data.get('items', []):
                info = candidate(issue, now)
                if info:
                    found[info['url']] = info
        except HTTPError as error:
            # Do not echo potentially sensitive headers/request content.
            errors.append(f'GitHub search failed with HTTP {error.code} for query {query!r}')
        except (URLError, TimeoutError, OSError, ValueError, KeyError) as error:
            errors.append(f'GitHub search error ({type(error).__name__}) for query {query!r}')
    return sorted(found.values(), key=lambda x: x['heuristic_score'], reverse=True), errors


def _md(text: str) -> str:
    return MARKDOWN.sub(r'\\\1', text.replace('\r', ' ').replace('\n', ' '))


def as_markdown(payload: dict, limit: int = 25) -> str:
    lines = [
        '# GitHub Bounty Watch', '',
        f"Scan (UTC): {payload['scan_time_utc']}", '',
        '**Not earnings:** all amounts are advertised claims; funding, eligibility,',
        'acceptance, and payment require independent verification.', '',
        '| Score* | Task | Claimed USD | Comments | Risk |',
        '|---:|---|---:|---:|---|',
    ]
    for x in payload['leads'][:limit]:
        title = _md(x['title'][:90])
        status = ', '.join(x['review_flags'][:2])
        lines.append(f"| {x['heuristic_score']:.1f} | [{title}]({x['url']}) | "
                     f"${x['advertised_usd']:g} | {x['comments']} | {_md(status)} |")
    if not payload['leads']:
        lines.append('| — | No suitable leads found | — | — | — |')
    lines += ['', '*Score is a sorting heuristic, **not** a payout probability.*', '',
              'Before claiming: check existing PRs, sponsor/funding receipts, current',
              'availability, actual payment terms, eligibility in your country, and',
              'test requirements. Never share keys/wallets in public comments.', '']
    if payload['errors']:
        lines += ['## Incomplete scan (API errors)', ''] + ['- ' + _md(x) for x in payload['errors']]
    return '\n'.join(lines) + '\n'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', help='Read local synthetic GitHub search JSON (no network)')
    parser.add_argument('--output', default='bounty_leads.json')
    parser.add_argument('--markdown', default='bounty_leads.md')
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--per-page', type=int, default=75)
    args = parser.parse_args(argv)
    if not 1 <= args.days <= 90 or not 1 <= args.per_page <= 100:
        parser.error('--days must be 1..90 and --per-page must be 1..100')
    now = datetime.now(timezone.utc)
    if args.fixture:
        source = json.loads(Path(args.fixture).read_text(encoding='utf-8'))
        raw_items = source.get('items', []) if isinstance(source, dict) else source
        leads = [row for item in raw_items if (row := candidate(item, now))]
        leads.sort(key=lambda x: x['heuristic_score'], reverse=True)
        errors = []
    else:
        leads, errors = collect(now, args.days, args.per_page, os.getenv('GITHUB_TOKEN', ''))
    data = {'scan_time_utc': now.isoformat(), 'leads': leads, 'errors': errors,
            'payment_disclaimer': 'Unverified leads only. Never count reward as received income.'}
    Path(args.output).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    md = as_markdown(data)
    Path(args.markdown).write_text(md, encoding='utf-8')
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(md)
    print(f"Discovered {len(leads)} leads, {len(errors)} API errors. Reports: {args.output}, {args.markdown}")
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
