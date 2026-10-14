#!/usr/bin/env python3
"""Read-only, low-trust GitHub bounty lead monitor. Stdlib only."""
import argparse
import datetime
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

QUERIES = [
    'is:issue is:open label:bounty updated:>=2026-09-01',
    'is:issue is:open label:"Help Wanted" "$" updated:>=2026-09-01',
]
AMOUNT = re.compile(r'(?<!\w)\$\s*([1-9][\d,]*(?:\.\d{1,2})?)\b')
UNPAID = re.compile(r'\b(?:not a paid bounty|unpaid|no money|not redeemable|no payment)\b', re.I)

def shortlist(issues):
    results = []
    seen = set()
    for issue in issues:
        url = issue.get('html_url', '')
        if url in seen or 'pull_request' in issue or issue.get('state') != 'open':
            continue
        seen.add(url)
        title, body = issue.get('title') or '', issue.get('body') or ''
        if UNPAID.search(title + ' ' + body[:3000]):
            continue
        match = AMOUNT.search(title) or AMOUNT.search(body[:1800])
        if not match:
            continue
        dollars = float(match.group(1).replace(',', ''))
        if not 5 <= dollars <= 10000:
            continue
        assigned = bool(issue.get('assignee') or issue.get('assignees'))
        proposed = 'proposal' in title.lower()
        comments = int(issue.get('comments', 0))
        score = min(dollars, 1000) / 20 - 15*assigned - 20*proposed - min(comments, 40)
        results.append({'title': title, 'url': url, 'advertised_usd': dollars,
                        'assigned': assigned, 'proposal_only': proposed,
                        'comments': comments, 'priority': round(score,1),
                        'payment_verified': False})
    return sorted(results, key=lambda item: item['priority'], reverse=True)

def get_issues(token):
    all_issues=[]
    for query in QUERIES:
        url='https://api.github.com/search/issues?'+urllib.parse.urlencode(
            {'q':query,'sort':'updated','order':'desc','per_page':100})
        headers={'Accept':'application/vnd.github+json','User-Agent':'ReadOnlyBountyScout/1.0'}
        if token: headers['Authorization']='Bearer '+token
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
            all_issues.extend(json.load(response)['items'])
    return all_issues

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', help='Read a JSON fixture instead of network access')
    parser.add_argument('--output',default='bounty_leads.json')
    opts=parser.parse_args()
    if opts.fixture:
        sample=json.loads(Path(opts.fixture).read_text(encoding='utf-8'))
        issues=sample['items'] if isinstance(sample,dict) else sample
    else:
        issues=get_issues(os.getenv('GITHUB_TOKEN',''))
    data={'date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'disclaimer':'Leads only; advertised amount is not guaranteed payment',
          'leads':shortlist(issues)}
    Path(opts.output).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f"{len(data['leads'])} leads saved to {opts.output}; funding unverified")

if __name__=='__main__': main()
