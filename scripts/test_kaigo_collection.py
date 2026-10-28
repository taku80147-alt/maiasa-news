"""Official meeting pages determine which collected source URLs remain active."""
import unittest
from collect_kaigo_documents import reconcile_sources
from build_kaigo_pdf_evidence import source_for_article

class CollectionTests(unittest.TestCase):
    def test_replaced_link_keeps_provenance_but_cannot_be_used_as_current_evidence(self):
        article={'id':'n-pay-269','date':'2026-10-09',
                 'source_url':'https://www.mhlw.go.jp/stf/newpage_76456.html'}
        old='https://www.mhlw.go.jp/content/12300000/old.pdf'
        new='https://www.mhlw.go.jp/content/12300000/new.pdf'
        row={'meeting_url':article['source_url'],'meeting_date':article['date'],
             'pdf_url':old,'sha256':'f'*64,'label':'【資料１】',
             'status':'本文取得・解説未審査','readable_page_rate':1}
        history={old:row}
        reconciled=reconcile_sources(history,[{**row,'pdf_url':new}])
        self.assertEqual(reconciled[old]['status'],'公式掲載URL変更・要再確認')
        self.assertEqual(reconciled[old]['sha256'],'f'*64)
        self.assertEqual(history[old]['status'],'本文取得・解説未審査')
        self.assertEqual(source_for_article(article,list(reconciled.values())),[])

    def test_uninspected_meeting_and_current_url_keep_status(self):
        row={'meeting_url':'meeting-a','status':'本文取得・解説未審査'}
        docs={'old':row,'other':{**row,'meeting_url':'meeting-b'}}
        candidates=[{'meeting_url':'meeting-a','pdf_url':'old'}]
        self.assertEqual(reconcile_sources(docs,candidates),docs)



class CommitteeLabelTests(unittest.TestCase):
    def test_research_committee_is_not_reported_as_the_parent_subcommittee(self):
        from update_kaigo_reform import scan
        html='<table><tr><td>第33回</td><td>2026年10月26日</td><td>介護報酬改定検証・研究委員会 令和6年度改定の効果検証調査の結果</td><td><a href="/stf/newpage_76754.html">資料</a></td></tr></table>'
        rows=scan('pay','介護給付費分科会','https://www.mhlw.go.jp/stf/index.html',html)
        self.assertEqual(rows[0]['title'],'第33回介護報酬改定検証・研究委員会の資料が公開')
        self.assertIn('介護報酬改定検証・研究委員会',rows[0]['source_name'])
