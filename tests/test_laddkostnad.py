"""Laddkostnad: formeln i js/laddkostnad.js och sidan som build.py skriver.

Kör: python -m unittest tests/test_laddkostnad.py
"""
import importlib.util
import json
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location("motorpuls_build", os.path.join(ROOT, "build.py"))
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)
VERKTYG = build.load_verktyg()


def js_compute(payload):
    script = (
        "const api=require('./js/laddkostnad.js');"
        "const input=Object.assign({}, api.DEFAULTS, JSON.parse(process.argv[1]));"
        "if (process.argv[2]==='drop') { delete input.petrolL; delete input.petrolPrice; }"
        "process.stdout.write(JSON.stringify(api.compute(input)));"
    )
    raw = subprocess.check_output(["node", "-e", script, json.dumps(payload), payload.get("_drop") or ""], cwd=ROOT)
    return json.loads(raw)


class FormulaTest(unittest.TestCase):
    def test_defaults_match_the_worked_example(self):
        r = js_compute({})
        self.assertTrue(r["ok"])
        self.assertEqual(r["kwhBatt"], "1,80")
        self.assertEqual(r["kwhHome"], "1,98")
        self.assertEqual(r["perMil"], "5,87\u00a0kr")
        self.assertEqual(r["perManad"], "587\u00a0kr")
        self.assertEqual(r["perAr"], "7\u00a0040\u00a0kr")
        self.assertEqual(r["hemmaAr"], "4\u00a0448\u00a0kr")
        self.assertEqual(r["snabbAr"], "2\u00a0592\u00a0kr")
        self.assertEqual(r["petrol"]["perAr"], "15\u00a0120\u00a0kr")
        self.assertIn("8\u00a0080\u00a0kr mindre", r["petrol"]["diffText"])

    def test_year_distance_matches_twelve_months(self):
        month = js_compute({"distance": 100, "period": "manad"})
        year = js_compute({"distance": 1200, "period": "ar"})
        self.assertEqual(month["perAr"], year["perAr"])
        self.assertEqual(month["perMil"], year["perMil"])

    def test_home_only_drops_fast_charging(self):
        r = js_compute({"homeShare": 100})
        self.assertEqual(r["fastShare"], "0")
        self.assertEqual(r["perMil"], r["hemmaMil"])
        self.assertEqual(r["snabbAr"], "0\u00a0kr")

    def test_empty_petrol_skips_the_comparison(self):
        r = js_compute({"_drop": "drop", "petrolL": None, "petrolPrice": None})
        self.assertTrue(r["ok"])
        self.assertIsNone(r["petrol"])

    def test_comma_and_invalid(self):
        self.assertEqual(js_compute({"homePrice": 2.5})["ok"], True)
        bad = js_compute({"kwhPer100": 0})
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["field"], "forbrukning")


class PageTest(unittest.TestCase):
    def setUp(self):
        self.feeds = build.FEEDS
        build.FEEDS = [dict(key="guider", name="Guider", path="/feed/guider.xml", arts=[])]

    def tearDown(self):
        build.FEEDS = self.feeds

    def test_tool_page_has_formula_schema_and_the_same_numbers(self):
        html = VERKTYG.tool_page(build)
        r = js_compute({})
        self.assertIn(f'<link rel="canonical" href="{build.DOMAIN}/verktyg/laddkostnad/">', html)
        self.assertIn("WebApplication", html)
        self.assertIn("FAQPage", html)
        self.assertIn('aria-live="polite"', html)
        self.assertEqual(html.count('inputmode="decimal"'), 8)
        self.assertIn('id="out-mil">' + r["perMil"], html)
        self.assertIn('id="out-ar">' + r["perAr"], html)
        self.assertIn(r["petrol"]["diffText"], html)
        self.assertIn("Startvärdena är exempel", html)
        self.assertIn("1 mil är 10 km", html)
        self.assertIn("/js/laddkostnad.js?", html)
        self.assertNotIn("cdn.", html)
        blocks = [json.loads(raw) for raw in __import__("re").findall(
            r'<script type="application/ld\+json">(.*?)</script>', html)]
        faq = next(b for b in blocks if b.get("@type") == "FAQPage")
        self.assertEqual(len(faq["mainEntity"]), 5)
        questions = [q["name"] for q in faq["mainEntity"]]
        self.assertEqual(questions, [q for q, _ in VERKTYG.faq_pairs()])
        for q, ans in VERKTYG.faq_pairs():
            self.assertIn(q, html)
            self.assertIn(ans, html)
            match = next(item for item in faq["mainEntity"] if item["name"] == q)
            self.assertEqual(match["acceptedAnswer"]["text"], ans)
        graph = next(b for b in blocks if "@graph" in b)
        types = [node["@type"] for node in graph["@graph"]]
        self.assertIn("WebApplication", types)
        self.assertIn('href="/verktyg/"', html)

    def test_index_lists_the_tool_and_guides_link_to_it(self):
        index = VERKTYG.index_page(build)
        self.assertIn('href="/verktyg/laddkostnad/"', index)
        self.assertIn(f'<link rel="canonical" href="{build.DOMAIN}/verktyg/">', index)
        guides = build.guides_page([])
        self.assertIn('href="/verktyg/laddkostnad/"', guides)

    def test_sitemap_paths(self):
        self.assertEqual([p for p, _ in VERKTYG.paths()], ["/verktyg/", "/verktyg/laddkostnad/"])
