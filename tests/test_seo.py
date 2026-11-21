"""Teknisk SEO: alt-text, bildlicens i JSON-LD, meta-beskrivning, guider i Läs också, schemalagd publicering.

Kör: python -m unittest tests/test_seo.py
"""
import datetime as dt
import importlib.util
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location("motorpuls_build", os.path.join(ROOT, "build.py"))
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


def article(slug, cat="elbil", tags=(), typ=None, when=1, title=None):
    return {"slug": slug, "cat": cat, "category": cat, "tags": list(tags), "type": typ,
            "when": when, "title": title or slug, "url": f"/artikel/{slug}/",
            "published": "2026-11-01T07:00:00+01:00", "date": dt.date(2026, 11, 1), "excerpt": "x"}


def image(**kw):
    base = dict(src="/img/x.webp", w=800, h=600, alt="Alt från front matter", credit="Foto: Test Testsson",
                license="", license_url="", license_name="", source_url="", caption="")
    base.update(kw)
    return base


class MetaDescTest(unittest.TestCase):
    def test_short_text_is_unchanged(self):
        self.assertEqual(build.meta_desc("Kort ingress."), "Kort ingress.")

    def test_cuts_on_a_word_and_stays_within_limit(self):
        text = " ".join(["ord"] * 80)
        out = build.meta_desc(text)
        self.assertLessEqual(len(out), build.META_DESC_MAX)
        self.assertTrue(out.endswith("…"))
        self.assertNotIn("ordord", out)
        self.assertTrue(out[:-1].endswith("ord"))

    def test_collapses_whitespace_without_cutting_a_short_text(self):
        self.assertEqual(build.meta_desc("En  rad.\nTvå."), "En rad. Två.")


class ImageRightsTest(unittest.TestCase):
    def test_cc_by_sa_maps_to_license_url_creator_and_source(self):
        im = image(
            credit="Foto: W.carter / Wikimedia Commons (CC BY-SA 4.0)",
            license="CC BY-SA 4.0, fri användning med namngivning och samma licens. Villkor: https://creativecommons.org/licenses/by-sa/4.0/",
            source_url="https://commons.wikimedia.org/wiki/File:Cars_at_a_charging_station_in_Lysekil_1.jpg")
        rights = build.image_rights(im)
        self.assertEqual(rights["license"], "https://creativecommons.org/licenses/by-sa/4.0/")
        self.assertEqual(rights["acquireLicensePage"], im["source_url"])
        self.assertEqual(rights["creator"], {"@type": "Person", "name": "W.carter"})
        self.assertIn("creditText", rights)

    def test_explicit_license_url_wins(self):
        im = image(license_name="CC BY-SA 3.0", license_url="https://creativecommons.org/licenses/by-sa/3.0/",
                   license="CC BY-SA 3.0, fri användning. Villkor: https://creativecommons.org/licenses/by-sa/3.0/")
        self.assertEqual(build.license_url_of(im), "https://creativecommons.org/licenses/by-sa/3.0/")

    def test_cc_token_without_url_is_mapped(self):
        self.assertEqual(build.cc_license_url("CC BY 4.0"), "https://creativecommons.org/licenses/by/4.0/")
        self.assertEqual(build.cc_license_url("CC0 1.0"), "https://creativecommons.org/publicdomain/zero/1.0/")

    def test_terms_url_is_license_even_when_it_is_also_the_source(self):
        url = "https://www.tesla.com/tesla-gallery"
        im = image(credit="Foto: Courtesy of Tesla, Inc.",
                   license="Endast redaktionell användning, villkor " + url,
                   source_url=url)
        rights = build.image_rights(im)
        self.assertEqual(rights["license"], url)
        self.assertEqual(rights["creator"], {"@type": "Organization", "name": "Tesla, Inc."})
        self.assertEqual(rights["acquireLicensePage"], url)

    def test_file_page_used_as_villkor_is_not_repeated_as_license(self):
        url = "https://commons.wikimedia.org/wiki/File:Studless_tire_2.jpg"
        im = image(credit="Foto: Lombroso / Wikimedia Commons (public domain)",
                   license=f"Public domain, fri användning utan krav på namngivning. Villkor: {url}",
                   source_url=url)
        rights = build.image_rights(im)
        self.assertNotIn("license", rights)
        self.assertEqual(rights["acquireLicensePage"], url)
        self.assertEqual(rights["creator"]["name"], "Lombroso")

    def test_omits_fields_without_data(self):
        rights = build.image_rights(image(credit="", license="", source_url="", alt="Bara alt"))
        self.assertEqual(rights, {})

    def test_markdown_credit_links_the_photographer_and_keeps_commons(self):
        im = image(
            credit="Foto: [Blogtrepreneur](https://howtostartablogonline.net/legal) / Wikimedia Commons (CC BY 2.0)",
            credit_url="https://commons.wikimedia.org/wiki/File:Legal_Contract_%26_Signature_-_Warm_Tones.jpg",
            license_name="CC BY 2.0",
            license_url="https://creativecommons.org/licenses/by/2.0/")
        html = build.caption(im)
        self.assertIn('href="https://howtostartablogonline.net/legal"', html)
        self.assertIn(">Blogtrepreneur</a>", html)
        self.assertIn('href="https://commons.wikimedia.org/wiki/File:Legal_Contract_%26_Signature_-_Warm_Tones.jpg"', html)
        self.assertIn(">Wikimedia Commons</a>", html)
        self.assertNotIn("[Blogtrepreneur]", html)
        rights = build.image_rights(im)
        self.assertEqual(rights["creator"], {"@type": "Person", "name": "Blogtrepreneur"})
        self.assertEqual(rights["creditText"], "Blogtrepreneur / Wikimedia Commons (CC BY 2.0)")
        a = article("avtal")
        a["img"] = im
        card = build.feed_item(a)
        self.assertIn("Foto: Blogtrepreneur / Wikimedia Commons (CC BY 2.0)", card)
        self.assertNotIn("howtostartablogonline", card)

    def test_plain_credit_stays_one_link(self):
        im = image(credit="Foto: Alexander-93, Wikimedia Commons",
                   credit_url="https://commons.wikimedia.org/wiki/File:X.jpg")
        html = build.caption(im)
        self.assertIn('href="https://commons.wikimedia.org/wiki/File:X.jpg" rel="noopener" target="_blank">Foto: Alexander-93, Wikimedia Commons</a>', html)
        self.assertEqual(html.count("<a "), 1)

    def test_organization_credits(self):
        self.assertEqual(build.creator_from_credit("Foto: Volvo Cars")["@type"], "Organization")
        self.assertEqual(build.creator_from_credit("Foto: Koenigsegg Automotive AB")["name"], "Koenigsegg Automotive AB")
        self.assertEqual(build.creator_from_credit("Foto: Calle Eklund/V-wolf / Wikimedia Commons (CC BY 3.0)")["name"],
                         "Calle Eklund/V-wolf")
        self.assertIsNone(build.creator_from_credit("Bild: Wikimedia Commons (allmän egendom)"))


