"""Hubbsidor för märke och modell, kunskapsbanken och guide-rutan.

Kör: python -m unittest tests/test_hubs.py
"""
import datetime as dt
import importlib.util
import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location("motorpuls_build", os.path.join(ROOT, "build.py"))
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


def art(slug, tags=(), cat="elbil", typ=None, when=1, title=None, excerpt="Ingress om bilen.", tema=None, updated=False):
    base = dt.datetime(2026, 11, 1, 7, tzinfo=build.TZ) + dt.timedelta(days=when)
    mod = base + dt.timedelta(hours=3) if updated else base
    row = {
        "slug": slug, "cat": cat, "category": cat, "tags": list(tags), "type": typ,
        "when": base, "mod_when": mod, "title": title or slug, "excerpt": excerpt,
        "url": f"/artikel/{slug}/", "published": base.isoformat(timespec="seconds"),
        "modified": mod.isoformat(timespec="seconds"), "date": base.date(), "mod_date": mod.date(),
        "img": None, "headline": title or slug, "author": "Lukas", "sources": [],
        "body_html": "<p>Bröd.</p>", "minutes": 1, "file": f"{slug}.md", "images_out": [],
    }
    if tema:
        row["guide_tema"] = tema
    return row


def jsonld(html):
    return [json.loads(raw) for raw in __import__("re").findall(
        r'<script type="application/ld\+json">(.*?)</script>', html)]


class HubBuildTest(unittest.TestCase):
    def test_alias_reaches_threshold_and_rolls_up_to_brand(self):
        arts = [
            art("ny", tags=["Model Y"], when=3),
            art("mellan", tags=["Tesla Model Y"], when=2),
            art("gammal", tags=["Model Y"], when=1),
        ]
        hubs = {h["slug"]: h for h in build.build_hubs(arts)}
        self.assertEqual([a["slug"] for a in hubs["tesla-model-y"]["arts"]], ["ny", "mellan", "gammal"])
        self.assertEqual(hubs["tesla-model-y"]["path"], "/modell/tesla-model-y/")
        self.assertEqual([a["slug"] for a in hubs["tesla"]["arts"]], ["ny", "mellan", "gammal"])
        self.assertNotIn("tesla-model-3", hubs)

    def test_two_articles_get_no_page(self):
        arts = [art("a", tags=["Porsche"], when=2), art("b", tags=["Porsche"], when=1)]
        self.assertFalse(any(h["slug"] == "porsche" for h in build.build_hubs(arts)))

    def test_category_counts_toward_the_brand(self):
        arts = [art(f"t{i}", tags=["förarstöd"], cat="tesla", when=i) for i in range(1, 4)]
        hubs = {h["slug"]: h for h in build.build_hubs(arts)}
        self.assertIn("tesla", hubs)
        self.assertEqual(len(hubs["tesla"]["arts"]), 3)

    def test_page_is_neutral_until_a_fact_field_is_filled(self):
        hub = build.build_hubs([art(f"t{i}", tags=["Volvo", "EX60"], when=i) for i in range(1, 4)])
        ex60 = next(h for h in hub if h["slug"] == "volvo-ex60")
        html = build.hub_page(ex60)
        self.assertIn("Alla Motorpuls artiklar om Volvo EX60.", html)
        self.assertNotIn('class="hub-facts"', html)
        self.assertNotIn(">Pris<", html)
        self.assertNotIn(">Specifikationer<", html)
        self.assertIn('rel="canonical" href="https://motorpuls.se/modell/volvo-ex60/"', html)
        self.assertIn('property="og:image" content="https://motorpuls.se/img/og/motorpuls.jpg"', html)
        self.assertLess(html.index('href="/artikel/t3/"'), html.index('href="/artikel/t1/"'))
        graph = jsonld(html)[0]["@graph"]
        types = [node.get("@type") for node in graph]
        self.assertIn("CollectionPage", types)
        self.assertIn("BreadcrumbList", types)
        page_ld = next(node for node in graph if node["@type"] == "CollectionPage")
        self.assertEqual(page_ld["mainEntity"]["@type"], "ItemList")
        self.assertEqual(page_ld["mainEntity"]["numberOfItems"], 3)
        ex60["specs"] = "Fyrhjulsdrift."
        filled = build.hub_page(ex60)
        self.assertIn("Specifikationer", filled)
        self.assertIn("Fyrhjulsdrift.", filled)
        self.assertNotIn(">Pris<", filled)

    def test_model_breadcrumb_links_the_brand_hub(self):
        hubs = build.build_hubs([art(f"t{i}", tags=["Volvo EX60"], when=i) for i in range(1, 4)])
        ex60 = next(h for h in hubs if h["slug"] == "volvo-ex60")
        html = build.hub_page(ex60)
        self.assertIn('href="/marke/volvo/"', html)
        self.assertIn(">Volvo EX60</span>", html)

    def test_news_sitemap_skips_hubs(self):
        xml = build.news_sitemap([art("nyhet", tags=["Tesla"], when=1)])
        self.assertNotIn("/marke/", xml)
        self.assertNotIn("/modell/", xml)

    def test_real_articles_only_publish_hubs_with_three(self):
        arts = build.load_articles()
        hubs = build.build_hubs(arts)
        self.assertGreaterEqual(len(hubs), 1)
        for h in hubs:
            self.assertGreaterEqual(len(h["arts"]), 3, h["path"])
            self.assertTrue(h["path"].startswith(("/marke/", "/modell/")))
        paths = {h["path"] for h in hubs}
        for must in ("/marke/tesla/", "/marke/volvo/", "/modell/tesla-model-y/", "/modell/volvo-ex60/"):
            self.assertIn(must, paths)
        slugs = {a["slug"] for a in arts}
        for h in hubs:
            for a in h["arts"]:
                self.assertIn(a["slug"], slugs)


