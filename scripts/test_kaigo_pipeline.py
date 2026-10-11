"""Negative tests exercise publication gates, including atomic last-good retention."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
import build_kaigo_explainers as build
from kaigo_evidence import extract_pdf, official_url, OfficialRedirect


class PipelineTests(unittest.TestCase):
    def setUp(self):
        doc = fitz.open()
        p = doc.new_page()
        p.insert_text((30, 40), ('A verified proposal and current rule 12 percent.\n' * 30),
                      fontsize=8)
        self.raw = doc.tobytes()
        doc.close()
        self.article = {
            'id': 'n-test', 'status_kind': 'proposal',
            'source_pdf': 'https://www.mhlw.go.jp/content/12300000/test.pdf',
            'pinned_pdf_sha256': hashlib.sha256(self.raw).hexdigest(),
            'verified_claims': [{'claim': 'fixture', 'pdf_page': 1, 'anchor': 'verified proposal'}],
            'numeric_evidence': [{'pdf_page': 1, 'literal': '12 percent', 'scope': 'fixture only'}],
            'one_liner': 'test', 'quick': ['test'], 'explain': ['test'], 'sales': {'test':'test'},
        }

    def test_hash_change_is_rejected(self):
        a = copy.deepcopy(self.article)
        a['pinned_pdf_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'changed'):
            build.examine(a, self.raw)

    def test_missing_hash_and_evidence_are_rejected(self):
        a = copy.deepcopy(self.article)
        a.pop('pinned_pdf_sha256')
        with self.assertRaises(ValueError):
            build.examine(a, self.raw)
        a = copy.deepcopy(self.article)
        a['verified_claims'] = []
        with self.assertRaises(ValueError):
            build.examine(a, self.raw)

    def test_wrong_page_number_and_missing_units_are_rejected(self):
        for field, value in [('pdf_page', 2), ('literal', '12 yen'), ('scope', '')]:
            a = copy.deepcopy(self.article)
            a['numeric_evidence'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                build.examine(a, self.raw)

    def test_invalid_and_image_only_pdfs_are_rejected(self):
        with self.assertRaises(ValueError):
            extract_pdf(b'<html>error</html>')
        doc = fitz.open()
        doc.new_page()
        blank = doc.tobytes()
        doc.close()
        a = copy.deepcopy(self.article)
        a['pinned_pdf_sha256'] = hashlib.sha256(blank).hexdigest()
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            build.examine(a, blank)

    def test_spoofed_hosts_and_external_redirects_are_rejected(self):
        for url in ['http://www.mhlw.go.jp/x', 'https://www.mhlw.go.jp.evil.example/x',
                    'https://user@www.mhlw.go.jp/x', 'https://www.mhlw.go.jp:8080/x']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                official_url(url)
        with self.assertRaises(ValueError):
            OfficialRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.example/x')

    def test_last_good_release_survives_partial_failure(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            draft, approved = p/'draft.json', p/'approved.json'
            a = copy.deepcopy(self.article)
            b = copy.deepcopy(a)
            b['id'] = 'n-second'
            b['verified_claims'][0]['anchor'] = 'unlocated evidence'
            draft.write_text(json.dumps({'articles': [a, b]}))
            approved.write_text('LAST GOOD')
            with (patch.object(build, 'DRAFT', draft), patch.object(build, 'APPROVED', approved),
                  patch.object(build, 'retrieve_pdf', return_value=self.raw),
                  patch.dict('os.environ', {'KAIGO_EVIDENCE_DIR': str(p/'evidence')})):
                with self.assertRaises(ValueError):
                    build.build()
            self.assertEqual(approved.read_text(), 'LAST GOOD')


if __name__ == '__main__':
    unittest.main()
