"""FAQ i front matter: synlig sektion och FAQPage med samma text.

Kör: python -m unittest tests/test_faq.py
"""
import datetime as dt
import importlib.util
import json
import os
import re
import unittest
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location("motorpuls_build", os.path.join(ROOT, "build.py"))
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

ARTICLES = os.path.join(ROOT, "content", "articles")
GUIDE_FILES = (
    "2026-11-09-1-guide-formansvarde-elbil-2027.md",
    "2026-11-12-vinterdack-vad-galler.md",
    "2026-11-18-guide-laddkostnad-elbil-hemma-supercharger.md",
)


def sentences(text):
    return [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]


def front_matter(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    fm = build.yaml.safe_load(m.group(1))
    return fm, m.group(2)


class _FaqText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.questions, self.answers, self._tag = [], [], None

    def handle_starttag(self, tag, attrs):
        self._tag = tag

    def handle_endtag(self, tag):
        self._tag = None

    def handle_data(self, data):
        if self._tag == "h3":
            self.questions.append(data)
        elif self._tag == "p":
            self.answers.append(data)


def faq_visible(html):
    m = re.search(r'<section class="faq"[\s\S]*?</section>', html)
    parser = _FaqText()
    parser.feed(m.group(0) if m else "")
    return parser.questions, parser.answers


def jsonld_blocks(html):
    return [json.loads(raw) for raw in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html)]


