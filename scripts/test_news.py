import copy,json,tempfile,unittest
from datetime import date,datetime
from pathlib import Path
import update_news as n
TODAY=date(2026,10,11)
NOW=datetime(2026,10,11,12,tzinfo=n.JST)
def row(source='sendai',**kw):
    r=dict(id='a',source_id=source,url='https://'+next(s['host'] for s in n.SOURCES if s['id']==source)+'/release/a.html',published='2026-10-09',category='local',verified_source=True,title='街の新しい話題',summary='出典で確認した要点',detail='事実の詳細',link_only=False)
    r.update(kw);return r
class NewsTests(unittest.TestCase):
    def test_dated_groups_not_neighboring_link(self):
        body='<dt>10月10日付</dt><dd><a href="/mofaj/press/release/new.html">今日の報道発表</a></dd><dt>10月8日付</dt><dd><a href="/mofaj/press/release/old.html">前日の報道発表</a></dd>'
        data=n.html_candidates(body,n.SOURCES[2],TODAY)
        self.assertEqual([r['published'] for r in data],['2026-10-10','2026-10-08'])
    def test_rdf_exact_date_and_host(self):
        body='''<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/"><item><title>秋のスタンプラリー</title><link>https://www.pref.miyagi.jp/event/20261015.html</link><dc:date>2026-10-08T10:00:00+09:00</dc:date></item><item><title>秋のスタンプラリー</title><link>https://evil.example/</link><dc:date>2026-10-09T00:00:00+09:00</dc:date></item></rdf:RDF>'''
        data=n.rdf_candidates(body,n.SOURCES[1],TODAY)
        self.assertEqual(len(data),1);self.assertEqual(data[0]['published'],'2026-10-08')
        with self.assertRaises(ValueError):n.rdf_candidates('<!DOCTYPE a>'+body,n.SOURCES[1],TODAY)
    def test_url_scheme_credentials_port_and_suffix(self):
        for u in ('javascript:alert(1)','http://www.mofa.go.jp/a','https://www.mofa.go.jp.evil/a','https://user@www.mofa.go.jp/a','https://www.mofa.go.jp:9000/a'):
            self.assertFalse(n.safe_url(u,'www.mofa.go.jp'))
    def test_outage_preserves_recent_not_expired_or_care(self):
        old={'items':[row(),row(id='expired',published='2026-09-20'),row(id='care',category='care')]}
        out=n.combine(old,[('sendai',[],'timeout'),('miyagi',[],None),('mofa',[],None)],TODAY,NOW)
        self.assertEqual([x['id'] for x in out['items']],['a']);self.assertEqual(len(out['source_errors']),1)
        with self.assertRaises(ValueError):n.combine(old,[(s['id'],[],'timeout') for s in n.SOURCES],TODAY,NOW)
    def test_check_time_is_not_content_change(self):
        old={'items':[row()]};data=n.combine(old,[('sendai',[row()],None)],TODAY,NOW)
        self.assertEqual(data['new_count'],0)
        changed=n.combine(old,[('sendai',[row(summary='出典訂正で内容変更')],None)],TODAY,NOW)
        self.assertEqual(changed['new_count'],1)
    def test_changed_reviewed_source_falls_back_to_link(self):
        candidate=dict(title='秋の地域イベント',url='https://www.city.sendai.jp/event.html',category='local',published='2026-10-09')
        body='<h1>秋の地域イベント</h1><div id="tmp_contents"><p>日程を変更しました。</p>お問い合わせ</div>'
        reviewed={candidate['url']:dict(published=candidate['published'],body_sha256='old',evidence=['以前の日程'])}
        data=n.prepare(candidate,n.SOURCES[0],body,reviewed)
        self.assertTrue(data['link_only']);self.assertFalse(data['distribution_allowed']);self.assertNotIn('以前',data['summary'])
    def test_wrong_article_date_never_published_as_brief(self):
        c=dict(title='日米外相電話会談',url='https://www.mofa.go.jp/mofaj/press/release/x.html',category='world',published='2026-10-10')
        with self.assertRaises(ValueError):n.prepare(c,n.SOURCES[2],'<h1>日米外相電話会談</h1><div id="main">令和8年10月8日</div>',{})
    def test_atomic_data_and_published_registry(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'news.json';n.atomic_write(p,{'items':[]});self.assertEqual(json.loads(p.read_text()),{'items':[]});self.assertEqual(len(list(Path(folder).iterdir())),1)
        data=json.loads((n.ROOT/'data/news.json').read_text())
        self.assertEqual(data['mode'],'newspaper');self.assertLessEqual(len(data['items']),36)
        self.assertEqual(len(set(r['id'] for r in data['items'])),len(data['items']))
        for r in data['items']:
            self.assertIn(r['category'],n.CATEGORIES);self.assertTrue(r['verified_source']);self.assertNotIn('介護',r['title'])
            self.assertTrue(any(n.safe_url(r['url'],s['host']) and r['source_id']==s['id'] for s in n.SOURCES))
            if r['distribution_allowed']:self.assertEqual(r['source_id'],'mofa');self.assertEqual(r['distribution_policy_url'],n.POLICY);self.assertEqual(r['status'],'本文抜粋')
if __name__=='__main__':unittest.main()
