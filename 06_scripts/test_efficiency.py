"""Regression tests for resuming jobs and avoiding unchanged review work."""
from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

import hx
import test_venues as fixtures
from hxlib.common import list_rounds, load_json, round_dir, save_json
from hxlib.efficiency import response_fingerprint
from smoke_test import make_pdf


class EfficiencyTests(unittest.TestCase):
    setUp = fixtures.VenueTests.setUp
    tearDown = fixtures.VenueTests.tearDown
    create = fixtures.VenueTests.create
    run_cli = fixtures.VenueTests.run_cli

    def output(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = hx.main(list(args))
        return result, buf.getvalue()

    def test_status_only_launches_invalid_jobs(self):
        session = self.create('icml')
        rp = round_dir(session, 1)
        fixtures.outputs(rp)
        result, text = self.output('status', str(session))
        self.assertEqual(result, 0)
        self.assertIn('0 pending', text)
        self.assertNotIn('follow it exactly', text)
        bad = rp / 'reviews' / 'M02' / 'review.json'
        bad.write_text('{broken JSON')
        _, text = self.output('status', str(session))
        launches = [line for line in text.splitlines() if 'follow it exactly' in line]
        self.assertEqual(len(launches), 1)
        self.assertIn('[M02]', launches[0])
        fixtures.outputs(rp)
        data = load_json(bad)
        data['section_scores'] = None
        save_json(bad, data)
        _, text = self.output('status', str(session))
        self.assertEqual(text.count('follow it exactly'), 1)
        self.assertIn('[M02]', text)

    def test_unchanged_and_blank_answers_do_not_create_rounds(self):
        session = self.create('icml')
        rp = round_dir(session, 1)
        fixtures.outputs(rp)
        self.run_cli('aggregate', str(session))
        self.run_cli('stage', str(session), 'writer')
        for action in ('round', 'round'):
            with patch('hx.snapshot_paper', side_effect=AssertionError('Unnecessary PDF processing')):
                result, text = self.output(action, str(session), '--paper', str(self.pdf))
            self.assertEqual(result, 0)
            self.assertIn('No new round', text)
            self.assertEqual(list_rounds(session), [1])
        self.run_cli('retest', str(session))
        self.assertEqual(list_rounds(session), [1, 2])

    def test_substantive_answer_allows_one_round_and_cannot_be_replayed(self):
        session = self.create('icml')
        rp = round_dir(session, 1)
        fixtures.outputs(rp)
        self.run_cli('aggregate', str(session))
        self.run_cli('stage', str(session), 'writer')
        sheet = rp / 'writer' / 'RESPONSE.md'
        sheet.write_text('### M01:W1\nDecision: contest\nAnswer to the reviewer: See Sec. 3, Eq. 2 for the missing argument.\n')
        self.run_cli('round', str(session), '--paper', str(self.pdf))
        self.assertEqual(list_rounds(session), [1, 2])
        rp2 = round_dir(session, 2)
        rnd2 = load_json(rp2 / 'ROUND.json')
        self.assertEqual(rnd2['changes']['changed'], [])
        fixtures.outputs(rp2)
        # Keep this same issue open to test replay, not just rejection of closed IDs.
        verdict_path = rp2 / 'satisfaction' / 'M01' / 'satisfaction.json'
        data = load_json(verdict_path)
        data['items'][0]['status'] = 'not_satisfied'
        save_json(verdict_path, data)
        sheet2 = rp2 / 'writer' / 'RESPONSE.md'
        sheet2.parent.mkdir(exist_ok=True)
        sheet2.write_text(sheet.read_text())
        self.run_cli('round', str(session), '--paper', str(self.pdf))
        self.assertEqual(list_rounds(session), [1, 2])

    def test_unknown_answer_ids_and_whitespace_are_not_new_evidence(self):
        path = self.root / 'answer.md'
        path.write_text('### M01:W1\nDecision: contest\nAnswer to the reviewer: See Sec. 3.\n')
        first = response_fingerprint(path, {'M01:W1'})
        self.assertIsNotNone(first)
        self.assertIsNone(response_fingerprint(path, {'M01:W2'}))
        path.write_text('### M01:W1\nDecision:   contest\nAnswer to the reviewer:   See Sec. 3.\n\n')
        self.assertEqual(response_fingerprint(path, {'M01:W1'}), first)

    def test_changed_main_and_supplement_get_new_rounds(self):
        session = self.create('icml')
        fixtures.outputs(round_dir(session, 1))
        revised = self.root / 'revised.pdf'
        make_pdf(revised, 2)
        self.run_cli('round', str(session), '--paper', str(revised))
        self.assertEqual(list_rounds(session), [1, 2])
        rnd = load_json(round_dir(session, 2) / 'ROUND.json')
        self.assertIn('method', rnd['changes']['changed'])
        fixtures.outputs(round_dir(session, 2))
        supp = self.root / 'supp.pdf'
        make_pdf(supp, 1)
        self.run_cli('round', str(session), '--paper', str(revised), '--supp', str(supp))
        self.assertEqual(list_rounds(session), [1, 2, 3])
        self.assertIn('supplementary', load_json(round_dir(session, 3) / 'ROUND.json')['changes']['added'])

    def test_default_aggregation_does_not_reprocess_old_rounds(self):
        session = self.create('icml')
        fixtures.outputs(round_dir(session, 1))
        self.run_cli('aggregate', str(session))
        self.run_cli('retest', str(session))
        fixtures.outputs(round_dir(session, 2))
        with patch('hx.aggregate_round', wraps=hx.aggregate_round) as aggregate:
            self.run_cli('aggregate', str(session))
            self.assertEqual(aggregate.call_count, 1)
            self.assertEqual(aggregate.call_args.args[0]['round'], 2)
        with patch('hx.aggregate_round', wraps=hx.aggregate_round) as aggregate:
            self.run_cli('aggregate', str(session), '--all')
            self.assertEqual(aggregate.call_count, 2)


if __name__ == '__main__':
    unittest.main()
