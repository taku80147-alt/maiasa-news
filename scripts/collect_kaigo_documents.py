#!/usr/bin/env python3
"""Cost-free MHLW PDF ingestion for an editorial *review queue*.

Never makes policy assertions; never creates auto-published explanations.
Scans authoritative source pages, downloads *whole* PDF sources, records page
coverage and checksum, and flags unreadable/scanned sources for investigation.
"""
import datetime as dt
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
import fitz

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'kaigo-navi2027-preview'/'data'
NEWS=DATA/'latest.json'
QUEUE=DATA/'document-review-queue.json'
MAX_PDF=15*1024*1024
MAX_PER_RUN=4
MAX_QUEUED=45

def fetch(url,limit):
    parts=urllib.parse.urlparse(url)
    if parts.scheme!='https' or parts.hostname!='www.mhlw.go.jp':
        raise ValueError('MHLW HTTPS URL required')
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; KaigoNavi2027/1.0)'})
    with urllib.request.urlopen(req,timeout=40) as r: raw=r.read(limit+1)
    if len(raw)>limit:raise ValueError('Source exceeds limit')
    return raw

def source_docs(meeting):
    html=fetch(meeting['source_url'],2*1024*1024).decode('utf-8','replace')
    soup=BeautifulSoup(html,'html.parser')
    found=[]
    for link in soup.select('a[href]'):
        label=' '.join(link.get_text(' ',strip=True).split())
        url=urllib.parse.urljoin(meeting['source_url'],link.get('href'))
        parts=urllib.parse.urlparse(url)
        if parts.hostname!='www.mhlw.go.jp' or parts.scheme!='https' or not parts.path.lower().endswith('.pdf'):continue
        if not ('資料' in label or '参考資料' in label):continue
        found.append({'pdf_url':url,'label':label[:95],'meeting_date':meeting['date'],'meeting_url':meeting['source_url']})
    seen=set()
    return [x for x in found if not (x['pdf_url'] in seen or seen.add(x['pdf_url']))]

def inspect_pdf(data):
    if not data.startswith(b'%PDF-'):raise ValueError('not a PDF')
    pdf=fitz.open(stream=data,filetype='pdf')
    if not (0<len(pdf)<=250):raise ValueError('invalid page count')
    lengths=[]
    for page in pdf:
        content=page.get_text(sort=True)
        lengths.append(len(content))
    total=sum(lengths)
    coverage=sum(n>=80 for n in lengths)/len(lengths)
    if total<400 or coverage<.75:
        return {'status':'本文不足・要確認','pages':len(lengths),'chars':total,'readable_page_rate':round(coverage,2)}
    return {'status':'本文取得・解説未審査','pages':len(lengths),'chars':total,'readable_page_rate':round(coverage,2)}

def run():
    feed=json.loads(NEWS.read_text(encoding='utf-8'))['articles']
    meetings=[x for x in feed if x.get('source_url','').startswith('https://www.mhlw.go.jp/stf/') and x['id'].startswith('n-')]
    # Always process latest, plus pinned welfare-equipment policy pack.
    meetings=sorted(meetings,key=lambda x:x['date'],reverse=True)[:7]
    older=[x for x in feed if x['id']=='n-pay-259']
    for x in older:
        if all(q['id']!=x['id'] for q in meetings):meetings.append(x)
    existing=json.loads(QUEUE.read_text(encoding='utf-8')) if QUEUE.exists() else {'documents':[]}
    docs={x['pdf_url']:x for x in existing.get('documents',[])}
    candidates=[];errors=[]
    for meeting in meetings:
        try:
            candidates.extend(source_docs(meeting))
        except Exception as e:errors.append({'meeting':meeting['id'],'message':type(e).__name__})
    if not candidates:raise RuntimeError('No official PDF links discovered; preserve prior queue')
    new=[d for d in candidates if d['pdf_url'] not in docs]
    print('Found',len(candidates),'PDF links; unprocessed',len(new))
    processed=0
    for item in new[:MAX_PER_RUN]:
        try:
            raw=fetch(item['pdf_url'],MAX_PDF)
            metrics=inspect_pdf(raw)
            docs[item['pdf_url']]={**item,**metrics,'sha256':hashlib.sha256(raw).hexdigest(),
                                   'checked_at':dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')}
        except Exception as e:
            # Keep retriable errors out of the queue; never misreport as verified.
            errors.append({'pdf_url':item['pdf_url'],'message':type(e).__name__})
            continue
        processed+=1
    output={'schema_version':1,'disclaimer':'本文取得は解説の正確さを意味しません。原文の読込・確認待ちリストです。',
            'documents':sorted(docs.values(),key=lambda x:(x['meeting_date'],x['pdf_url']),reverse=True)[:MAX_QUEUED]}
    if output['documents']!=existing.get('documents',[]):
        QUEUE.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Processed',processed,'docs. Queue',len(output['documents']),'Errors',errors[:8])
    if processed==0 and not docs:raise RuntimeError('Nothing retrieved; no queue produced')

if __name__=='__main__':run()
