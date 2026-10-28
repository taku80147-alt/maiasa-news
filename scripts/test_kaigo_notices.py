import copy
import tempfile
import unittest
from pathlib import Path
from discover_kaigo_notices import scan_notices, triage, reconcile_inventory, coverage_errors


def notice(title='福祉用具の給付対象の一部改正について', date='令和８年10月26日', volume='1549', href='/content/001762862.pdf'):
    return f'<p>○<a href="{href}">介護保険最新情報Vol.{volume}（{title}）［426KB］</a><br>（{date}高齢者支援課長通知）</p>'


class NoticeTests(unittest.TestCase):
    def test_notice_date_not_future_applicability_and_normalized_volume(self):
        rows = scan_notices(notice(title='令和９年２月１日からの給付対象改正', volume='１５４９'))
        self.assertEqual(rows[0]['id'], 'n-notice-vol-1549')
        self.assertEqual(rows[0]['date'], '2026-10-26')
        self.assertEqual(triage(rows[0])[0], 'include')

    def test_qa_and_facility_changes_are_included_without_equipment_keyword(self):
        for title in ['介護報酬改定に関するＱ＆Ａ（Vol.18）', '介護老人福祉施設の人員基準の見直し', '利用者負担の一部改正']:
            self.assertEqual(triage({'title': title})[0], 'include')

    def test_unknown_not_silently_excluded_and_event_has_reason(self):
        self.assertEqual(triage({'title': '新しい運用のお知らせ'})[0], 'review_pending')
        state, reason = triage({'title': 'ケアプラン活用セミナーの開催'})
        self.assertEqual(state, 'excluded')
        self.assertTrue(reason)

    def test_bullet_inside_anchor_keeps_correct_primary_pdf(self):
        html = notice(volume='1494', href='/content/first.pdf') + notice(volume='1493', href='/content/second.pdf').replace('○<a', '<a').replace('>介護保険', '>○介護保険')
        rows = {r['id']:r for r in scan_notices(html)}
        self.assertEqual(rows['n-notice-vol-1493']['source_urls'], ['https://www.mhlw.go.jp/content/second.pdf'])
        self.assertEqual(rows['n-notice-vol-1494']['source_urls'], ['https://www.mhlw.go.jp/content/first.pdf'])

    def test_multiple_pdf_attachments_and_unnumbered_notice(self):
        html = notice(volume='') .replace('Vol.', '').replace('</a><br>', '</a><a href="/content/appendix.pdf">別紙</a><br>')
        row = scan_notices(html)[0]
        self.assertEqual(len(row['source_urls']), 2)
        self.assertTrue(row['id'].startswith('n-notice-'))

    def test_effective_date_in_following_note_is_not_issue_date(self):
        html = notice(date='令和８年１月23日') + ' (施行日：令和８年４月１日)' + notice(volume='1550')
        self.assertEqual([r['id'] for r in scan_notices(html)], ['n-notice-vol-1550'])

    def test_unparseable_or_external_source_fails_closed(self):
        for html in ['<html>maintenance</html>', notice(href='https://www.mhlw.go.jp.evil.example/x.pdf'), notice(href='https://user@www.mhlw.go.jp/x.pdf')]:
            with self.assertRaises(ValueError):
                scan_notices(html)

    def test_inventory_keeps_old_entries_and_detects_missing_publication(self):
        rows = scan_notices(notice())
        inventory = reconcile_inventory(rows, {}, [])
        self.assertEqual(coverage_errors(inventory, []), [rows[0]['id']])
        articles = [{'id': rows[0]['id'], 'source_url': rows[0]['source_url']}]
        self.assertEqual(coverage_errors(inventory, articles), [])
        older = copy.deepcopy(rows[0]); older['id'] = 'n-notice-vol-1490'
        later = reconcile_inventory([older], inventory, articles)
        self.assertEqual(len(later['documents']), 2)

    def test_manual_selection_invalidated_when_source_changes(self):
        rows = scan_notices(notice())
        inv = reconcile_inventory(rows, {}, [])
        inv['documents'][0]['selection'] = 'excluded'
        inv['documents'][0]['reason'] = 'editorial'
        inv['documents'][0]['editorial_reviewed_on'] = '2026-10-28'
        kept=reconcile_inventory(rows, inv, [])
        self.assertEqual(kept['documents'][0]['selection'], 'excluded')
        self.assertEqual(reconcile_inventory(rows, kept, [])['documents'][0]['selection'], 'excluded')
        changed = copy.deepcopy(rows); changed[0]['source_urls'].append('https://www.mhlw.go.jp/content/new.pdf')
        self.assertEqual(reconcile_inventory(changed, inv, [])['documents'][0]['selection'], 'include')


if __name__ == '__main__':
    unittest.main()
