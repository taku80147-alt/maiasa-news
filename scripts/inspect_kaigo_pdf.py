#!/usr/bin/env python3
"""One-shot audit log of full official PDFs for editorial reading. Never publishes articles."""
import re
import urllib.request
import fitz
SOURCES={
 "nursing_multifunction":"https://www.mhlw.go.jp/content/12300000/001758325.pdf",
 "scheduled_night_visit":"https://www.mhlw.go.jp/content/12300000/001758324.pdf",
}
for name,url in SOURCES.items():
 print("============== SOURCE",name,url,"==============")
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
 with urllib.request.urlopen(req,timeout=45) as res: content=res.read(14_000_000)
 doc=fitz.open(stream=content,filetype="pdf")
 print("PDF_PAGES",len(doc))
 for i,p in enumerate(doc):
  raw=p.get_text(sort=True)
  normalized=re.sub(r"\s+"," ",raw).strip()
  print("=== ",name,"PDF_PAGE",i+1,"CHARS",len(raw)," ===")
  # Read each complete page in the logs for source-specific human review.
  print(raw[:6800].replace("\x00",""))
  if len(raw)>6800:print("...[PAGE TEXT TRUNCATED, require further review]")
