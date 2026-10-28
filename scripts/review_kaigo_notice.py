"""Inspect a source for pinning; build only after an editorial hash is pinned.

--inspect prints evidence for review but never writes a verified release.
"""
import argparse
import hashlib
import json
from pathlib import Path
from build_kaigo_explainers import examine, retrieve_pdf
from kaigo_evidence import extract_pdf, archive_source

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'kaigo-navi2027-preview/data'


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--inspect', action='store_true')
    inspect = args.parse_args().inspect
    article = json.loads((DATA / 'notice-editorial.json').read_text())
    raw = retrieve_pdf(article['source_pdf'])
    extracted = extract_pdf(raw)
    archive_source('/tmp/kaigo-evidence', article['source_pdf'], raw, extracted)
    if inspect:
        # A discovery checksum is an inspection result, never an editorial pin.
        article['pinned_pdf_sha256'] = hashlib.sha256(raw).hexdigest()
    audit = examine(article, raw, extracted)
    print('NOTICE_INSPECTION_JSON ' + json.dumps({'article': article, 'audit': audit}, ensure_ascii=False))
    if inspect:
        return
    for name in ('explainers.json', 'explainers-verified.json'):
        path = DATA / name
        release = json.loads(path.read_text())
        release['articles'] = [a for a in release['articles'] if a['id'] != article['id']] + [article]
        if name.endswith('-verified.json'):
            release['source_audits'] = [a for a in release['source_audits'] if a['id'] != article['id']] + [audit]
        path.write_text(json.dumps(release, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
