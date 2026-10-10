"""Run with:  python -m unittest discover -s tests -v   (no extra dependencies, no API keys)"""

import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
for k in ("SERPAPI_API_KEY", "ANTHROPIC_API_KEY"):
    os.environ.pop(k, None)

import extractor  # noqa: E402
import storage  # noqa: E402


def posting(company, title, location="Bengaluru"):
    return {"company": company, "title": title, "location": location, "seniority": "mid",
            "remote": False, "posted": "1 day ago", "signal_note": "", "source_url": ""}


class RulesExtraction(unittest.TestCase):
    def test_no_key_means_rules_mode(self):
        self.assertEqual(extractor.extraction_mode(), "rules")
        _, info = extractor.normalize_with_info([{"title": "x", "company_name": "y"}])
        self.assertEqual(info, {"mode": "rules", "ai_failed": False})

    def test_fields_come_from_serpapi_data(self):
        raw = {
            "title": "Senior LLM Infra Engineer", "company_name": "Acme", "location": "Hyderabad, India",
            "via": "via LinkedIn", "share_link": "https://example.com/j/1",
            "detected_extensions": {"posted_at": "3 days ago", "schedule_type": "Full-time", "work_from_home": True},
            "description": "Build GPU platforms.",
        }
        out = extractor.rules_normalize(raw)
        self.assertEqual(out["company"], "Acme")
        self.assertEqual(out["seniority"], "senior")
        self.assertTrue(out["remote"])
        self.assertEqual(out["posted"], "3 days ago")
        self.assertEqual(out["source_url"], "https://example.com/j/1")
        for fact in ("3 days ago", "full-time", "remote-friendly", "via LinkedIn"):
            self.assertIn(fact.lower(), out["signal_note"].lower())

    def test_seniority_from_years(self):
        self.assertEqual(extractor.guess_seniority("ML Engineer", "2+ years experience"), "junior")
        self.assertEqual(extractor.guess_seniority("ML Engineer", "4-6 years of experience"), "mid")
        self.assertEqual(extractor.guess_seniority("ML Engineer", "8+ years"), "senior")
        self.assertEqual(extractor.guess_seniority("Staff Engineer"), "lead/staff")
        self.assertEqual(extractor.guess_seniority("Engineer"), "unknown")

    def test_missing_fields_do_not_crash(self):
        out = extractor.rules_normalize({})
        self.assertEqual(out["company"], "unknown")
        self.assertEqual(out["signal_note"], "No extra details in listing.")


class DiffLogic(unittest.TestCase):
    def setUp(self):
        storage.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "test.db"

    def test_new_disappeared_unchanged(self):
        a, b, c = posting("A", "X"), posting("B", "Y"), posting("C", "Z")
        r1 = storage.save_run("q", "India", [a, b])
        r2 = storage.save_run("q", "India", [b, c])
        d = storage.diff_runs(r1, r2)
        self.assertEqual([r["company"] for r in d.new], ["C"])
        self.assertEqual([r["company"] for r in d.disappeared], ["A"])
        self.assertEqual(d.unchanged_count, 1)

    def test_key_ignores_case_and_whitespace(self):
        self.assertEqual(storage.posting_key(posting("Acme ", "ML Engineer")),
                         storage.posting_key(posting("acme", " ml engineer ")))


if __name__ == "__main__":
    unittest.main()