class FaqBuildTest(unittest.TestCase):
    def setUp(self):
        self.feeds = build.FEEDS
        build.FEEDS = [dict(key="elbil", name="Elbil", path="/feed/elbil.xml", arts=[]),
                       dict(key="guider", name="Guider", path="/feed/guider.xml", arts=[])]

    def tearDown(self):
        build.FEEDS = self.feeds

    def test_visible_text_matches_schema(self):
        pairs = [("Vad gäller A & B?", 'Svaret är "ja", och <klart>.'),
                 ("Vad  kostar\ndet?", "En mening.  Två meningar.")]
        html = build.faq_section(build.faq_pairs({"faq": [
            {"question": q, "answer": a} for q, a in pairs]}))
        ld = build.faq_ld(build.faq_pairs({"faq": [
            {"question": q, "answer": a} for q, a in pairs]}))
        questions, answers = faq_visible(html)
        self.assertEqual(questions, [item["name"] for item in ld["mainEntity"]])
        self.assertEqual(answers, [item["acceptedAnswer"]["text"] for item in ld["mainEntity"]])
        self.assertEqual(questions, ["Vad gäller A & B?", "Vad kostar det?"])
        self.assertEqual(answers[1], "En mening. Två meningar.")
        self.assertEqual(ld["@type"], "FAQPage")
        self.assertIsNone(build.faq_ld([]))
        self.assertEqual(build.faq_section([]), "")

    def test_check_faq_rejects_bad_lists(self):
        for bad in ([], [{"question": "Fråga?"}], [{"question": " ", "answer": "Svar."}], "Fråga"):
            with self.assertRaises(SystemExit):
                build.check_faq({"faq": bad}, "x.md")
        build.check_faq({}, "x.md")

    def test_article_keeps_newsarticle_and_adds_faqpage(self):
        when = dt.datetime(2026, 11, 18, 7, tzinfo=build.TZ)
        base = dict(
            title="Test", excerpt="Kort.", published="2026-11-18T07:00:00+01:00",
            modified="2026-11-18T09:00:00+01:00", category="Elbil", tags=["elbil"],
            url="/artikel/test/", author="Test", sources=[], headline="Test",
            date=dt.date(2026, 11, 18), mod_date=dt.date(2026, 11, 18),
            when=when, mod_when=when, minutes=1, body_html="<p>Bröd.</p>",
            slug="test", file="t.md", cat="elbil", img=None, images_out=[],
        )
        plain = build.article(dict(base, type="nyhet"))
        types = [block.get("@type") for block in jsonld_blocks(plain)]
        self.assertIn("NewsArticle", types)
        self.assertNotIn("FAQPage", types)
        self.assertNotIn('class="faq"', plain)

        guide = build.article(dict(base, type="guide", sources=[("Skatteverket", "https://www.skatteverket.se/")], faq=[
            {"question": "Vad kostar det?", "answer": "3,15 kronor per kWh."}]))
        blocks = jsonld_blocks(guide)
        types = [block.get("@type") for block in blocks]
        self.assertIn("Article", types)
        self.assertNotIn("NewsArticle", types)
        self.assertIn("FAQPage", types)
        article_ld = next(b for b in blocks if b.get("@type") == "Article")
        self.assertEqual(article_ld["headline"], "Test")
        self.assertNotIn("mainEntity", article_ld)
        faq_ld = next(b for b in blocks if b.get("@type") == "FAQPage")
        questions, answers = faq_visible(guide)
        self.assertEqual(questions, [faq_ld["mainEntity"][0]["name"]])
        self.assertEqual(answers, [faq_ld["mainEntity"][0]["acceptedAnswer"]["text"]])
        self.assertLess(guide.index('class="faq"'), guide.index('id="kallor-h"'))

    def test_guides_intro_above_the_list(self):
        html = build.guides_page([])
        self.assertIn(f'<p class="catpage__dek">{build.GUIDE_INTRO}</p>', html)
        self.assertLess(html.index("catpage__dek"), html.index("catpage__list"))
        self.assertEqual(build.GUIDE_INTRO.count(". "), 2)
        self.assertNotIn("\u2013", build.GUIDE_INTRO)
        self.assertNotIn("\u2014", build.GUIDE_INTRO)
        self.assertIn(build.GUIDE_DESC, html)
        graph = jsonld_blocks(html)[0]["@graph"][0]
        self.assertEqual(graph["@type"], "CollectionPage")
        self.assertEqual(graph["description"], build.GUIDE_DESC)

    def test_three_guides_only(self):
        for name in os.listdir(ARTICLES):
            if not name.endswith(".md"):
                continue
            fm, body = front_matter(os.path.join(ARTICLES, name))
            if name not in GUIDE_FILES:
                self.assertNotIn("faq", fm, name)
                continue
            faq = fm["faq"]
            # Guiden vinterdack-vad-galler uppdaterades 24 november 2026 till en
            # sammanhängande text (8 frågor, påståenderubriker, datumlista).
            # De andra guiderna är kvar i frågeformen från 18 november.
            winter = name == "2026-11-12-vinterdack-vad-galler.md"
            self.assertGreaterEqual(len(faq), 4, name)
            self.assertLessEqual(len(faq), 8 if winter else 6, name)
            prose = body.split("\n## Källor", 1)[0]
            self.assertNotIn("\u2013", prose + json.dumps(faq, ensure_ascii=False))
            self.assertNotIn("\u2014", prose + json.dumps(faq, ensure_ascii=False))
            h2s = re.findall(r"^## (.+)$", prose, re.M)
            self.assertTrue(h2s, name)
            if not winter:
                for h2 in h2s:
                    self.assertTrue(h2.endswith("?"), h2)
                for block in re.split(r"^## .+$", prose, flags=re.M)[1:]:
                    first = next(line for line in block.splitlines() if line.strip())
                    self.assertFalse(first.startswith(("-", "|")), first)
            for item in faq:
                self.assertTrue(item["question"].endswith("?"))
                self.assertTrue(1 <= len(sentences(item["answer"])) <= 3, item["answer"])
            updated = fm["updated"]
            if isinstance(updated, dt.datetime):
                stamp = updated.isoformat()
            else:
                stamp = str(updated)
            self.assertTrue(stamp.startswith("2026-11-24" if winter else "2026-11-18"), stamp)
            self.assertIn("+01:00", stamp)


if __name__ == "__main__":
    unittest.main()