class AltTextTest(unittest.TestCase):
    def test_feed_popular_and_related_use_front_matter_alt(self):
        a = article("bilen", title="Rubriken")
        a["img"] = image()
        self.assertIn('alt="Alt från front matter"', build.feed_item(a))
        self.assertIn('alt="Alt från front matter"', build.popular_card(a, 1))
        self.assertIn('alt="Alt från front matter"', build.related_card(a))

    def test_empty_alt_falls_back_to_title(self):
        a = article("bilen", title='Rubrik med "citat"')
        a["img"] = image(alt="  ")
        html = build.feed_item(a)
        self.assertIn("alt=\"Rubrik med &quot;citat&quot;\"", html)
        self.assertNotIn('alt=""', html)


class RelatedGuideTest(unittest.TestCase):
    def test_matching_guide_is_first(self):
        current = article("nyhet", cat="elbil", tags=["tesla", "model y"], when=5)
        guide = article("guide-laddning", cat="elbil", tags=["laddning"], typ="guide", when=1)
        closer = article("annan-tesla", cat="elbil", tags=["tesla", "model y"], when=9)
        other = article("f1", cat="motorsport", tags=["f1"], when=20)
        picked = [b["slug"] for b in build.related(current, [current, closer, other, guide])]
        self.assertEqual(picked[0], "guide-laddning")
        self.assertIn("annan-tesla", picked)

    def test_unrelated_guide_does_not_jump_the_queue(self):
        current = article("f1-nyhet", cat="motorsport", tags=["f1"], when=5)
        guide = article("guide-laddning", cat="elbil", tags=["laddning"], typ="guide", when=30)
        same = article("annan-f1", cat="motorsport", tags=["f1"], when=4)
        picked = [b["slug"] for b in build.related(current, [guide, same, current])]
        self.assertEqual(picked[0], "annan-f1")


class ScheduleTest(unittest.TestCase):
    def test_future_instant_is_not_published_yet(self):
        n = dt.datetime(2026, 11, 21, 8, 0, tzinfo=build.TZ)
        later = dt.datetime(2026, 11, 21, 12, 0, tzinfo=build.TZ)
        self.assertTrue(build.is_future(later.date(), later, n))
        self.assertFalse(build.is_future(n.date(), n, later))
        # Datum utan klockslag räknas som hela dagen och publiceras när dagen har börjat.
        self.assertFalse(build.is_future(n.date(), None, n))
        self.assertTrue(build.is_future(dt.date(2026, 11, 22), None, n))

    def test_load_articles_skips_future_file(self):
        path = os.path.join(ROOT, "content", "articles", "2099-01-01-framtida-test-ska-inte-publiceras.md")
        path = os.path.abspath(path)
        self.assertTrue(path.startswith(os.path.join(ROOT, "content", "articles")))
        text = """---
title: "Framtida test"
date: 2099-01-01T07:00:00+01:00
slug: framtida-test-ska-inte-publiceras
excerpt: "Inte publicerad än."
category: Elbil
author: Lukas
---

# Framtida test

En mening.
"""
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            arts = build.load_articles()
        finally:
            if os.path.exists(path):
                os.remove(path)
        self.assertTrue(arts)
        self.assertNotIn("framtida-test-ska-inte-publiceras", {a["slug"] for a in arts})
