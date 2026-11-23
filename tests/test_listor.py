"""Listsidor ur listor/*.yaml: tabell, markeringar, JSON-LD och sitemap."""
import datetime as dt
import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location("motorpuls_build", os.path.join(ROOT, "build.py"))
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


def lists():
    return build.load_lists()


class ListPagesTest(unittest.TestCase):
    def setUp(self):
        self.lists = lists()
        self.by = {lst["slug"]: lst for lst in self.lists}
        self._saved = list(build.LISTS)
        build.LISTS[:] = self.lists

    def tearDown(self):
        build.LISTS[:] = self._saved

    def test_three_files_keep_their_slugs_and_checked_dates(self):
        self.assertEqual(
            [lst["slug"] for lst in self.lists],
            ["elbilar-dragkrok", "elbilar-under-400000", "rackvidd-kyla"])
        for lst in self.lists:
            self.assertEqual(lst["checked"], dt.date(2026, 11, 23))
            self.assertTrue(lst["rows"])

    def test_price_list_marks_only_flagged_rows(self):
        html = build.list_page(self.by["elbilar-under-400000"])
        body_rows = html.split("<tbody")[1].split("</tbody>")[0].split("<tr")
        prelim = [r for r in body_rows if "listmark--prelim" in r]
        kampanj = [r for r in body_rows if "listmark--kampanj" in r]
        self.assertEqual(len(prelim), 5)
        self.assertEqual(len(kampanj), 1)
        self.assertIn("Škoda Epiq", kampanj[0])
        self.assertIn("Preliminär WLTP", html)
        self.assertIn("Kampanjpris", html)
        self.assertIn("Markeringar", html)
        self.assertNotIn("listmark--kampanj", html.split("Citroën")[1].split("</tr>")[0])

    def test_other_lists_have_no_price_or_wltp_badges(self):
        for slug in ("elbilar-dragkrok", "rackvidd-kyla"):
            body = build.list_page(self.by[slug]).split("</head>", 1)[1]
            self.assertNotIn("listmark", body)
            self.assertNotIn("Markeringar", body)

    def test_page_has_table_sources_dates_and_sections(self):
        lst = self.by["elbilar-dragkrok"]
        html = build.list_page(lst)
        self.assertIn("<h1", html)
        self.assertIn(lst["title"].replace("2 500", "2\u00a0500"), html)
        self.assertIn("<caption>Modell, värde, källa och datum för kontroll.</caption>", html)
        self.assertIn('scope="col"', html)
        self.assertEqual(html.count('scope="row"'), len(lst["rows"]))
        self.assertEqual(html.count('data-label="Källa"'), len(lst["rows"]))
        self.assertEqual(html.count('data-label="Kontrollerad"'), len(lst["rows"]))
        self.assertIn("Senast kontrollerad", html)
        self.assertIn('datetime="2026-11-23"', html)
        self.assertIn(">23 november 2026</time>", html)
        self.assertIn("Så gjorde vi", html)
        self.assertIn("Osäkerheter", html)
        self.assertIn("Vanliga frågor", html)
        self.assertIn('"@type": "FAQPage"', html)
        self.assertIn('"@type": "ItemList"', html)
        self.assertIn('"@type": "BreadcrumbList"', html)
        self.assertIn('rel="canonical" href="https://motorpuls.se/listor/elbilar-dragkrok/"', html)
        self.assertIn('property="og:image" content="https://motorpuls.se/img/og/motorpuls.jpg"', html)
        self.assertIn("https://web.archive.org/web/20260513164712/", html)
        self.assertNotIn("\u2013", html)
        self.assertNotIn("\u2014", html)

    def test_source_query_is_escaped_and_linked(self):
        html = build.list_page(self.by["rackvidd-kyla"])
        self.assertIn("publisherId=2126680", html)
        self.assertIn("&amp;publisherId=2126680", html)
        self.assertIn('class="listsrc"', html)

    def test_index_footer_guides_and_sitemap(self):
        index = build.lists_index(self.lists)
        for lst in self.lists:
            self.assertIn(f'href="{lst["path"]}"', index)
        nav = build.topics_nav()
        self.assertIn('href="/listor/"', nav)
        self.assertIn(">Listor</a>", nav)
        self.assertIn('href="/verktyg/">Verktyg</a>', nav)
        guide = {
            "slug": "g", "title": "Guide", "url": "/artikel/g/", "excerpt": "x", "cat": "guider",
            "category": "Guider", "tags": [], "when": 1, "file": "g.md", "img": None,
            "published": "2026-11-01T00:00:00+01:00", "date": dt.date(2026, 11, 1),
        }
        guides = build.guides_page([guide])
        self.assertIn('href="/listor/">Listor</a>', guides)
        self.assertIn('href="/verktyg/laddkostnad/"', guides)
        xml = build.lists_sitemap(self.lists)
        self.assertIn("<loc>https://motorpuls.se/listor/</loc>", xml)
        for lst in self.lists:
            self.assertIn(f"<loc>https://motorpuls.se{lst['path']}</loc>", xml)
        self.assertEqual(xml.count("<lastmod>2026-11-23T00:00:00+01:00</lastmod>"), 4)
        self.assertNotIn("\u2013", index)
        self.assertNotIn("\u2014", index)


if __name__ == "__main__":
    unittest.main()
