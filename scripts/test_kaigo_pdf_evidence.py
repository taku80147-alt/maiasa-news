"""Offline tests for PDF evidence cards; never label unreviewed snippets as approved law."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz
import build_kaigo_pdf_evidence as x

class EvidenceBriefTests(unittest.TestCase):
    def test_headings_only_from_proposal_pages(self):
        page='第270回 論点①\n対応案\n（入浴介助加算の見直し）\n◼ この見直しの条件は今後検討してはどうか。\n'
        hits=x.headings_from_page(page,8)
        self.assertEqual(hits[0]['heading'],'入浴介助加算の見直し')
        self.assertEqual(hits[0]['pdf_page'],8)
        self.assertEqual(x.headings_from_page(page.replace('対応案','主なご意見'),8),[])
    def test_no_policy_claim_on_table_only(self):
        self.assertEqual(x.headings_from_page('参考資料\n報酬単位数 300点\n',2),[])
    def test_hash_mismatch_blocks_publication(self):
        with patch.object(x,'fetch',return_value=b'%PDF-testwrong'):
            doc={'pdf_url':'https://www.mhlw.go.jp/content/12300000/example.pdf',
                 'sha256':'0'*64,'label':'【資料１】','status':'本文取得・解説未審査'}
            with self.assertRaisesRegex(ValueError,'changed'):x.inspect_document(doc)
    def test_latest_document_selection_pinned_official(self):
        article={'id':'n-pay-270','date':'2026-10-14',
                 'source_url':'https://www.mhlw.go.jp/stf/newpage_76633.html'}
        row=dict(meeting_url=article['source_url'],meeting_date=article['date'],
          pdf_url='https://www.mhlw.go.jp/content/12300000/001759344.pdf',
          label='【資料１】通所介護',sha256='f'*64,
          status='本文取得・解説未審査',readable_page_rate=1)
        result=x.source_for_article(article,[row,{**row,'label':'【参考資料】'},{
          **row,'pdf_url':'https://www.mhlw.go.jp.evil.example/evil.pdf'}])
        self.assertEqual(len(result),1)
    def test_fetch_failure_preserves_complete_previous_evidence(self):
        article={'id':'n-pay-270','date':'2026-10-14',
                 'source_url':'https://www.mhlw.go.jp/stf/newpage_76633.html'}
        row=dict(meeting_url=article['source_url'],meeting_date=article['date'],
                 pdf_url='https://www.mhlw.go.jp/content/12300000/test.pdf',
                 label='【資料１】通所介護',sha256='f'*64,
                 status='本文取得・解説未審査',readable_page_rate=1)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            news=root/'latest.json'; queue=root/'queue.json'; output=root/'evidence.json'
            news.write_text(json.dumps({'articles':[article]}))
            queue.write_text(json.dumps({'documents':[row]}))
            prior='{"articles":[{"id":"previous","documents":[]}]}'
            output.write_text(prior)
            with patch.object(x,'NEWS',news), patch.object(x,'QUEUE',queue), \
                 patch.object(x,'OUTPUT',output), \
                 patch.object(x,'inspect_document',side_effect=OSError('network unavailable')):
                with self.assertRaisesRegex(RuntimeError,'preserve prior evidence'):
                    x.build()
            self.assertEqual(output.read_text(),prior)

    def test_draft_and_approved_explainers_are_not_confused(self):
        data=Path(__file__).resolve().parents[1]/'kaigo-navi2027-preview'/'data'
        draft=json.loads((data/'explainers.json').read_text(encoding='utf-8'))
        approved=json.loads((data/'explainers-verified.json').read_text(encoding='utf-8'))
        self.assertTrue(set(a['id'] for a in approved['articles'])<=
                        set(a['id'] for a in draft['articles']))

if __name__=='__main__':unittest.main()
