#!/usr/bin/env python3
"""Offline quality gates for the free reviewed-explainer content."""
import json
import re
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parent.parent/'kaigo-navi2027-preview'/'data'

class TestCareReformExplainers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.draft=json.loads((BASE/'explainers.json').read_text(encoding='utf-8'))
        cls.release=json.loads((BASE/'explainers-verified.json').read_text(encoding='utf-8'))

    def test_all_articles_match_verified_release(self):
        self.assertEqual(self.draft['articles'],self.release['articles'])

    def test_every_source_pdf_fully_read_and_pinned(self):
        audits={x['id']:x for x in self.release['source_audits']}
        for a in self.draft['articles']:
            with self.subTest(a=a['id']):
                self.assertIn(a['id'],audits)
                doc=audits[a['id']]
                self.assertEqual(doc['sha256'],a['pinned_pdf_sha256'])
                self.assertGreaterEqual(doc['pdf_pages_read'],1)
                self.assertGreater(doc['characters_read'],700)
                self.assertEqual(len(doc['evidence_checks']),len(a['verified_claims']))
                self.assertTrue(all(x['status']=='located' for x in doc['evidence_checks']))
                self.assertGreaterEqual(doc['readable_page_rate'],.75 if doc['pdf_pages_read']>3 else 0)
                self.assertEqual(len(doc['numeric_checks']),len(a['numeric_evidence']))
                self.assertTrue(all(v['status']=='located' and v['scope'] for v in doc['numeric_checks']))

    def test_information_classified_as_proposal(self):
        for a in self.draft['articles']:
            self.assertIn('検討中',a['status'])
            self.assertEqual(a['source_page'].split('/')[2],'www.mhlw.go.jp')
            self.assertEqual(a['source_pdf'].split('/')[2],'www.mhlw.go.jp')
            self.assertGreaterEqual(len(a['quick']),3)
            self.assertGreaterEqual(len(a['explain']),4)
            self.assertTrue('現在' in a['now_vs_next']['now'] or '現行' in a['now_vs_next']['now'])
            self.assertTrue(all(v.get('source') for v in a['explain']))
            self.assertIn('caremanager',a['sales'])
            self.assertIn('family',a['sales'])

    def test_numeric_scope_prevents_false_2027_forecast(self):
        a=next(x for x in self.draft['articles'] if x['id']=='n-pay-259')
        evidence=' '.join(c['anchor'] for c in a['verified_claims'])
        self.assertIn('88.7%',evidence)
        self.assertIn('11.3%',evidence)
        self.assertIn('2024',a['quick'][2])
        self.assertIn('商品数',a['quick'][2])
        self.assertIn('2027',a['numerical_caution'])
        self.assertIn('歩行車を除く',a['quick'][0])
        self.assertIn('松葉杖を除く',a['quick'][0])

    def test_curated_four_articles_and_document_source(self):
        article_ids={a['id'] for a in self.draft['articles']}
        self.assertTrue({'n-pay-268','n-pay-259','n-pay-269-gh','n-pay-269-sm'}<=article_ids)
        index=json.loads((BASE/'latest.json').read_text(encoding='utf-8'))
        visible_ids={a['id'] for a in index['articles']}
        self.assertEqual(len(visible_ids),len(index['articles']),'latest news must not contain duplicate IDs')
        self.assertTrue(article_ids <= visible_ids)

    def test_single_document_full_five_directions(self):
        a=next(x for x in self.draft['articles'] if x['id']=='n-pay-268')
        self.assertEqual(len(a['explain']),5)
        self.assertEqual(self.release['source_audits'][0]['pdf_pages_read'],1)
        self.assertIn('5つ',a['one_liner'])
        self.assertIn('未決定',a['explain'][1]['body'])

if __name__=='__main__':unittest.main()
