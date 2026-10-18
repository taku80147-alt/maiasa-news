"""Bounded official-source retrieval and page/table extraction (no inference)."""
import hashlib
import json
import re
import urllib.parse
import urllib.request
import urllib.error
import socket
import time
from pathlib import Path

import fitz

MAX_PDF = 25 * 1024 * 1024
MAX_PAGES = 300


def official_url(url):
    p = urllib.parse.urlsplit(url)
    if (p.scheme != 'https' or p.hostname != 'www.mhlw.go.jp' or
            p.username or p.password or p.port not in (None, 443)):
        raise ValueError('MHLW HTTPS URL required')
    return url


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url, limit=MAX_PDF):
    official_url(url)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (KaigoNavi2027/1.0)'})
    # Retry only transport failures; all source, size and content checks still fail closed.
    opener = urllib.request.build_opener(OfficialRedirect())
    for attempt in range(3):
        try:
            with opener.open(req, timeout=35) as response:
                official_url(response.url)
                if int(response.headers.get('Content-Length', '0')) > limit:
                    raise ValueError('Source exceeds size limit')
                raw = response.read(limit + 1)
            if len(raw) > limit:
                raise ValueError('Source exceeds size limit')
            return raw
        except urllib.error.HTTPError as err:
            if err.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise
            err.close()
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)



def extract_pdf(raw):
    if not raw.startswith(b'%PDF-'):
        raise ValueError('Response is not a PDF')
    pages = []
    with fitz.open(stream=raw, filetype='pdf') as doc:
        if doc.is_encrypted or not 0 < len(doc) <= MAX_PAGES:
            raise ValueError('Encrypted, empty or oversized document')
        for number, page in enumerate(doc, 1):
            text = page.get_text(sort=True)
            # Tables are extraction candidates, never certified legal facts.
            tables = [t.extract() for t in page.find_tables().tables]
            notes = [line.strip() for line in text.splitlines()
                     if re.search(r'※|ただし|除く|例外|原則|要件|経過措置|注[０-９0-9）)]', line)]
            pages.append({'pdf_page': number, 'text': text, 'tables': tables,
                          'notes_and_exceptions': notes,
                          'has_images': bool(page.get_images()),
                          'review_required': len(text.strip()) < 150})
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'pages': pages,
            'table_scope': '機械抽出の候補。罫線のない表や図の完全性・意味は自動保証しない。'}


def archive_source(directory, url, raw, extracted):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stem = extracted['sha256']
    (directory / (stem + '.pdf')).write_bytes(raw)
    (directory / (stem + '.json')).write_text(
        json.dumps({'source_url': url, **extracted}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def article_hash(article):
    return hashlib.sha256(json.dumps(article, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()
