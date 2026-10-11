#!/usr/bin/env python3
"""Validate source-backed explainers against full original PDFs.

Fail closed: only write an approved release when every PDF is fully readable
and each page-specific evidence anchor can be located. This does NOT claim
AI can infer legislation safely without human/editorial verification.
"""
import datetime as dt
import hashlib
import json
import re
import urllib.request
import unicodedata
from pathlib import Path

from kaigo_evidence import extract_pdf, fetch, archive_source, article_hash
import os

ROOT=Path(__file__).resolve().parent.parent
DIR=ROOT/"kaigo-navi2027-preview"/"data"
DRAFT=DIR/"explainers.json"
APPROVED=DIR/"explainers-verified.json"
MAX_DOWNLOAD=25*1024*1024

def text_norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s)).lower()

def retrieve_pdf(url):
    if not url.startswith("https://www.mhlw.go.jp/content/") or not url.endswith(".pdf"):
        raise ValueError("URL must be an MHLW PDF")
    return fetch(url)

def examine(article, pdf_bytes, extracted=None):
    digest=hashlib.sha256(pdf_bytes).hexdigest()
    if not re.fullmatch(r'[0-9a-f]{64}', article.get('pinned_pdf_sha256', '')):
        raise ValueError('Editorially pinned PDF hash required')
    if digest!=article['pinned_pdf_sha256']:
        raise ValueError('Official source PDF changed since editorial review: '+article['id'])
    extracted = extracted or extract_pdf(pdf_bytes)
    pages=[page['text'] for page in extracted['pages']]
    if not article.get('verified_claims'):
        raise ValueError('Evidence claims required')
    if article.get('status_kind') not in ('proposal','current','mixed','enacted'):
        raise ValueError('Explicit legal status required')
    if not pages or sum(len(p) for p in pages)<700:
        raise ValueError("Source PDF text is incomplete; manual review required")
    if len(pages)>300: raise ValueError("Too many PDF pages")
    readable=sum(len(page.strip())>=150 for page in pages)
    if len(pages)>3 and readable/len(pages)<0.75:
        raise ValueError('Fewer than 75% of PDF pages have extractable text; manual PDF review required')
    results=[]
    for claim in article["verified_claims"]:
        page_idx=claim["pdf_page"]-1
        if page_idx<0 or page_idx>=len(pages):
            raise ValueError("Invalid page index: "+str(page_idx+1))
        anchor=text_norm(claim["anchor"])
        if len(anchor)<3 or anchor not in text_norm(pages[page_idx]):
            raise ValueError("Source evidence NOT found: page "+str(page_idx+1)+" / "+claim["anchor"])
        results.append({"claim":claim["claim"],"pdf_page":page_idx+1,"anchor":claim["anchor"],"status":"located"})

    numerics=[]
    for numeric in article.get("numeric_evidence", []):
        page_idx=numeric["pdf_page"]-1
        if not (0<=page_idx<len(pages)): raise ValueError("Invalid numerical PDF page")
        literal=text_norm(numeric["literal"])
        if len(literal)<2 or literal not in text_norm(pages[page_idx]):
            raise ValueError("Numerical evidence NOT located: "+article["id"]+" page "+str(page_idx+1)+" "+numeric["literal"])
        if not numeric.get("scope"):raise ValueError("Missing time/population scope for numeric evidence")
        numerics.append({"pdf_page":page_idx+1,"literal":numeric["literal"],"scope":numeric["scope"],"status":"located"})
    return {"id":article["id"],"source_pdf":article["source_pdf"],
            "sha256":hashlib.sha256(pdf_bytes).hexdigest(),
            "pdf_pages_read":len(pages),"characters_read":sum(len(p) for p in pages),
            "evidence_checks":results,"numeric_checks":numerics,
            "readable_page_rate":round(readable/len(pages),3),
            "article_sha256":article_hash(article),
            "tables_extracted":sum(len(p['tables']) for p in extracted['pages']),
            "notes_and_exceptions_candidates":sum(len(p['notes_and_exceptions']) for p in extracted['pages']),
            "pages_requiring_visual_review":[p['pdf_page'] for p in extracted['pages'] if p['review_required']],
            "table_verification":"Extraction candidates only; semantic review remains editorial"}

def build():
    data=json.loads(DRAFT.read_text(encoding="utf-8"))
    articles=data.get("articles")
    if not isinstance(articles,list) or len(articles)<2: raise ValueError("Need at least two curated articles")
    if len({a["id"] for a in articles})!=len(articles): raise ValueError("Duplicate article ids")
    reports=[]
    sources={}
    evidence_dir=os.environ.get("KAIGO_EVIDENCE_DIR",str(ROOT/".kaigo-evidence"))
    for article in articles:
        if not (article.get("one_liner") and article.get("quick") and article.get("explain") and article.get("sales")):
            raise ValueError("Missing reader or sales layer: "+article["id"])
        url=article["source_pdf"]
        if url not in sources:
            pdf=retrieve_pdf(url)
            extracted=extract_pdf(pdf)
            archive_source(evidence_dir,url,pdf,extracted)
            sources[url]=(pdf,extracted)
        pdf,extracted=sources[url]
        result=examine(article,pdf,extracted)
        reports.append(result)
        print("Verified source",article["id"],"pages",result["pdf_pages_read"],"chars",result["characters_read"])
    approved={**data,"source_verified_at":dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
              "verification_scope":"All PDF pages, table candidates and exception-note candidates extracted; originals archived in CI. Pinned PDF hashes, page anchors, numeric literals and article hashes checked. Text coverage >=75% for multi-page files. Scope and legal meaning are editorial, not automatically certified.",
              "source_audits":reports}
    output=json.dumps(approved,ensure_ascii=False,indent=2)+"\n"
    if APPROVED.exists():
        old=json.loads(APPROVED.read_text(encoding="utf-8"))
        # Keep stable date if PDFs and curated article content have not changed.
        old_compare={k:v for k,v in old.items() if k not in ("source_verified_at",)}
        new_compare={k:v for k,v in approved.items() if k not in ("source_verified_at",)}
        if old_compare==new_compare:
            print("Verified sources unchanged");return
    temp=APPROVED.with_suffix(".tmp")
    temp.write_text(output,encoding="utf-8")
    temp.replace(APPROVED)
    print("Published verified curation JSON")

if __name__=="__main__":
    build()

