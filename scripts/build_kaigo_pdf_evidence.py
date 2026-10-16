#!/usr/bin/env python3
"""Build bounded, source-linked MHLW PDF reading aids; NOT approved legal interpretations.

Only extracts headings from pages explicitly marked 対応案 and optionally short
same-page sentences. It never infers reimbursement figures, legal effect or dates.
Files are pinned to the official SHA256 recorded by the full PDF collector.
"""
import datetime as dt
import hashlib
import json
import re
import os
from pathlib import Path

import fitz
from kaigo_evidence import fetch, official_url

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'kaigo-navi2027-preview' / 'data'
NEWS = DATA / 'latest.json'
QUEUE = DATA / 'document-review-queue.json'
OUTPUT = DATA / 'pdf-evidence.json'
MAX_NEW_DOCUMENTS = 5
MAX_ITEMS_PER_DOC = 5
MAX_READING_PAGES = 240
EXTRACTOR_VERSION = 3

def norm(s):
    return re.sub(r'\s+', '', s).replace('　','').strip()

def headings_from_page(text, page_number):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    indices = [i for i, line in enumerate(lines) if norm(line) in ('対応案','＜対応案＞','【対応案】') or (norm(line).endswith('対応案') and len(norm(line))<=12)]
    if not indices: return []
    result=[]
    def original_sentence(i):
        for ix in range(i,min(len(lines),i+9)):
            if not lines[ix].startswith(('◼','■','●','○','・')):continue
            parts=[re.sub(r'^[◼■●○・]\\s*','',lines[ix])]
            for line in lines[ix+1:ix+6]:
                if line.startswith(('◼','■','●','○','論点','対応案')):break
                parts.append(line)
                if '。' in line:break
            sentence=''.join(parts).split('。')[0].strip()+'。'
            if 25<=len(sentence)<=170 and norm(sentence[:-1]) in norm(text):
                return sentence
            return ''
        return ''
    for start in indices:
        found=0
        for i in range(start+1,min(len(lines),start+36)):
            line=lines[i]
            if line.startswith(('論点','参考資料','参考文献')) and i>start+3: break
            match=re.fullmatch(r'[（(]([^()（）]{4,44})[）)]',line)
            if not match:continue
            topic=match.group(1).strip()
            if '改定' in topic and '令和' in topic:continue
            result.append({'heading':topic,'pdf_page':page_number,
                           'evidence':original_sentence(i+1)})
            found+=1
            if len(result)>=MAX_ITEMS_PER_DOC:return result
        if found:continue
        # Some official PDFs put a direct proposal under 論点① without a parenthesized subheading.
        near=lines[max(0,start-6):start]
        options=[re.sub(r'^論点[①-⑳0-9]+\\s*','',line).strip() for line in near
                 if re.match(r'^論点[①-⑳0-9]+\\s*\\S',line) and '・・・' not in line]
        topic=options[-1] if options else ''
        if not (5<=len(topic)<=60):
            topic='このページの対応案（本文の確認が必要）'
        if 5<=len(topic)<=60:
            result.append({'heading':topic,'pdf_page':page_number,
                           'evidence':original_sentence(start+1)})
            if len(result)>=MAX_ITEMS_PER_DOC:return result
    unique={}
    for item in result:unique.setdefault(item['heading'],item)
    return list(unique.values())[:MAX_ITEMS_PER_DOC]

def source_for_article(article,documents):
    linked=[]
    for d in documents:
        if d.get('meeting_url')!=article['source_url']:continue
        if d.get('meeting_date')!=article['date']:continue
        label=d.get('label','')
        if not re.search(r'(【資料\s*[０-９0-9]+】|資料[１-９0-9])',label):continue
        if d.get('status')!='本文取得・解説未審査':continue
        if d.get('readable_page_rate',0)<.75:continue
        if not re.fullmatch(r'[0-9a-f]{64}',d.get('sha256','')):continue
        try:
            official_url(d['pdf_url'])
        except ValueError:
            continue
        linked.append(d)
    def material_order(row):
        label=row.get('label','').translate(str.maketrans('０１２３４５６７８９','0123456789'))
        match=re.search(r'資料\s*(\d+)',label)
        return (int(match.group(1)) if match else 99,row.get('pdf_url',''))
    return sorted(linked,key=material_order)

