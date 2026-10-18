"""Transport retries must never bypass official URL, size or source checks."""
import io
import unittest
import urllib.error
from unittest.mock import Mock, patch
from kaigo_evidence import fetch

URL = 'https://www.mhlw.go.jp/content/12300000/test.pdf'

def response(raw=b'%PDF-test', url=URL, headers=None):
    result = Mock()
    result.url = url
    result.headers = headers or {}
    result.read.return_value = raw
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    return result

class FetchTests(unittest.TestCase):
    @patch('kaigo_evidence.time.sleep')
    @patch('kaigo_evidence.urllib.request.build_opener')
    def test_transient_http_failure_retries(self, build, sleep):
        build.return_value.open.side_effect = [
            urllib.error.HTTPError(URL, 503, 'temporary', {}, io.BytesIO()),
            response()]
        self.assertEqual(fetch(URL), b'%PDF-test')
        self.assertEqual(build.return_value.open.call_count, 2)

    @patch('kaigo_evidence.time.sleep')
    @patch('kaigo_evidence.urllib.request.build_opener')
    def test_exhausted_transport_failure_is_not_success(self, build, sleep):
        build.return_value.open.side_effect = urllib.error.URLError('timeout')
        with self.assertRaises(urllib.error.URLError):
            fetch(URL)
        self.assertEqual(build.return_value.open.call_count, 3)

    @patch('kaigo_evidence.time.sleep')
    @patch('kaigo_evidence.urllib.request.build_opener')
    def test_permanent_http_failure_is_not_retried(self, build, sleep):
        build.return_value.open.side_effect = urllib.error.HTTPError(URL, 404, 'missing', {}, io.BytesIO())
        with self.assertRaises(urllib.error.HTTPError):
            fetch(URL)
        self.assertEqual(build.return_value.open.call_count, 1)
        sleep.assert_not_called()

    @patch('kaigo_evidence.time.sleep')
    @patch('kaigo_evidence.urllib.request.build_opener')
    def test_size_and_redirect_checks_are_not_retried(self, build, sleep):
        for result in [response(raw=b'12345'), response(url='https://example.com/test.pdf')]:
            build.return_value.open.reset_mock()
            build.return_value.open.return_value = result
            with self.assertRaises(ValueError):
                fetch(URL, limit=4)
            self.assertEqual(build.return_value.open.call_count, 1)
        sleep.assert_not_called()
