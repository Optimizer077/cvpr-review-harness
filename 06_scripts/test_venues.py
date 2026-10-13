"""Integration tests for venue routing, evidence validation and frozen instruments."""
from __future__ import annotations

import contextlib
import copy
import io
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hx
from smoke_test import make_pdf, fake_review
from hxlib.common import load_json, save_json, review_dir, round_dir
from hxlib.panel import draw_panel, load_personas
from hxlib.venues import instrument, scales_for
from hxlib.validate import validate_round


def extensions(data, job, rnd):
    config = rnd['review_config']
    if job.get('careful'):
        data['first_impression'] = None
        data['evidence_audit'] = {
            'coverage': {s: {'status': 'checked', 'note': 'Synthetic fixture, Sec. 3'} for s in job['sections']},
            'claim_checks': [{'claim': 'Toy method improves toy metric', 'location': 'Abstract',
                              'evidence': 'Synthetic Table 1', 'verdict': 'partial'}]}
    profile = config['profile']
    if profile['dimensions']:
        data['venue_assessment'] = {'profile': profile['id'], 'dimensions': {
            d: {'score': 3, 'reason': 'Synthetic assessment', 'location': 'Sec. 3'}
            for d in profile['dimensions'] if job['overall']}}
    return data


def outputs(rpath):
    rnd = load_json(rpath / 'ROUND.json')
    for job in rnd['jobs']:
        data = extensions(fake_review(job, rnd, random.Random(4)), job, rnd)
        if job.get('stage') == 'satisfy':
            out = rpath / 'satisfaction' / job['job_id']
            data.update(stage='satisfy', previous_rating=3, items=[{
                'id': wid, 'status': 'satisfied', 'reason': 'Synthetic fix', 'evidence': 'Sec. 3'}
                for wid in job['open_items']], new_issues=[])
            save_json(out / 'satisfaction.json', data)
            (out / 'reply.md').write_text('Synthetic answer check with enough content for the output-size validation.\n')
        else:
            out = review_dir(rpath, job)
            save_json(out / 'review.json', data)
            (out / 'review.md').write_text('\n'.join('## ' + h + '\nSynthetic review.' for h in scales_for(rnd)['review_md_headings']))
            (out / 'debrief.md').write_text('Synthetic debrief with enough content for the output-size validation.\n')


class VenueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pdf = self.root / 'paper.pdf'
        make_pdf(self.pdf, 1)
        self.patcher = patch.object(hx, 'SESSIONS_DIR', self.root / 'sessions')
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def run_cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            return hx.main(list(args))

    def create(self, venue, name='test', *extra):
        self.run_cli('new', '--paper', str(self.pdf), '--name', name, '--venue', venue, *extra)
        return next(p for p in hx.SESSIONS_DIR.iterdir() if p.name.endswith('_' + name))

    def test_all_venues_full_sections_dialogue_retest(self):
        for venue, prefix, heldout in [('iclr', 'I', 'I04'), ('icml', 'M', 'M04'), ('neurips', 'N', 'N05')]:
            for mode in ('full', 'sections', 'both'):
                with self.subTest(venue=venue, mode=mode):
                    spath = self.create(venue, venue + mode, '--mode', mode, '--heldout', heldout)
                    r1 = round_dir(spath, 1)
                    rnd = load_json(r1 / 'ROUND.json')
                    self.assertTrue(all(j['reviewer'].startswith(prefix) and j['view'] == 'full' for j in rnd['jobs']))
                    for prompt in (r1 / 'prompts' / 'initial').glob('*.md'):
                        text = prompt.read_text(encoding='utf-8')
                        self.assertIn('evidence_audit', text)
                        self.assertNotIn('reviewer of a CVPR submission', text)
                        self.assertNotIn('Keep this offset', text)
                    outputs(r1)
                    self.assertTrue(all(not e for e in validate_round(rnd, r1).values()))
                    self.assertEqual(self.run_cli('aggregate', str(spath)), 0)
                    self.run_cli('stage', str(spath), 'writer')
                    self.run_cli('round', str(spath), '--paper', str(self.pdf))
                    r2 = round_dir(spath, 2)
                    outputs(r2)
                    self.assertEqual(self.run_cli('validate', str(spath)), 0)
                    self.run_cli('aggregate', str(spath))
                    for prompt in (r2 / 'prompts' / 'satisfy').glob('*.md'):
                        self.assertIn('evidence_audit', prompt.read_text(encoding='utf-8'))
                        self.assertNotIn('Base rates from', prompt.read_text(encoding='utf-8'))
                    scores = load_json(r2 / 'SCORES.json')
                    self.assertTrue(all(row['evidence_audit'] for row in scores['rows'].values()))
                    self.run_cli('retest', str(spath))
                    self.assertTrue(all(j.get('stage', 'initial') == 'initial' for j in load_json(round_dir(spath, 3) / 'ROUND.json')['jobs']))

    def test_invalid_assessments_fail_and_empty_weaknesses_pass(self):
        spath = self.create('icml')
        rp = round_dir(spath, 1)
        rnd = load_json(rp / 'ROUND.json')
        outputs(rp)
        job = rnd['jobs'][0]
        path = review_dir(rp, job) / 'review.json'
        base = load_json(path)
        base['weaknesses'] = []
        save_json(path, base)
        self.assertEqual(validate_round(rnd, rp)[job['job_id']], [])
        for change in ('missing_audit', 'wrong_profile', 'out_of_range', 'bool_score', 'missing_section', 'bad_claim', 'premature_score'):
            data = copy.deepcopy(base)
            if change == 'missing_audit': del data['evidence_audit']
            if change == 'wrong_profile': data['venue_assessment']['profile'] = 'neurips2026'
            if change == 'out_of_range': data['overall']['rating'] = 7
            if change == 'bool_score': data['venue_assessment']['dimensions']['soundness']['score'] = True
            if change == 'missing_section': data['evidence_audit']['coverage'] = {}
            if change == 'bad_claim': data['evidence_audit']['claim_checks'] = [{}]
            if change == 'premature_score': data['first_impression'] = {'rating': 3}
            save_json(path, data)
            self.assertTrue(validate_round(rnd, rp)[job['job_id']], change)
        self.assertEqual(self.run_cli('aggregate', str(spath)), 1)
        self.assertFalse((rp / 'SCORES.json').exists())

    def test_frozen_instruments_survive_updates(self):
        spath = self.create('neurips')
        session = load_json(spath / 'SESSION.json')
        with patch('hxlib.venues.load_scales', side_effect=AssertionError('live scale read')), \
             patch('hx.load_personas', side_effect=AssertionError('live persona read')), \
             patch('hxlib.panel.load_section_map', side_effect=AssertionError('live panel read')):
            self.run_cli('retest', str(spath))
            rnd = load_json(round_dir(spath, 2) / 'ROUND.json')
            self.assertEqual(scales_for(rnd), session['review_config']['scales'])
        from hxlib.common import PROTOCOL_DIR
        with patch.object(Path, 'read_text', side_effect=AssertionError('live rule read')):
            self.assertIn('Careful reading', instrument(session, PROTOCOL_DIR / 'careful_review.md'))

    def test_profile_routing_and_fail_early(self):
        for kind, reviewer in [('theory', 'N02'), ('use_inspired', 'N03'), ('concept_feasibility', 'N04'), ('negative_results', 'N05')]:
            spath = self.create('NeurIPS 2026', kind, '--contribution-type', kind)
            self.assertIn(reviewer, load_json(spath / 'SESSION.json')['panel_ids'])
        before = set(hx.SESSIONS_DIR.iterdir())
        for args in [('--venue', 'ICML 2027'), ('--venue', 'iclr', '--scale', 'cvpr26_5'),
                     ('--venue', 'icml', '--reviewers', 'R03'), ('--venue', 'iclr', '--contribution-type', 'theory'),
                     ('--venue', 'icml', '--reading', 'persona')]:
            with self.assertRaises((ValueError, KeyError)):
                self.run_cli('new', '--paper', str(self.pdf), '--name', 'bad', *args)
        self.assertEqual(set(hx.SESSIONS_DIR.iterdir()), before)
        self.assertEqual(len(draw_panel('gauntlet', 0, load_personas())), 16)

    def test_cvpr_careful_has_no_skim_or_offset(self):
        spath = self.create('cvpr', 'careful', '--reading', 'careful', '--reviewers', 'R09')
        rp = round_dir(spath, 1)
        rnd = load_json(rp / 'ROUND.json')
        self.assertEqual(rnd['jobs'][0]['view'], 'full')
        text = (rp / 'prompts' / 'initial' / 'R09.md').read_text(encoding='utf-8')
        self.assertNotIn('Keep this offset', text)
        outputs(rp)
        self.assertEqual(self.run_cli('validate', str(spath)), 0)


if __name__ == '__main__':
    unittest.main()