def inspect_document(doc):
    raw=fetch(doc['pdf_url'],limit=15*1024*1024)
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=doc['sha256']:
        raise ValueError('MHLW PDF changed since collection; do not publish unverified extracts: '+doc['pdf_url'])
    if not raw.startswith(b'%PDF-'):raise ValueError('Official source response not PDF')
    items=[]; pages_seen=0; readable=0
    with fitz.open(stream=raw,filetype='pdf') as pdf:
        if pdf.is_encrypted or not 0<len(pdf)<=300:
            raise ValueError('Invalid PDF page count')
        pages_seen=len(pdf)
        for number,page in enumerate(pdf,1):
            if number>MAX_READING_PAGES:break
            raw_page=page.get_text(sort=True)
            if len(raw_page.strip())>=120:readable+=1
            if '対応案' not in raw_page:continue
            items.extend(headings_from_page(raw_page,number))
            if len(items)>=MAX_ITEMS_PER_DOC:break
    if not pages_seen or readable==0:raise ValueError('Unreadable source document')
    return {
        'pdf_url':doc['pdf_url'],'pdf_sha256':digest,'label':doc['label'],
        'extractor_version':EXTRACTOR_VERSION,
        'pdf_pages':pages_seen,'checked_at':dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d'),
        'topics':items[:MAX_ITEMS_PER_DOC]
    }

def build():
    feed=json.loads(NEWS.read_text(encoding='utf-8'))
    queue=json.loads(QUEUE.read_text(encoding='utf-8'))
    old=json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else {'articles':[]}
    known={}
    for row in old.get('articles',[]):
        for d in row.get('documents',[]):
            if d.get('extractor_version')==EXTRACTOR_VERSION:
                known[(d.get('pdf_url'),d.get('pdf_sha256'))]=d
    articles=[]
    read=0
    eligible=[a for a in feed['articles'] if re.fullmatch(r'n-(pay|ins|econ)-[0-9]+',a['id']) and
              a['source_url'].startswith('https://www.mhlw.go.jp/stf/')]
    eligible=sorted(eligible,key=lambda a:a['date'],reverse=True)[:8]
    for a in eligible:
        docs=[]; warnings=[]
        for source in source_for_article(a,queue['documents'])[:6]:
            key=source['pdf_url'],source['sha256']
            if key in known:
                docs.append(known[key])
                continue
            if read>=MAX_NEW_DOCUMENTS:
                warnings.append('資料の本文解析は次回に繰り越し')
                continue
            try:
                newdoc=inspect_document(source)
                docs.append(newdoc)
            except Exception as err:
                warnings.append(source['label']+'：'+type(err).__name__)
                print('WARNING PDF',source['pdf_url'],err,flush=True)
                # Changed / invalid official sources require a fresh editorial review.
                if isinstance(err,ValueError) and 'changed' in str(err):
                    raise
            read+=1
        if not docs:continue
        articles.append({
            'id':a['id'],'meeting_date':a['date'],'source_url':a['source_url'],
            'status':'公式資料の「対応案」見出しを機械抽出（未審査）',
            'scope':'資料にある検討項目を探しやすくしたものです。新制度の決定・適用条件・数値を保証する解説ではありません。',
            'documents':docs,'warnings':warnings})
    if not articles:
        raise RuntimeError('No PDF evidence available; keep last published version')
    output={'schema_version':1,'source_type':'厚生労働省・原文PDF',
      'disclaimer':'PDFの対応案見出しを機械抽出。資料全文の理解・法的な適用判断は人による確認が必要です。',
      'articles':articles}
    payload=json.dumps(output,ensure_ascii=False,indent=2)+'\n'
    if not OUTPUT.exists() or payload!=OUTPUT.read_text(encoding='utf-8'):
        temporary=OUTPUT.with_suffix('.tmp')
        temporary.write_text(payload,encoding='utf-8')
        os.replace(temporary,OUTPUT)
    print('PDF brief articles',len(articles),'fresh PDF reads',read,
          'subjects',sum(len(doc['topics']) for a in articles for doc in a['documents']))
if __name__=='__main__': build()
