"""Deterministic, network-free bounty lead classification tests."""
import sys
from datetime import datetime, timezone
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from github_bounty_scout import candidate, money_values, as_markdown, repo_of

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)

def issue(**overrides):
    payload = {'state':'open','html_url':'https://github.com/acme/project/issues/4',
        'repository_url':'https://api.github.com/repos/acme/project',
        'number':4,'title':'[Bounty $100] Fix the mobile view',
        'body':'Pays $100 when merged', 'updated_at':'2026-10-14T09:00:00Z',
        'comments':2, 'assignees':[]}
    payload.update(overrides)
    return payload

class ScannerTests(unittest.TestCase):
    def test_funded_is_not_inferred(self):
        found = candidate(issue(), NOW)
        self.assertEqual(found['advertised_usd'], 100)
        self.assertFalse(found['funding_verified'])
        self.assertFalse(found['payment_received'])

    def test_unpaid_label(self):
        self.assertIsNone(candidate(issue(body='Not a paid bounty. No money'), NOW))

    def test_virtual_token_payout_rejected(self):
        self.assertIsNone(candidate(issue(body='Virtual tokens awarded; no payment'), NOW))

    def test_does_not_accept_pull_request(self):
        self.assertIsNone(candidate(issue(pull_request={'url':'https://api.github.com'}), NOW))

    def test_assigned_penalty(self):
        a = candidate(issue(), NOW)
        b = candidate(issue(assignees=[{'login':'other'}]), NOW)
        self.assertLess(b['heuristic_score'], a['heuristic_score'])

    def test_comments_penalty(self):
        a = candidate(issue(), NOW)
        b = candidate(issue(comments=1848), NOW)
        self.assertLess(b['heuristic_score'], a['heuristic_score'])
        self.assertIn('very crowded', b['review_flags'])

    def test_proposal_penalty(self):
        a = candidate(issue(), NOW)
        b = candidate(issue(title='[Bounty proposal] $100 fix'), NOW)
        self.assertTrue(b['proposal_only'])
        self.assertLess(b['heuristic_score'], a['heuristic_score'])

    def test_url_must_be_github(self):
        self.assertIsNone(candidate(issue(html_url='javascript:alert(1)'), NOW))

    def test_aggregate_mirrors_excluded(self):
        self.assertIsNone(candidate(issue(repository_url='https://api.github.com/repos/Vikingr2023/awesome-agent-bounties'), NOW))

    def test_dollar_variants(self):
        self.assertEqual(money_values('Pays 150 USD, or $100'), [150.0,100.0])

    def test_escape_untrusted_titles_in_markdown(self):
        item = candidate(issue(title='[Bounty $100] Bad | <tag> [foo](bar)'), NOW)
        md = as_markdown({'scan_time_utc':'now','leads':[item], 'errors':[]})
        self.assertIn(r'\|', md)
        self.assertIn(r'\<tag\>', md)
        self.assertNotIn('<tag>', md)

    def test_closed_rejected(self):
        self.assertIsNone(candidate(issue(state='closed'), NOW))

    def test_repo_extract(self):
        self.assertEqual(repo_of(issue()), 'acme/project')

if __name__ == '__main__':
    unittest.main()
