#!/usr/bin/env python3
"""Offline fail-closed evidence contract checks; no content publication."""
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "kaigo-navi2027-preview" / "data"

class EvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.draft = json.loads((DATA / "explainers.json").read_text(encoding="utf-8"))
        cls.release = json.loads((DATA / "explainers-verified.json").read_text(encoding="utf-8"))

    def test_sources_are_official_and_pinned(self):
        for article in self.draft["articles"]:
            with self.subTest(article=article["id"]):
                pdf = urlparse(article["source_pdf"])
                self.assertEqual((pdf.scheme, pdf.hostname), ("https", "www.mhlw.go.jp"))
                self.assertTrue(pdf.path.startswith("/content/") and pdf.path.endswith(".pdf"))
                self.assertRegex(article["pinned_pdf_sha256"], r"^[0-9a-f]{64}$")
                self.assertRegex(article["meeting_date"], r"^20\\d{2}-\\d{2}-\\d{2}$")
                self.assertTrue(article.get("review_scope"))
                self.assertTrue(article.get("source_scope"))

    def test_numerical_evidence_is_scoped_and_page_linked(self):
        for article in self.draft["articles"]:
            for item in article.get("numeric_evidence", []):
                with self.subTest(article=article["id"], item=item):
                    self.assertIsInstance(item["pdf_page"], int)
                    self.assertGreater(item["pdf_page"], 0)
                    self.assertTrue(item["literal"].strip())
                    self.assertTrue(item["scope"].strip())
                    self.assertTrue(any(
                        a["id"] == article["id"] and
                        n["pdf_page"] == item["pdf_page"] and
                        n["literal"] == item["literal"] and
                        n["scope"] == item["scope"] and
                        n["status"] == "located"
                        for a in self.release["source_audits"]
                        for n in a["numeric_checks"]
                    ))

    def test_source_audits_match_articles_exactly(self):
        article_ids = [a["id"] for a in self.draft["articles"]]
        audit_ids = [a["id"] for a in self.release["source_audits"]]
        self.assertEqual(len(audit_ids), len(set(audit_ids)), "duplicate source audit IDs")
        self.assertEqual(set(article_ids), set(audit_ids), "missing or stale source audits")
        for audit in self.release["source_audits"]:
            article = next(a for a in self.draft["articles"] if a["id"] == audit["id"])
            with self.subTest(article=audit["id"]):
                self.assertEqual(audit["source_pdf"], article["source_pdf"])
                self.assertEqual(audit["sha256"], article["pinned_pdf_sha256"])
                self.assertEqual(len(audit["evidence_checks"]), len(article["verified_claims"]))
                for actual, expected in zip(audit["evidence_checks"], article["verified_claims"]):
                    self.assertEqual(actual["pdf_page"], expected["pdf_page"])
                    self.assertEqual(actual["anchor"], expected["anchor"])
                    self.assertEqual(actual["claim"], expected["claim"])
                    self.assertEqual(actual["status"], "located")

    def test_proposal_not_mislabeled_as_enacted(self):
        for article in self.draft["articles"]:
            with self.subTest(article=article["id"]):
                self.assertIn("検討中", article["status"])
                self.assertNotIn("施行済み", article["status"])
                self.assertNotIn("決定済み", article["status"])

if __name__ == "__main__":
    unittest.main()
