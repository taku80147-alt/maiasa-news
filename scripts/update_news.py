#!/usr/bin/env python3
"""Free newspaper: official releases, reviewed factual briefs, publisher entrances.
No paid inference, no media RSS republication, no guesses from headlines.
"""
from __future__ import annotations
import hashlib, html, json, os, re, sys, tempfile
import urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = ('national','world','economy','local','life','sports','culture','business')
SOURCES = (
 {'id':'sendai','name':'仙台市','host':'www.city.sendai.jp','url':'https://www.city.sendai.jp/shinchaku/shinchaku.xml','kind':'rdf'},
 {'id':'miyagi','name':'宮城県','host':'www.pref.miyagi.jp','url':'https://www.pref.miyagi.jp/release/release.xml','kind':'rdf'},
 {'id':'mofa','name':'外務省','host':'www.mofa.go.jp','url':'https://www.mofa.go.jp/mofaj/press/release/index.html','kind':'html'},
)
POLICY = 'https://www.mofa.go.jp/mofaj/annai/legalmatters/index.html'

def safe_url(url, host):
    try:
        p = urllib.parse.urlsplit(url)
        return p.scheme == 'https' and p.hostname == host and not p.username and not p.password and p.port in (None,443)
    except ValueError: return False

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl, urllib.parse.urlsplit(req.full_url).hostname):
            raise ValueError('Unapproved redirect')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def get(url,host):
    if not safe_url(url,host): raise ValueError('Unapproved source URL')
    req=urllib.request.Request(url,headers={'User-Agent':'MaiasaNews/2.0 (+official-source monitor)','Accept-Language':'ja'})
    with urllib.request.build_opener(Redirect()).open(req,timeout=20) as response:
        if not safe_url(response.url,host): raise ValueError('Unapproved response host')
        if 'pdf' in response.headers.get_content_type(): raise ValueError('HTML required')
        raw=response.read(2_000_001)
        if len(raw)>2_000_000: raise ValueError('Oversized source')
        return raw.decode(response.headers.get_content_charset() or 'utf-8',errors='strict')

def clean(s):
    s=re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>',' ',s,flags=re.I|re.S)
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()

def scope(body, source_id):
    ids = 'main' if source_id == 'mofa' else 'tmp_contents'
    match=re.search(r'<(?:div|main)\b[^>]*\bid=["\']'+ids+r'["\'][^>]*>',body,re.I)
    if not match: raise ValueError('Main article body missing')
    text=clean(body[match.end():])
    stop='関連リンク' if source_id=='mofa' else 'お問い合わせ'
    return text.split(stop,1)[0].strip()

def fresh(published,today):
    try: d=date.fromisoformat(published)
    except (TypeError,ValueError): return False
    return today-timedelta(days=7)<=d<=today

def classify(title, source_id):
    if any(k in title for k in ('介護','福祉用具','介護報酬','高齢者施設')):return None
    if source_id=='mofa':return 'economy' if any(k in title for k in ('経済','貿易','投資','EPA')) else 'world'
    if any(k in title for k in ('審議会','審査会','委員会','入札','人事','採用','職員','公募型','プロポーザル','評価部会','記者会見')):return None
    if any(k in title for k in ('スポーツ','スポGOMI','ベガルタ','楽天','野球')):return 'sports'
    if any(k in title for k in ('スタンプラリー','トリップ','博物館','美術','音楽','コンサート','祭','観光')):return 'culture'
    if any(k in title for k in ('マルシェ','販売会','食品','防犯','安全運動','交通','暮らし','防災','災害','食中毒')):return 'life'
    if any(k in title for k in ('企業','経済','産業','物価','賃金')):return 'economy'
    return 'local'

def rdf_candidates(body,source,today):
    if re.search(r'<!DOCTYPE|<!ENTITY',body,re.I):raise ValueError('Unsafe XML')
    root=ET.fromstring(body);rows=[]
    for item in root.iter():
        if item.tag.rsplit('}',1)[-1]!='item':continue
        f={child.tag.rsplit('}',1)[-1]:(child.text or '').strip() for child in item}
        stamp=f.get('date','')
        try:published=datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(JST).date().isoformat()
        except ValueError:continue
        title=f.get('title','');url=f.get('link','');cat=classify(title,source['id'])
        if cat and 6<=len(title)<=150 and fresh(published,today) and safe_url(url,source['host']) and not url.lower().endswith('.pdf'):
            rows.append({'title':title,'url':url,'published':published,'category':cat})
    return rows[:18]

