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
import os
from kaigo_evidence import fetch as official_fetch, extract_pdf, archive_source

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
    return official_fetch(url,limit)

def source_docs(meeting):
    if urllib.parse.urlparse(meeting['source_url']).path.lower().endswith('.pdf'):
        return [{'pdf_url':meeting['source_url'],'label':meeting['title'],'meeting_date':meeting['date'],'meeting_url':meeting['source_url']}]
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
    extracted=extract_pdf(data)
    lengths=[len(page['text']) for page in extracted['pages']]
    total=sum(lengths)
    coverage=sum(n>=80 for n in lengths)/len(lengths)
    status='本文不足・要確認' if total<400 or coverage<.75 else '本文取得・解説未審査'
    return {'status':status,'pages':len(lengths),'chars':total,'readable_page_rate':round(coverage,2),
            'tables_extracted':sum(len(p['tables']) for p in extracted['pages']),
            'notes_and_exceptions_candidates':sum(len(p['notes_and_exceptions']) for p in extracted['pages'])},extracted

def reconcile_sources(documents,candidates):
    """Retain provenance, but never treat superseded official links as active sources."""
    current={}
    for item in candidates:
        current.setdefault(item['meeting_url'],set()).add(item['pdf_url'])
    result={url:dict(row) for url,row in documents.items()}
    for url,row in result.items():
        linked=current.get(row.get('meeting_url'))
        if linked is not None and url not in linked:
            row['status']='公式掲載URL変更・要再確認'
    return result

def run():
    feed=json.loads(NEWS.read_text(encoding='utf-8'))['articles']
    meetings=[x for x in feed if x.get('source_url','').startswith('https://www.mhlw.go.jp/stf/') and x['id'].startswith('n-')]
    # Always process latest, plus pinned welfare-equipment policy pack.
    meetings=sorted(meetings,key=lambda x:x['date'],reverse=True)[:7]
    older=[x for x in feed if x['id']=='n-pay-259']
    for x in older:
        if all(q['id']!=x['id'] for q in meetings):meetings.append(x)
    for item in feed:
        if item.get('source_kind')=='notice' and all(q['id']!=item['id'] for q in meetings):meetings.append(item)
    existing=json.loads(QUEUE.read_text(encoding='utf-8')) if QUEUE.exists() else {'documents':[]}
    docs={x['pdf_url']:x for x in existing.get('documents',[])}
    candidates=[];errors=[]
    for meeting in meetings:
        try:
            candidates.extend(source_docs(meeting))
        except Exception as e:errors.append({'meeting':meeting['id'],'message':type(e).__name__})
    if not candidates:raise RuntimeError('No official PDF links discovered; preserve prior queue')
    docs=reconcile_sources(docs,candidates)
    new=[d for d in candidates if d['pdf_url'] not in docs or
         docs[d['pdf_url']].get('status')=='公式掲載URL変更・要再確認']
    print('Found',len(candidates),'PDF links; unprocessed',len(new))
    processed=0
    for item in new[:MAX_PER_RUN]:
        try:
            raw=fetch(item['pdf_url'],MAX_PDF)
            metrics,extracted=inspect_pdf(raw)
            archive_source(os.environ.get('KAIGO_EVIDENCE_DIR',str(ROOT/'.kaigo-evidence')),item['pdf_url'],raw,extracted)
            docs[item['pdf_url']]={**item,**metrics,'sha256':hashlib.sha256(raw).hexdigest(),
                                   'checked_at':dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')}
        except Exception as e:
            # Keep retriable errors out of the queue; never misreport as verified.
            errors.append({'pdf_url':item['pdf_url'],'message':type(e).__name__})
            continue
        processed+=1
    if errors:
        raise RuntimeError('Official document collection incomplete; preserve prior queue: '+json.dumps(errors,ensure_ascii=False))
    output={'schema_version':1,'disclaimer':'本文取得は解説の正確さを意味しません。原文の読込・確認待ちリストです。',
            'documents':sorted(docs.values(),key=lambda x:(x['meeting_date'],x['pdf_url']),reverse=True)}
    if output['documents']!=existing.get('documents',[]):
        QUEUE.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Processed',processed,'docs. Queue',len(output['documents']),'Errors',errors[:8])
    if processed==0 and not docs:raise RuntimeError('Nothing retrieved; no queue produced')

if __name__=='__main__':run()


