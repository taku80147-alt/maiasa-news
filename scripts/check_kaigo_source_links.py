"""Report exact-byte replacements for retired URLs; never accept a new hash."""
import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from collect_kaigo_documents import source_docs
from kaigo_evidence import fetch, extract_pdf, archive_source

DATA = Path(__file__).resolve().parent.parent / 'kaigo-navi2027-preview/data'


def main():
    articles = json.loads((DATA / 'explainers.json').read_text())['articles']
    cached = {}
    for article in articles:
        try:
            fetch(article['source_pdf'])
            continue
        except HTTPError as error:
            if error.code != 404:
                raise
        page = article['source_page']
        if page not in cached:
            cached[page] = []
            for row in source_docs({'source_url':page, 'date':article['meeting_date']}):
                raw = fetch(row['pdf_url'])
                extracted = extract_pdf(raw)
                archive_source('/tmp/kaigo-evidence', row['pdf_url'], raw, extracted)
                cached[page].append((row['pdf_url'], hashlib.sha256(raw).hexdigest()))
        matches = [url for url, sha in cached[page] if sha == article['pinned_pdf_sha256']]
        print('SOURCE_LINK_REPORT ' + json.dumps({'id':article['id'], 'retired':article['source_pdf'],
              'exact_hash_replacements':matches, 'candidates':cached[page]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