def html_candidates(body,source,today):
    rows=[]
    # Dated dt/dd groups: never associate a neighboring story's date with a link.
    for group in re.finditer(r'<dt\b[^>]*>(.*?)</dt>\s*<dd\b[^>]*>(.*?)</dd>',body,re.I|re.S):
        stamp=re.search(r'(\d{1,2})月(\d{1,2})日付',clean(group.group(1)))
        if not stamp:continue
        month,day=map(int,stamp.groups());year=today.year-(1 if month>today.month else 0)
        try:published=date(year,month,day).isoformat()
        except ValueError:continue
        if not fresh(published,today):continue
        for href,title in re.findall(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',group.group(2),re.I|re.S):
            url=urllib.parse.urljoin(source['url'],html.unescape(href));title=clean(title)
            if safe_url(url,source['host']) and '/mofaj/press/release/' in url and url.endswith('.html') and len(title)>=6:
                rows.append({'title':title,'url':url,'published':published,'category':classify(title,source['id'])})
    return rows[:8]

def prepare(candidate,source,body,reviewed):
    text=scope(body,source['id']);title=candidate['title']
    headings=[clean(x) for x in re.findall(r'<h[12]\b[^>]*>(.*?)</h[12]>',body,re.I|re.S)]
    reviewed_article=reviewed.get(candidate['url'])
    reviewed_matches=bool(reviewed_article and reviewed_article['published']==candidate['published'] and reviewed_article['body_sha256']==hashlib.sha256(text.encode()).hexdigest() and all(clean(q) in text for q in reviewed_article['evidence']))
    if not reviewed_matches and not any(title in h or h in title for h in headings if len(h)>5):raise ValueError('Article title mismatch')
    row=dict(candidate,id=hashlib.sha256(candidate['url'].encode()).hexdigest()[:16],source=source['name'],source_id=source['id'],source_type='official',primary=True,verified_source=True,date_label='掲載・更新',summary='',detail='',key_points=[],link_only=True,status='見出し',distribution_allowed=False,distribution_policy_url='',distribution_note='出典のページで本文を読めます。',fact_note='掲載・更新日は情報源の配信日時です。開催日とは異なります。',body_sha256=hashlib.sha256(text.encode()).hexdigest())
    review=reviewed.get(candidate['url'])
    if review and review['published']==row['published'] and review['body_sha256']==row['body_sha256'] and all(clean(q) in text for q in review['evidence']):
        row.update(title=review['title'],category=review['category'],summary=review['summary'],detail=review['detail'],link_only=False,status='要点',editorial=True,distribution_note='毎朝ニュースが出典の事実を整理した独自の要点です。配布資料の選択対象外。')
    elif source['id']=='mofa':
        era=re.search(r'令和\s*(\d+)年\s*(\d+)月\s*(\d+)日',text)
        if not era or date(2018+int(era[1]),int(era[2]),int(era[3])).isoformat()!=row['published']:
            raise ValueError('Publication date mismatch')
        # Copy only first-party press release prose, never third-party statements/photos.
        article_html=body[re.search(r'<(?:div|main)\b[^>]*\bid=["\']main["\'][^>]*>',body,re.I).end():].split('relatedlink-section',1)[0]
        paragraphs=[clean(p) for p in re.findall(r'<(?:p|li)\b[^>]*>(.*?)</(?:p|li)>',article_html,re.I|re.S)]
        paragraphs=[p for p in paragraphs if 45<=len(p)<=600 and p in text and '。' in p and not any(k in p for k in ('Image','メール','お問い合わせ','サイト','ウェブ','出典','転載'))]
        if paragraphs and not any(k in title for k in ('共同声明','共同宣言','談話')):
            overview=' '.join(paragraphs[:2]); overview=overview[:380]
            if len(' '.join(paragraphs[:2]))>380:overview=overview.rsplit('。',1)[0]+'。'
            row.update(summary=overview,detail='\n\n'.join(paragraphs[:4]),link_only=False,status='本文抜粋',date_label='発表',distribution_allowed=True,distribution_policy_url=POLICY,distribution_note='出典：外務省。公式本文の抜粋を毎朝ニュースが編集。画像・第三者の声明は含みません。',fact_note='発表元による説明です。報道機関の独立した評価とは異なります。')
    if row['link_only']:row['summary']='本文は出典のページで読めます。掲載・更新日と開催日を分けてご確認ください。'
    return row

def combine(old,results,today,now):
    rows={};errors=[];ok=0
    for source_id,new_rows,error in results:
        if error:
            errors.append({'source':source_id,'message':'取得できなかったため、確認済みの記事を保持しています。'})
            for row in old.get('items',[]):
                if row.get('source_id')==source_id and fresh(row.get('published'),today) and row.get('category') in CATEGORIES and row.get('verified_source') and any(s['id']==source_id and safe_url(row.get('url',''),s['host']) for s in SOURCES):rows[row['id']]=row
        if not error or new_rows:ok+=1
        for row in new_rows:rows[row['id']]=row
    if not ok:raise ValueError('All sources failed: keeping previous file')
    items=sorted(rows.values(),key=lambda r:(r['published'],not r['link_only']),reverse=True)[:36]
    previous={r['id']:hashlib.sha256(json.dumps({k:r.get(k) for k in ('title','summary','detail','published')},ensure_ascii=False,sort_keys=True).encode()).hexdigest() for r in old.get('items',[])}
    new_count=sum(previous.get(r['id'])!=hashlib.sha256(json.dumps({k:r.get(k) for k in ('title','summary','detail','published')},ensure_ascii=False,sort_keys=True).encode()).hexdigest() for r in items)
    # A local factual brief leads, then international, then a different useful local topic.
    leads=[]
    for cat in (('local','life'),('world','national','economy'),('culture','sports','business')):
        found=next((r for r in items if r['category'] in cat and not r['link_only'] and r['id'] not in leads),None)
        if found:leads.append(found['id'])
    for row in items:
        if len(leads)>=3:break
        if row['id'] not in leads:leads.append(row['id'])
    return {'schema_version':2,'mode':'newspaper','updated_at':now.isoformat(),'updated_label':now.strftime('%m/%d %H:%M'),'latest_article_date':max((r['published'] for r in items),default=''),'new_count':new_count,'important_ids':leads,'items':items,'source_errors':errors,'source_count':ok,'window_days':7}

def collect(source,today,reviewed):
    try:
        body=get(source['url'],source['host'])
        candidates=(rdf_candidates if source['kind']=='rdf' else html_candidates)(body,source,today)
        rows=[];failures=[]
        def article(candidate):
            try:return prepare(candidate,source,get(candidate['url'],source['host']),reviewed),None
            except ValueError as error:
                # Listing entries may point to an index or have a different page title.
                # These are not verified articles; exclude them without fabricating a brief.
                print(source['id']+': excluded '+candidate['url']+' ('+str(error)+')',file=sys.stderr)
                return None,None
            except Exception as error:return None,str(error)
        with ThreadPoolExecutor(max_workers=2) as pool:
            for row,error in pool.map(article,candidates):
                if row:rows.append(row)
                if error:failures.append(error)
        if candidates and not rows:raise ValueError('No individually verified article available')
        return source['id'],rows,('; '.join(failures) if failures else None)
    except Exception as error:
        print(source['id']+': '+str(error),file=sys.stderr)
        return source['id'],[],str(error)

def atomic_write(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(payload,ensure_ascii=False,indent=2)+'\n'
    with tempfile.NamedTemporaryFile('w',dir=path.parent,encoding='utf-8',delete=False) as f:
        f.write(content);temp=f.name
    try:os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def main():
    target=ROOT/'data/news.json'; old=json.loads(target.read_text()) if target.exists() else {}
    reviewed={x['url']:x for x in json.loads((ROOT/'data/news-reviewed.json').read_text())}
    now=datetime.now(JST)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda source:collect(source,now.date(),reviewed),SOURCES))
    payload=combine(old,results,now.date(),now)
    atomic_write(target,payload)
    print(f"Newspaper: {len(payload['items'])} articles; {payload['new_count']} new/changed; {len(payload['source_errors'])} unavailable sources")
if __name__=='__main__':main()
