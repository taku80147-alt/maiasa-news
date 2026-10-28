"""Discover every dated MHLW notice before relevance triage; no policy inference.

The inventory is intentionally not truncated to the homepage feed. Unclassified
items remain review_pending, rather than disappearing through keyword filtering.
"""
import datetime as dt
import hashlib
import json
import re
import unicodedata
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

NOTICE_INDEX = 'https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/hukushi_kaigo/kaigo_koureisha/index_00010.html'
START_DATE = '2026-04-01'


def official(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.netloc != 'www.mhlw.go.jp':
        raise ValueError('Official MHLW HTTPS source required')
    return urlunsplit((p.scheme, p.netloc, p.path, p.query, ''))


class IndexText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.skip = [], [], 0
        self.pending_link = None

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if self.skip:
            return
        if tag in ('p', 'div', 'br', 'li', 'tr'):
            self.parts.append('\n')
        if tag == 'a':
            href = dict(attrs).get('href', '')
            self.pending_link = ' LINK%d ' % len(self.links)
            self.links.append(urljoin(NOTICE_INDEX, href))

    def handle_endtag(self, tag):
        if tag == 'a' and self.pending_link:
            self.parts.append(self.pending_link)
            self.pending_link = None
        if tag in ('script', 'style') and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            if self.pending_link:
                bullet = re.match(r'^(\s*[○〇◯])', data)
                if bullet:
                    self.parts.extend([bullet[0], self.pending_link, data[len(bullet[0]):]])
                else:
                    self.parts.extend([self.pending_link, data])
                self.pending_link = None
            else:
                self.parts.append(data)


def scan_notices(html):
    parser = IndexText()
    parser.feed(html)
    text = unicodedata.normalize('NFKC', ''.join(parser.parts))
    blocks = re.split(r'[○〇◯]', text)
    found = {}
    for block in blocks:
        if not re.search(r'LINK\d+', block):
            continue
        # Dates in the notice title (e.g. applicability) are not the issue date.
        date_matches = list(re.finditer(r'[（(]\s*令和\s*(元|\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日[^）)]*(?:厚生労働|事務連絡|課長|局長)[^）)]*[）)]', block))
        dates = [m.groups() for m in date_matches]
        if not dates:
            continue
        year, month, day = dates[0]
        date = dt.date(2018 + (1 if year == '元' else int(year)), int(month), int(day)).isoformat()
        if date < START_DATE:
            continue
        first_date = date_matches[0]
        title = re.sub(r'LINK\d+', '', block[:first_date.start()]).strip()
        title = re.sub(r'\s+', ' ', title)
        title = re.sub(r'[\[［][^\]］]*(?:KB|MB)[\]］]', '', title, flags=re.I).strip()
        urls = []
        for n in re.findall(r'LINK(\d+)', block):
            try:
                url = official(parser.links[int(n)])
            except ValueError:
                continue
            if urlsplit(url).path.lower().endswith('.pdf') and url not in urls:
                urls.append(url)
        if not urls:
            raise ValueError('Dated notice without an official PDF: ' + title)
        volume = re.search(r'vol\.?\s*(\d+)', title, re.I)
        identity = 'vol-' + volume[1] if volume else hashlib.sha256(urls[0].encode()).hexdigest()[:16]
        row = {'id': 'n-notice-' + identity, 'date': date, 'title': title,
               'source_url': urls[0], 'source_urls': urls, 'index_url': NOTICE_INDEX}
        if row['id'] in found and found[row['id']] != row:
            raise ValueError('Conflicting notice identity: ' + row['id'])
        found[row['id']] = row
    if not found:
        raise ValueError('No dated notices parsed; preserve last good inventory')
    return sorted(found.values(), key=lambda r: (r['date'], r['id']), reverse=True)


def triage(row):
    title = unicodedata.normalize('NFKC', row['title'])
    if re.search(r'セミナー|研修会|参加案内|出展|老人の日|老人週間|への協力依頼', title):
        return 'excluded', '行事・研修・調査協力の案内。改正内容の新情報ではない。'
    if re.search(r'改正|改定|見直し|公布|施行|Q\s*&\s*A|給付対象|給付と負担|中間とりまとめ|貸与価格|価格の上限', title, re.I):
        return 'include', '改正・制度運用・Q&Aに関する一次資料。本文の解釈は別途確認。'
    if re.search(r'セミナー|研修会|参加案内|出展|老人の日|老人週間', title):
        return 'excluded', '行事・研修の案内。改正内容の新情報ではない。'
    return 'review_pending', '見出しだけでは改正との関係を判断できないため、本文確認待ち。'


def reconcile_inventory(rows, previous, articles):
    old = {r['id']: r for r in previous.get('documents', [])}
    published = {a['id']: a for a in articles}
    for row in rows:
        row = dict(row)
        prior = old.get(row['id'])
        state, reason = triage(row)
        # Editorial decisions survive only for unchanged discovery metadata.
        if prior and prior.get('editorial_reviewed_on') and prior.get('title') == row['title'] and prior.get('source_urls') == row['source_urls'] and prior.get('date') == row['date']:
            state, reason = prior.get('selection', state), prior.get('reason', reason)
            row['editorial_reviewed_on'] = prior['editorial_reviewed_on']
        row.update(selection=state, reason=reason)
        article = published.get(row['id'])
        row['publication'] = 'listed' if article and article['source_url'] == row['source_url'] else 'not_listed'
        old[row['id']] = row
    return {'schema_version': 1, 'coverage_start': START_DATE,
            'sources': [NOTICE_INDEX], 'documents': sorted(old.values(), key=lambda r: (r['date'], r['id']), reverse=True)}


def notice_article(row, classify):
    return {'id': row['id'], 'date': row['date'], 'title': row['title'],
            'summary': '改正・制度運用に関する公式資料が公開されました。本文の解説は準備中です。',
            'detail': 'この項目は公式一覧の見出しと発出日を確認した速報です。変更内容・対象・適用日は本文確認後に追記します。',
            'category': classify(row['title'], 'ins'), 'status': '公式資料公開・解説準備中',
            'source_url': row['source_url'], 'source_name': '厚生労働省・介護保険最新情報',
            'source_kind': 'notice', 'curated': False}


def coverage_errors(inventory, articles):
    published = {a['id']: a for a in articles}
    return [r['id'] for r in inventory['documents'] if r['selection'] == 'include' and
            (r['id'] not in published or published[r['id']]['source_url'] != r['source_url'])]