class GuideHubTest(unittest.TestCase):
    def setUp(self):
        self.feeds, self.guides, self.hubs = build.FEEDS, list(build.GUIDES), list(build.HUBS)
        build.FEEDS = [dict(key=k, name=k, path=f"/feed/{k}.xml", arts=[])
                       for k in ("elbil", "guider", "tesla", "motorsport", "trafik-och-sakerhet", "sportbil")]

    def tearDown(self):
        build.FEEDS, build.GUIDES[:], build.HUBS[:] = self.feeds, self.guides, self.hubs

    def test_guides_grouped_by_theme_with_updated(self):
        guides = [
            art("ladd", tags=["laddning"], typ="guide", when=3, tema="Elbil och laddning", title="Ladda hemma", updated=True),
            art("skatt", tags=["skatt"], typ="guide", when=2, tema="Skatt och kostnader", title="Förmånsvärde"),
            art("regler", tags=["vinterdäck"], cat="trafik-och-sakerhet", typ="guide", when=1, title="Vinterdäck"),
        ]
        html = build.guides_page(guides)
        self.assertLess(html.index("Elbil och laddning"), html.index("Skatt och kostnader"))
        self.assertLess(html.index("Skatt och kostnader"), html.index("Lagar och regler"))
        self.assertIn("Uppdaterad", html)
        self.assertEqual(html.count("Uppdaterad"), 1)
        self.assertIn(build.GUIDE_INTRO, html)
        graph = jsonld(html)[0]["@graph"][0]
        self.assertEqual(graph["@type"], "CollectionPage")
        self.assertEqual(graph["mainEntity"]["@type"], "ItemList")
        self.assertEqual(graph["mainEntity"]["numberOfItems"], 3)
        self.assertEqual(graph["mainEntity"]["itemListElement"][0]["name"], "Ladda hemma")

    def test_fallback_theme_without_guide_tema(self):
        self.assertEqual(build.guide_theme(art("x", tags=["laddkostnad"], typ="guide")), "Elbil och laddning")
        self.assertEqual(build.guide_theme(art("y", tags=["vinterdäck"], cat="trafik-och-sakerhet", typ="guide")), "Lagar och regler")
        self.assertEqual(build.guide_theme(art("z", tags=["annat"], cat="sportbil", typ="guide")), "Övrigt")

    def test_guide_box_picks_one_match_and_skips_guides(self):
        older = art("forman", tags=["Tesla Model Y", "skatt"], cat="guider", typ="guide", when=1, title="Förmån")
        newer = art("ladd", tags=["Tesla Model Y", "laddning"], cat="elbil", typ="guide", when=4, title="Ladda")
        other = art("vinter", tags=["vinterdäck"], cat="trafik-och-sakerhet", typ="guide", when=9, title="Däck")
        build.GUIDES[:] = [newer, older, other]
        news = art("nyhet", tags=["Tesla Model Y"], cat="tesla", when=5, title="Ny Model Y")
        self.assertEqual(build.matching_guide(news)["slug"], "ladd")
        self.assertIsNone(build.matching_guide(older))
        lone = art("f1", tags=["Formel 1"], cat="motorsport", when=2)
        self.assertIsNone(build.matching_guide(lone))
        box = build.guide_box(build.matching_guide(news))
        self.assertEqual(box.count("<a "), 1)
        self.assertIn('href="/artikel/ladd/"', box)
        self.assertIn(">Guide</h2>", box)

    def test_tag_chips_link_hubs_and_the_parent_brand(self):
        hubs = build.build_hubs([
            art("a", tags=["Model Y"], when=3),
            art("b", tags=["Tesla Model Y"], when=2),
            art("c", tags=["Model Y", "Tesla"], when=1),
        ])
        build.HUBS[:] = hubs
        links = [h["name"] for h in build.article_hub_links(art("c", tags=["Model Y"]))]
        self.assertEqual(links, ["Tesla", "Tesla Model Y"])
        html = build.tag_chips(art("ensam", tags=["Porsche"]))
        self.assertEqual(html, "")
        page = build.article(art("c", tags=["Model Y"], title="Model Y i test"))
        self.assertIn('href="/marke/tesla/"', page)
        self.assertIn('href="/modell/tesla-model-y/"', page)
        self.assertIn('class="article-tags"', page)

    def test_news_article_gets_a_guide_box_without_changing_the_prose(self):
        guide = art("guide-ladd", tags=["elbil", "laddning"], cat="elbil", typ="guide", when=1,
                    title="Vad kostar laddning", excerpt="Så räknar du.")
        build.GUIDES[:] = [guide]
        build.HUBS[:] = []
        news = art("nyhet", tags=["elbil"], cat="elbil", when=2, title="En nyhet")
        html = build.article(news, [news, guide])
        self.assertIn('class="guide-box"', html)
        self.assertIn('href="/artikel/guide-ladd/"', html)
        self.assertLess(html.index('class="prose"'), html.index('class="guide-box"'))
        self.assertIn("<p>Bröd.</p>", html)
        self.assertNotIn('class="related"', html)


if __name__ == "__main__":
    unittest.main()
