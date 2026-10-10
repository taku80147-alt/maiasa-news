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
from pathlib import Path

import fitz

ROOT=Path(__file__).resolve().parent.parent
DIR=ROOT/"kaigo-navi2027-preview"/"data"
DRAFT=DIR/"explainers.json"
APPROVED=DIR/"explainers-verified.json"
MAX_DOWNLOAD=25*1024*1024

def text_norm(s):
    return re.sub(r"\s+", "", s).translate(str.maketrans("％（）", "%()")).lower()

def retrieve_pdf(url):
    if not url.startswith("https://www.mhlw.go.jp/content/") or not url.endswith(".pdf"):
        raise ValueError("URL must be an MHLW PDF")
    request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; KaigoNavi2027/1.0)"})
    with urllib.request.urlopen(request,timeout=35) as response:
        buf=response.read(MAX_DOWNLOAD+1)
    if len(buf)>MAX_DOWNLOAD: raise ValueError("PDF exceeds 25 MiB limit")
    if not buf.startswith(b"%PDF-"): raise ValueError("Response is not a PDF")
    return buf

def examine(article, pdf_bytes):
    digest=hashlib.sha256(pdf_bytes).hexdigest()
    if article.get('pinned_pdf_sha256') and digest!=article['pinned_pdf_sha256']:
        raise ValueError('Official source PDF changed since editorial review: '+article['id'])
    doc=fitz.open(stream=pdf_bytes,filetype="pdf")
    pages=[page.get_text(sort=True) for page in doc]
    if not pages or sum(len(p) for p in pages)<700:
        raise ValueError("Source PDF text is incomplete; manual review required")
    if len(pages)>300: raise ValueError("Too many PDF pages")
    results=[]
    for claim in article["verified_claims"]:
        page_idx=claim["pdf_page"]-1
        if page_idx<0 or page_idx>=len(pages):
            raise ValueError("Invalid page index: "+str(page_idx+1))
        anchor=text_norm(claim["anchor"])
        if len(anchor)<3 or anchor not in text_norm(pages[page_idx]):
            raise ValueError("Source evidence NOT found: page "+str(page_idx+1)+" / "+claim["anchor"])
        results.append({"claim":claim["claim"],"pdf_page":page_idx+1,"anchor":claim["anchor"],"status":"located"})
    return {"id":article["id"],"source_pdf":article["source_pdf"],
            "sha256":hashlib.sha256(pdf_bytes).hexdigest(),
            "pdf_pages_read":len(pages),"characters_read":sum(len(p) for p in pages),
            "evidence_checks":results}

def build():
    data=json.loads(DRAFT.read_text(encoding="utf-8"))
    articles=data.get("articles")
    if not isinstance(articles,list) or len(articles)<2: raise ValueError("Need at least two curated articles")
    if len({a["id"] for a in articles})!=len(articles): raise ValueError("Duplicate article ids")
    reports=[]
    for article in articles:
        if not (article.get("one_liner") and article.get("quick") and article.get("explain") and article.get("sales")):
            raise ValueError("Missing reader or sales layer: "+article["id"])
        pdf=retrieve_pdf(article["source_pdf"])
        result=examine(article,pdf)
        reports.append(result)
        print("Verified source",article["id"],"pages",result["pdf_pages_read"],"chars",result["characters_read"])
    approved={**data,"source_verified_at":dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
              "verification_scope":"All PDF pages readable and all declared evidence page-anchors matched. Editorial interpretations remain human/AI-reviewed separately, not mechanically proven.",
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
