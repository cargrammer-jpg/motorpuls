# Bygger Motorpuls från content/articles/*.md. Kör: .venv/bin/python build.py (kräver markdown och pyyaml).
#
# Utdata:
#   index.html                    startsida, riktiga artiklar, nyast först
#   artikel/<slug>/index.html     en sida per artikel (rena URL:er: /artikel/<slug>/)
#   404.html, sitemap.xml, robots.txt, feed.xml (RSS, samma artiklar som sitemap)
#   sitemap-news.xml              Google News-sitemap: bara artiklar publicerade de senaste 2 dygnen (Googles regel),
#                                 kan vara tom. Räknas vid bygget, så sajten behöver byggas om minst en gång per dygn (föreslaget schema i pages.yml, se PR:en).
#   om/, om/<författare>/         sidor ur content/pages/*.md (front matter: title, path, description, valfritt author).
#                                 En sida med author (id i data/authors.json) blir författarsida med ProfilePage-JSON-LD.
#   skribentruta                  längst ner i varje artikel, en mall (author_box) med data ur data/authors.json
#                                 Ord som TODO i texten ger en varning i bygget.
#   img/ld/<slug>-16x9.jpg m.fl.  bilder för NewsArticle-JSON-LD: huvudbilden beskuren till 16:9, 4:3 och 1:1, högst
#                                 1200 px bred, aldrig uppskalad (checka in dem tillsammans med artikeln, som img/og/)
#   feed/<kategori>.xml           RSS per kategori (och feed/sverige.xml när någon artikel har sweden: true)
#   sw.js, push.js                bara när PUSH_BOX är på (förhandsvisning av push-rutan, se nedan)
#   nyhetsbrev.js                 bara när NEWSLETTER_BOX är på (förhandsvisning av nyhetsbrevsrutan i sidfoten, se nedan)
#   img/og/<slug>.jpg             delningsbild 1200x630 (JPEG) ur huvudbilden; startsidan använder img/og/motorpuls.jpg
#                                 (ritad från brand/og/startsida.html)
#
# Artiklar: markdown med YAML-front matter (title, date, slug, tags, excerpt, category, author,
# valfritt summary, images, sources, äldre image/image_credit). Brödtexten renderas oförändrad. Rubriken (#) i texten
# blir sidans h1, avsnittet "## Källor" renderas i källistan. Fältet sources är valfritt, men finns det måste
# länkarna vara desamma som under "## Källor" (annars avbryts bygget). Ordning: publiceringstidpunkt (date med tid, ett datum utan tid räknas som
# dagens början), sedan filnamn, nyast först. Samma ordning gäller startsidan, feed.xml och sitemap.xml.
#
# date:    publiceringsdag (2026-10-30) eller tidpunkt med zon (2026-10-30T03:25:00+01:00). Tid utan zon räknas
#          som Europe/Stockholm. Bygget stoppas om datumet ligger i framtiden (svensk tid; ett datum utan tid
#          räknas som hela den dagen, så en artikel som mergas på sin egen dag går igenom). För förhandsbygge av
#          schemalagda artiklar: MOTORPULS_NOW=2026-11-05T07:10+01:00 .venv/bin/python build.py
# updated: valfritt, samma format som date. Blir dateModified (annars samma som date) och sitemaps lastmod, och
#          artikeln visar "Uppdaterad <datum>" i bylinen när tidpunkten är senare än date.
#
# sweden:  valfritt, true när nyheten gäller Sverige. Då visas en liten svensk flagga (äldre, mörkare färger)
#          som ett eget element ovanpå huvudbildens hörn och på startsidans kort, eller vid kategorin om
#          artikeln saknar bild. Bildfilerna ändras aldrig.
# summary: lista med 2 till 4 korta punkter (vanlig text), visas i rutan "Kort om nyheten".
# images:  lista med {src, alt, credit, license, valfritt caption}. src är en lokal fil: ett filnamn som
#          letas upp i drafts/img/<slug>/, utkastens form img/<slug>/fil (relativ till drafts/), en sökväg
#          relativ till projektroten eller en absolut sökväg. Okända fält (t.ex. source_url) ignoreras.
#          Filen kopieras till img/articles/<slug>/ och får WebP-versioner (1600, 800 och 400 px bred, bara
#          storleksändring, aldrig beskärning). Finns WebP-filen redan byggs den inte om (källan behövs inte).
#          Första bilden är huvudbild (og:image), fler bilder blir ett bildspel.
# image:   äldre fält (en URL). Laddas ned till img/articles/<slug>.webp om filen saknas, kredit i image_credit.
#
# Populärt: startsidans "Populärt just nu" tar artiklarna i data/popular.json i tur och ordning (skrivs av
# tools/update_popular.py från Cloudflare Web Analytics; okända slugs hoppas över). Saknas filen eller räcker den
# inte fylls det på med de senaste artiklarna som inte redan syns högst upp. Rutan visas när det finns minst 2.
#
# Publicering: GitHub Actions (.github/workflows/pages.yml) kör `python build.py --out _site`. Då byggs allt som vanligt
# i projektroten och sedan kopieras bara den publika delen till _site (genererade sidor, css, js, fonts, img, favicon,
# CNAME). Källor som build.py, content/, DESIGN.md, brand/ och drafts/ publiceras alltså inte. I --out-läget används
# även genererade bilder som inte är incheckade (WebP-varianter, img/og/<slug>.jpg), eftersom de följer med till _site.
# Till sist kontrolleras att varje lokal länk i sidorna, css:en och manifestet finns i _site (annars avbryts bygget).
# Utan --out fungerar allt som förut (resultatet skrivs i projektroten och checkas in).
import datetime as dt, glob, hashlib, html, json, math, os, re, shutil, sys, urllib.parse, urllib.request
import markdown, yaml
from zoneinfo import ZoneInfo

DRAFTS_IMG = os.environ.get("MOTORPULS_DRAFTS_IMG")  # valfri extra källmapp, standard: <root>/drafts/img

ROOT = os.path.dirname(os.path.abspath(__file__))
DOMAIN = "https://motorpuls.se"
SITE = "Motorpuls"
NEWS_LANG = "sv"      # news:language i sitemap-news.xml (ISO 639)
NEWS_DAYS = 2         # Google: bara artiklar från de senaste två dygnen i news-sitemapen
# Search Console, verifiering med HTML-tagg: klistra in content-värdet från Search Console (bara koden, inte hela
# taggen). Tom sträng ger ingen tagg. Taggen hamnar bara på startsidan.
GOOGLE_SITE_VERIFICATION = ""
SITE_DESC = "Korta, sakliga nyheter om elbilar, sportbilar, laddning och förnybara bränslen. Varje text länkar till sina källor."
MAX_W = 1600
VARIANTS = ((MAX_W, ""), (800, "-800"), (400, "-400"))  # bredd, filändelse; minsta används av miniatyrerna (104 px)

MONTHS = ["januari","februari","mars","april","maj","juni","juli","augusti","september","oktober","november","december"]
DAYS = ["måndag","tisdag","onsdag","torsdag","fredag","lördag","söndag"]
def sv_date(d): return f"{d.day} {MONTHS[d.month-1]} {d.year}"
def sv_day(d): return f"{DAYS[d.weekday()].capitalize()} {d.day} {MONTHS[d.month-1]}"
def host(u): return re.sub(r"^www\.", "", u.split("/")[2])
def esc(s): return html.escape(str(s), quote=True)
NUM_GAP = re.compile(r"(?<=\d) (?=\d{3}(?!\d))")
def nbnum(s):
    """Tusentalsavgränsare blir hårt mellanslag så att 1 079 aldrig bryts över två rader."""
    return NUM_GAP.sub("\u00a0", s)
def nbnum_html(h): return re.sub(r">[^<]+<", lambda m: nbnum(m.group(0)), ">" + h + "<")[1:-1]
def slugify(s): return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("å","a").replace("ä","a").replace("ö","o")).strip("-")

# ---------- feature-flaggor ----------
# PUSH_BOX: orange ruta "Få en notis när vi publicerar nyheter" (Web Push). AV i produktion. Utskicken är inte
# inkopplade (se supabase/README.md). Förhandsbygge med rutan på, bara till --out och aldrig till main:
#   MOTORPULS_PUSH=1 python build.py --out _preview
# När flaggan är av finns varken rutan, push.js, sw.js eller någon registrering av service worker i utdata
# (kontrolleras i check_no_push). PUSH_CONFIG fylls i först när ALX har godkänt backend; vapidPublicKey är den
# publika VAPID-nyckeln (den privata ligger bara som hemlighet i Supabase), subscribeUrl är Supabase REST för
# tabellen push_subscriptions och anonKey projektets publika nyckel (publishable). Tomma värden: rutan frågar om
# lov och registrerar service workern, men sparar ingen prenumeration.
PUSH_BOX = os.environ.get("MOTORPULS_PUSH") == "1"
PUSH_CONFIG = {"vapidPublicKey": "", "subscribeUrl": "", "anonKey": ""}
PUSH_SRC = os.path.join(ROOT, "push")  # källor för rutan: push.js, push.css, sw.js (publiceras inte som katalog)

# NEWSLETTER_BOX: orange nyhetsbrevsruta i sidfoten (e-postfält och knapp, höger om sidfotens text). AV i produktion,
# lanseringen väntar på ALX:s OK. Förhandsbygge med rutan på, bara till --out och aldrig till main:
#   MOTORPULS_NYHETSBREV=1 python build.py --out _preview
# När flaggan är av finns varken rutan, nyhetsbrev.js eller Supabase-adressen i utdata (kontrolleras i check_no_newsletter).
# NEWSLETTER_CONFIG: Supabase REST för tabellen public.newsletter_subscribers i projektet motorpuls (eu-north-1, samma som
# PR #15) och projektets publika nyckel (publishable, får synas i klienten; RLS ger anon bara INSERT med consent = true).
# Tomma värden: rutan visas men skickar inget. Utskick (t.ex. Resend) och integritetssidan är inte på plats än.
NEWSLETTER_BOX = os.environ.get("MOTORPULS_NYHETSBREV") == "1"
NEWSLETTER_CONFIG = {"url": "https://yhxnrcykinmuoqbgboda.supabase.co/rest/v1/newsletter_subscribers",
                     "key": "sb_publishable_obvTElRjWsEDBGP_aJ4dFA_8PcVkx1c"}
NEWSLETTER_SRC = os.path.join(ROOT, "nyhetsbrev")  # källor: nyhetsbrev.css, nyhetsbrev.js (publiceras inte som katalog)

ANALYTICS = """<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "bace28864ae04c6fa5e9f4a98ca70f94"}'></script><!-- End Cloudflare Web Analytics -->
"""

# ---------- content ----------
TZ = ZoneInfo("Europe/Stockholm")

def parse_when(v, path, field):
    """date/updated -> (lokalt datum, tidpunkt med zon eller None)"""
    try:
        if isinstance(v, dt.datetime): t = v
        elif isinstance(v, dt.date): return v, None
        else:
            s = str(v).strip()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s): return dt.date.fromisoformat(s), None
            t = dt.datetime.fromisoformat(s)
    except ValueError: raise SystemExit(f"{path}: ogiltigt {field}: {v!r}")
    t = t.replace(tzinfo=TZ) if t.tzinfo is None else t
    return t.astimezone(TZ).date(), t

def iso(d, t): return t.isoformat(timespec="seconds") if t else d.isoformat()

def instant(d, t):
    """jämförbar tidpunkt: tiden om den finns, annars dagens början i svensk tid"""
    return t if t else dt.datetime.combine(d, dt.time.min, TZ)

def lastmod(url, arts):
    """sitemap: artikelns updated/date, startsidan får den senaste av dem"""
    hit = [a for a in arts if a["url"] == url] or [max(arts, key=lambda a: a["mod_when"])]
    return hit[0]["modified"]

def now():
    n = os.environ.get("MOTORPULS_NOW")
    t = dt.datetime.fromisoformat(n) if n else dt.datetime.now(TZ)
    return t.replace(tzinfo=TZ) if t.tzinfo is None else t

def load_articles():
    arts = []
    for path in sorted(glob.glob(os.path.join(ROOT, "content/articles/*.md"))):
        raw = open(path, encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
        if not m: raise SystemExit(f"saknar front matter: {path}")
        fm, body = yaml.safe_load(m.group(1)), m.group(2)
        for k in ("title","date","slug","excerpt","category","author"):
            if not fm.get(k): raise SystemExit(f"{path}: saknar {k}")
        check_summary_images(fm, path)
        if "sweden" in fm and not isinstance(fm["sweden"], bool): raise SystemExit(f"{path}: sweden ska vara true eller false")
        d, t = parse_when(fm["date"], path, "date")
        n = now()
        if (t and t > n) or d > n.astimezone(TZ).date():
            raise SystemExit(f"{path}: date {iso(d, t)} ligger i framtiden (nu {n.astimezone(TZ):%Y-%m-%d %H:%M} svensk tid)")
        ud, ut = parse_when(fm["updated"], path, "updated") if fm.get("updated") else (d, t)
        # h1 in the body is the page headline; "## Källor" becomes the source list
        h1 = re.search(r"^# (.+)$", body, re.M)
        headline = h1.group(1).strip() if h1 else fm["title"]
        if h1: body = body[:h1.start()] + body[h1.end():]
        sources = []
        ks = re.search(r"^## Källor\s*$", body, re.M)
        if ks:
            for line in body[ks.end():].splitlines():
                lm = re.match(r"^\s*[-*]\s+\[(.+?)\]\((\S+?)\)\s*$", line)
                if lm: sources.append((lm.group(1), lm.group(2)))
                elif line.strip(): raise SystemExit(f"{path}: oväntad rad i Källor: {line!r}")
            body = body[:ks.start()]
        check_sources(fm, sources, path)
        words = len(re.findall(r"\w+", body))
        arts.append(dict(fm, date=d, published=iso(d, t), modified=iso(ud, ut), mod_date=ud, when=instant(d, t), mod_when=instant(ud, ut), headline=headline, body_html=markdown.markdown(body.strip()),
                         sources=sources, file=os.path.basename(path), minutes=max(1, math.ceil(words/200)),
                         url=f"/artikel/{fm['slug']}/", cat=slugify(fm["category"])))
    arts.sort(key=lambda a: (a["when"], a["file"]), reverse=True)
    if len({a["slug"] for a in arts}) != len(arts): raise SystemExit("dubbla slugs")
    return arts

def check_sources(fm, sources, path):
    """Front matter-fältet sources är valfritt. Finns det ska det vara samma länkar som under "## Källor"
    (det är Källor-listan som visas på sidan och hamnar i JSON-LD)."""
    fs = fm.get("sources")
    if fs is None: return
    if not isinstance(fs, list) or not all(isinstance(u, str) for u in fs):
        raise SystemExit(f"{path}: sources ska vara en lista med länkar")
    shown = [u for _, u in sources]
    if set(fs) != set(shown):
        raise SystemExit(f"{path}: sources i front matter stämmer inte med ## Källor "
                         f"(saknas i Källor: {sorted(set(fs) - set(shown))}, saknas i sources: {sorted(set(shown) - set(fs))})")

def check_summary_images(fm, path):
    sm = fm.get("summary")
    if sm is not None:
        if isinstance(sm, str) or not isinstance(sm, list) or not 2 <= len(sm) <= 4 or not all(isinstance(x, str) and x.strip() for x in sm):
            raise SystemExit(f"{path}: summary ska vara en lista med 2 till 4 punkter (text)")
    ims = fm.get("images")
    if ims is not None:
        if not isinstance(ims, list) or not ims: raise SystemExit(f"{path}: images ska vara en lista")
        for i, im in enumerate(ims, 1):
            if not isinstance(im, dict): raise SystemExit(f"{path}: images[{i}] ska ha src, alt, credit, license")
            for k in ("src", "alt", "credit"):
                if not str(im.get(k) or "").strip(): raise SystemExit(f"{path}: images[{i}] saknar {k}")
            if not str(im.get("license") or "").strip(): print(f"varning: {path}: images[{i}] saknar license")

def webp_variants(src_path, out_base):
    """Skriver <out_base>.webp (max 1600 px), <out_base>-800.webp och <out_base>-400.webp (de mindre bara om
    bilden är bredare än så).
    Samma bildformat: bara storleksändring, aldrig beskärning."""
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = None  # pressbilder kan vara över 100 megapixel, källorna är våra egna filer
    im = Image.open(src_path); im.load()
    im = ImageOps.exif_transpose(im)  # följ EXIF-orienteringen (vrider bara, beskär aldrig)
    icc = im.info.get("icc_profile")  # färgprofilen följer med oförändrad (t.ex. Adobe RGB, P3), inga färgändringar
    if im.mode not in ("RGB", "RGBA"): im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
    for w, suffix in VARIANTS:
        if suffix and im.width <= w: continue
        tw = min(w, im.width)
        if tw == im.width and src_path.lower().endswith(".webp"):  # redan WebP i rätt storlek: kopiera, koda inte om
            shutil.copyfile(src_path, os.path.join(ROOT, f"{out_base}{suffix}.webp")); continue
        r = im if tw == im.width else im.resize((tw, round(im.height * tw / im.width)), Image.LANCZOS)
        r.save(os.path.join(ROOT, f"{out_base}{suffix}.webp"), "WEBP", quality=86, method=6, **({"icc_profile": icc} if icc else {}))

def small_variants(out_base):
    """Äldre bilder byggda innan en mindre storlek fanns: skapa den ur den största WebP-filen (bara storleksändring)."""
    from PIL import Image
    main = os.path.join(ROOT, out_base + ".webp")
    if not os.path.exists(main): return
    with Image.open(main) as im:
        for w, suffix in VARIANTS[1:]:
            p = os.path.join(ROOT, f"{out_base}{suffix}.webp")
            if im.width > w and not os.path.exists(p):
                icc = im.info.get("icc_profile")
                im.resize((w, round(im.height * w / im.width)), Image.LANCZOS).save(p, "WEBP", quality=86, method=6, **({"icc_profile": icc} if icc else {}))

_tracked = None
OUT = None          # utkatalog (--out), sätts i main()
WRITTEN = []        # sidor och filer som bygget skrivit (relativa sökvägar), publiceras med --out
PUBLIC_DIRS = ("css", "js", "fonts", "img", "favicon")
PUBLIC_FILES = ("favicon.ico", "CNAME")

def committed(rel):
    """Sant om filen finns i git (eller om vi inte bygger i ett git-repo). En ny variant som inte är incheckad
    hamnar inte i srcset, så sajten pekar aldrig på en fil som saknas på GitHub Pages."""
    global _tracked
    if OUT: return os.path.exists(os.path.join(ROOT, rel))  # --out: allt som finns följer med till _site
    if _tracked is None:
        try:
            import subprocess
            out = subprocess.run(["git", "ls-files", "-z", "img"], cwd=ROOT, capture_output=True, check=True).stdout
            _tracked = set(out.decode().split("\0"))
        except Exception: _tracked = False
    return _tracked is False or rel in _tracked

def read_variants(out_base):
    from PIL import Image
    res = []
    for _, suffix in VARIANTS:
        rel = f"{out_base}{suffix}.webp"
        p = os.path.join(ROOT, rel)
        if os.path.exists(p) and (not suffix or committed(rel)):
            with Image.open(p) as im: res.append(("/" + rel, im.width, im.height))
    return res

def find_source(src, slug):
    if os.path.isabs(src): cands = [src]
    else:
        cands = [os.path.join(ROOT, src)] if "/" in src else []
        if src.startswith("img/"):  # utkastens form: img/<slug>/fil, relativ till drafts/
            for base in [DRAFTS_IMG, os.path.join(ROOT, "drafts/img")]:
                if base: cands.append(os.path.join(base, src[len("img/"):]))
        name = os.path.basename(src)
        for base in [DRAFTS_IMG, os.path.join(ROOT, "drafts/img")]:
            if base: cands.append(os.path.join(base, slug, name))
    return next((c for c in cands if os.path.isfile(c)), None), cands

def ensure_images(a):
    """Bilder för en artikel: lista med dict(src, w, h, srcset, alt, credit, caption, license). Tom lista om inga."""
    slug = a["slug"]
    if a.get("images"):
        res, seen = [], set()
        os.makedirs(os.path.join(ROOT, f"img/articles/{slug}"), exist_ok=True)
        for i, im in enumerate(a["images"], 1):
            src = str(im["src"]).strip()
            stem = slugify(os.path.splitext(os.path.basename(src))[0]) or f"bild-{i}"
            if stem in seen: stem = f"{stem}-{i}"
            seen.add(stem)
            out_base = f"img/articles/{slug}/{stem}"
            found, cands = find_source(src, slug)
            have = os.path.exists(os.path.join(ROOT, out_base + ".webp"))
            if found:  # originalet kopieras inte in i sajten, bara WebP-versionerna skrivs
                if not have or os.path.getmtime(found) > os.path.getmtime(os.path.join(ROOT, out_base + ".webp")):
                    webp_variants(found, out_base)
            elif not have:
                raise SystemExit(f"{a['file']}: hittar inte bilden {src!r} (letade i: {', '.join(cands)})")
            small_variants(out_base)
            v = read_variants(out_base)
            res.append(dict(src=v[0][0], w=v[0][1], h=v[0][2], srcset=", ".join(f"{u} {w}w" for u, w, _ in reversed(v)),
                            alt=str(im["alt"]).strip(), credit=str(im["credit"]).strip(),
                            caption=str(im.get("caption") or "").strip(), license=str(im.get("license") or "").strip()))
        return res
    if not a.get("image"): return []
    # äldre fält: en bild-URL
    rel = f"img/articles/{slug}.webp"
    out = os.path.join(ROOT, rel)
    if not os.path.exists(out):
        from PIL import Image
        os.makedirs(os.path.dirname(out), exist_ok=True)
        req = urllib.request.Request(a["image"], headers={"User-Agent": "Mozilla/5.0 (Motorpuls build)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data, ctype = r.read(), r.headers.get("Content-Type", "")
        ext = {"image/webp":"webp","image/png":"png","image/jpeg":"jpg"}.get(ctype.split(";")[0], "bin")
        orig = os.path.join(ROOT, f"img/articles/{slug}-original.{ext}")
        open(orig, "wb").write(data)
        im = Image.open(orig); im.load()
        if im.width > MAX_W:  # same aspect ratio, resize only
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        im.convert("RGB").save(out, "WEBP", quality=86, method=6)
    from PIL import Image
    with Image.open(out) as im: w, h = im.size
    return [dict(src="/" + rel, w=w, h=h, srcset="", alt=a["headline"], credit=str(a.get("image_credit") or "").strip(),
                 caption="", license=str(a.get("image_license") or "").strip())]

OG_W, OG_H = 1200, 630
DEFAULT_OG = dict(src="/img/og/motorpuls.jpg", w=OG_W, h=OG_H)

def og_image(a):
    """Delningsbild: huvudbilden beskuren till 1200x630 som JPEG (bara för og:image/twitter:image, sajtens bilder
    beskärs aldrig). Skrivs om den saknas. Används bara om filen är incheckad, annars WebP-huvudbilden som förut."""
    img = a["img"]
    if not img: return None
    rel = f"img/og/{a['slug']}.jpg"
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        from PIL import Image, ImageOps
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with Image.open(os.path.join(ROOT, img["src"].lstrip("/"))) as im:
            ImageOps.fit(im.convert("RGB"), (OG_W, OG_H), Image.LANCZOS).save(p, "JPEG", quality=85, optimize=True, progressive=True)
    return dict(src="/" + rel, w=OG_W, h=OG_H) if committed(rel) else img

def short_title(t, limit=60):
    """<title>: artikelrubriken kortas så att hela titeln med " · Motorpuls" blir högst ~60 tecken. Helst vid
    ": " eller ". " (utan …), annars vid ett ordslut med …. og:title och twitter:title behåller hela rubriken."""
    suffix = f" · {SITE}"
    room = limit - len(suffix)
    if len(t) <= room: return t + suffix
    head_part = re.split(r"[:.] ", t, maxsplit=1)[0]
    if head_part != t and room // 2 <= len(head_part) <= room: return head_part + suffix
    return t[:room - 1].rsplit(" ", 1)[0].rstrip(" ,.:;–-") + "…" + suffix

def rss(arts, title=SITE, desc=SITE_DESC, path="/feed.xml", link="/"):
    from email.utils import format_datetime
    def rfc822(iso_s):
        t = dt.datetime.fromisoformat(iso_s)
        return format_datetime(t.replace(tzinfo=TZ) if t.tzinfo is None else t)
    items = "".join(f"""  <item>
    <title>{esc(a["title"])}</title>
    <link>{DOMAIN}{a["url"]}</link>
    <guid isPermaLink="true">{DOMAIN}{a["url"]}</guid>
    <pubDate>{rfc822(a["published"])}</pubDate>
    <category>{esc(a["category"])}</category>
    <description>{esc(a["excerpt"])}</description>
  </item>
""" for a in arts)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{esc(title)}</title>
  <link>{DOMAIN}{link}</link>
  <description>{esc(desc)}</description>
  <language>sv-SE</language>
  <lastBuildDate>{rfc822(lastmod("/", arts))}</lastBuildDate>
  <atom:link href="{DOMAIN}{path}" rel="self" type="application/rss+xml"/>
{items}</channel>
</rss>
"""

FEEDS = []  # kategoriflöden: dict(key, name, path, arts), sätts i main()

def category_feeds(arts):
    """Ett RSS-flöde per kategori (feed/<kategori>.xml), i samma ordning som kategorierna först dyker upp, plus
    feed/sverige.xml när minst en artikel har sweden: true. Tomma flöden skrivs aldrig."""
    groups = {}
    for a in arts: groups.setdefault(a["cat"], (a["category"], []))[1].append(a)
    feeds = [dict(key=k, name=n, path=f"/feed/{k}.xml", arts=g) for k, (n, g) in groups.items()]
    sv = [a for a in arts if a.get("sweden")]
    if sv and "sverige" not in groups: feeds.append(dict(key="sverige", name="Sverige", path="/feed/sverige.xml", arts=sv))
    return feeds

def feed_for(a):
    return next(f for f in FEEDS if f["key"] == a["cat"])

def feed_links(feeds):
    return "".join(f'<link rel="alternate" type="application/rss+xml" title="{SITE}: {esc(f["name"])}" href="{f["path"]}">\n' for f in feeds)

RSS_SVG = ('<svg class="rss-icon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false">'
           '<rect width="16" height="16" rx="3" fill="#FF5B1F"/><circle cx="4.6" cy="11.4" r="1.5" fill="#0B0D10"/>'
           '<path d="M3.2 7.1a5.7 5.7 0 0 1 5.7 5.7M3.2 3.6a9.2 9.2 0 0 1 9.2 9.2" fill="none" stroke="#0B0D10" stroke-width="1.8" stroke-linecap="round"/></svg>')

def rss_row(a):
    """Rad i slutet av artikeln: kategorins flöde och hela sajtens flöde."""
    f = feed_for(a)
    return (f'\n        <p class="rss-row">{RSS_SVG}<span>Prenumerera via RSS:</span> '
            f'<a href="{f["path"]}">{esc(f["name"])}</a><span aria-hidden="true">·</span><a href="/feed.xml">Alla nyheter</a></p>')

# ---------- push (förhandsvisning, PUSH_BOX) ----------
def push_src(name): return open(os.path.join(PUSH_SRC, name), encoding="utf-8").read()

def push_head():
    if not PUSH_BOX: return ""
    return f'<style>{push_src("push.css")}</style>\n<script src="/push.js?v={hashlib.sha256(push_src("push.js").encode()).hexdigest()[:10]}" defer></script>\n'

def push_box(where):
    """where: "article" (i flödet efter texten) eller "front" (fast ruta nere, visas efter en stunds skrollning)."""
    if not PUSH_BOX: return ""
    cfg = esc(json.dumps(PUSH_CONFIG, separators=(",", ":")))
    cls = "pushb pushb--toast" if where == "front" else "pushb"
    return f'''
<section class="{cls}" id="push" aria-labelledby="push-h" data-config="{cfg}" hidden>
  <p class="pushb__kicker">Notiser</p>
  <h2 id="push-h">Få en notis när vi publicerar nyheter</h2>
  <p class="pushb__lede">En kort notis i din telefon eller dator, bara när en ny artikel är ute. Stäng av när du vill.</p>
  <p class="pushb__ios">På iPhone fungerar notiser när Motorpuls ligger på hemskärmen. Tryck på Dela <span aria-hidden="true">(rutan med pilen)</span> och välj Lägg till på hemskärmen. Öppna sedan Motorpuls därifrån.</p>
  <div class="pushb__row">
    <button class="pushb__btn pushb__yes" type="button" data-push="ja">Ja tack</button>
    <button class="pushb__btn pushb__btn--ghost" type="button" data-push="nej">Inte nu</button>
  </div>
  <p class="pushb__status" role="status" aria-live="polite"></p>
</section>'''

# ---------- nyhetsbrev i sidfoten (förhandsvisning, NEWSLETTER_BOX) ----------
def nl_src(name): return open(os.path.join(NEWSLETTER_SRC, name), encoding="utf-8").read()

def newsletter_head():
    if not NEWSLETTER_BOX: return ""
    return (f'<style>{nl_src("nyhetsbrev.css")}</style>\n<noscript><style>.nlf__form{{display:none}}</style></noscript>\n'
            f'<script src="/nyhetsbrev.js?v={hashlib.sha256(nl_src("nyhetsbrev.js").encode()).hexdigest()[:10]}" defer></script>\n')

def newsletter_box():
    if not NEWSLETTER_BOX: return ""
    cfg = esc(json.dumps(NEWSLETTER_CONFIG, separators=(",", ":")))
    return f'''
    <section class="nlf" id="nyhetsbrev-fot" aria-labelledby="nlf-h" data-config="{cfg}">
      <p class="nlf__kicker">Nyhetsbrev</p>
      <h2 id="nlf-h">Få Motorpuls i inkorgen</h2>
      <p class="nlf__lede">De viktigaste bilnyheterna, korta och med källor. Du hänger med utan att leta.</p>
      <noscript><p class="nlf__fine">Anmälan kräver JavaScript.</p></noscript>
      <form class="nlf__form" novalidate>
        <label class="nlf__label" for="nlf-email">Din e-postadress</label>
        <div class="nlf__row">
          <input class="nlf__input" id="nlf-email" type="email" name="email" inputmode="email" autocomplete="email" maxlength="254" required placeholder="namn@exempel.se" aria-describedby="nlf-fine">
          <button class="nlf__btn" type="submit">Prenumerera</button>
        </div>
        <div class="nlf__hp" aria-hidden="true"><label>Lämna tomt <input type="text" name="webbplats" tabindex="-1" autocomplete="off"></label></div>
        <p class="nlf__fine" id="nlf-fine">Gratis. Avsluta när du vill.</p>
        <p class="nlf__status" role="status" aria-live="polite"></p>
      </form>
    </section>'''

# ---------- shared html ----------
def asset(rel):
    """URL med ?v=<kort innehållshash> så att webbläsare (Safari) alltid hämtar aktuell css/js efter en ändring."""
    with open(os.path.join(ROOT, rel.lstrip("/")), "rb") as f:
        return f"{rel}?v={hashlib.sha256(f.read()).hexdigest()[:10]}"


def head(title, desc, path, og_type="website", image=None, extra="", preload_img=None, og_title=None, preload_sizes="100vw", noindex=False, robots=None, feeds=()):
    canon = DOMAIN + path if path else None
    og_title = og_title or title
    og_img = ""
    if image:
        og_img = (f'<meta property="og:image" content="{DOMAIN}{image["src"]}">\n'
                  f'<meta property="og:image:width" content="{image["w"]}">\n<meta property="og:image:height" content="{image["h"]}">\n'
                  f'<meta name="twitter:image" content="{DOMAIN}{image["src"]}">\n')
    pre = ""
    if preload_img:
        ss = f' imagesrcset="{preload_img["srcset"]}" imagesizes="{preload_sizes}"' if preload_img.get("srcset") else ""
        pre = f'<link rel="preload" as="image" href="{preload_img["src"]}"{ss} fetchpriority="high">\n'

    return f'''<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{f'<meta name="robots" content="{"noindex" if noindex else robots}">' + chr(10) if noindex or robots else ""}{f'<link rel="canonical" href="{canon}">' + chr(10) if canon else ""}{f'<meta name="google-site-verification" content="{esc(GOOGLE_SITE_VERIFICATION)}">' + chr(10) if GOOGLE_SITE_VERIFICATION and path == "/" else ""}<meta property="og:site_name" content="{SITE}">
<meta property="og:locale" content="sv_SE">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(og_title)}">
<meta property="og:description" content="{esc(desc)}">
{f'<meta property="og:url" content="{canon}">' + chr(10) if canon else ""}{og_img}<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}">
<meta name="twitter:title" content="{esc(og_title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="theme-color" content="#0B0D10">
<meta name="color-scheme" content="dark">
<link rel="stylesheet" href="{asset("/css/site.css")}">
<script src="{asset("/js/site.js")}" defer></script>
<link rel="icon" href="/favicon/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="/favicon/favicon-16.png" sizes="16x16" type="image/png">
<link rel="apple-touch-icon" href="/favicon/apple-touch-icon.png">
<link rel="manifest" href="/favicon/site.webmanifest">
<link rel="alternate" type="application/rss+xml" title="{SITE}" href="/feed.xml">
{feed_links(feeds)}<link rel="preload" href="/fonts/newsreader-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/fonts/archivo-var.woff2" as="font" type="font/woff2" crossorigin>
{pre}{push_head()}{newsletter_head()}{extra}</head>
<body>
<a class="skip" href="#innehall">Hoppa till innehållet</a>
<header class="masthead">
  <div class="wrap masthead__row">
    <a class="wordmark" href="/"><img class="logo" src="/img/logo.svg" alt="Motorpuls" width="872" height="88">{BANNER_FLAG_SVG}</a>
  </div>
</header>
'''

def footer():
    cats = "".join(f'<li><a href="{f["path"]}">{esc(f["name"])}</a></li>' for f in FEEDS)
    per_cat = (f'\n      <span class="site-footer__feeds-label" id="rss-kat">RSS per kategori:</span>'
               f'\n      <ul class="site-footer__feeds" aria-labelledby="rss-kat">{cats}</ul>') if FEEDS else ""
    main_open, main_close = ('<div class="site-footer__main">\n    ', '\n    </div>') if NEWSLETTER_BOX else ("", "")
    return f'''
<footer class="site-footer{" site-footer--nl" if NEWSLETTER_BOX else ""}">
  <div class="wrap">
    {main_open}<a class="wordmark" href="/"><img class="logo logo--footer" src="/img/logo.svg" alt="Motorpuls" width="872" height="88" loading="lazy"></a>
    <p class="site-footer__desc">{SITE_DESC}</p>
    <nav class="site-footer__nav" aria-label="Om Motorpuls"><ul><li><a href="/om/">Om Motorpuls</a></li><li><a href="/om/lukas/">Om Lukas</a></li></ul></nav>
    <div class="site-footer__rss">
      <a class="rss-link" href="/feed.xml">{RSS_SVG}RSS</a>{per_cat}
    </div>
    <p class="fine">© {dt.date.today().year} Motorpuls</p>{main_close}{newsletter_box()}
  </div>
</footer>
'''

def page(h, body): return h + body + footer() + ANALYTICS + "</body>\n</html>\n"

def meta_line(a, with_date=True, flag_html=""):
    t = f'<time datetime="{a["published"]}">{sv_date(a["date"])}</time>' if with_date else ""
    return f'<span class="meta"><span class="tag">{esc(a["category"])}</span>{flag_html}{t}</span>'

def img_tag(img, alt, eager=False, sizes="100vw"):
    load = 'fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"'
    ss = f' srcset="{img["srcset"]}" sizes="{sizes}"' if img.get("srcset") else ""
    return f'<img src="{img["src"]}"{ss} width="{img["w"]}" height="{img["h"]}" alt="{esc(alt)}" {load}>'

# Svensk flagga, äldre mörkare färger: blå #005293, gul #FECB00. Proportioner 5:2:9 och 4:2:4 (16x10).
# Ett eget DOM-element ovanpå bilden (bildfilen ändras aldrig), placeras med CSS (.flag--*).
FLAG_SVG = ('<svg viewBox="0 0 16 10" width="16" height="10" aria-hidden="true" focusable="false">'
            '<rect width="16" height="10" fill="#005293"/><rect x="5" width="2" height="10" fill="#FECB00"/>'
            '<rect y="4" width="16" height="2" fill="#FECB00"/></svg>')
# Svensk flagga efter loggan i sidhuvudet (dekorativ, aria-hidden). Mörk marinblå #0A2260 (ALX:s referens) och gul
# #FECC00, samma proportioner som FLAG_SVG. Artiklarnas flagga (FLAG_SVG) är oförändrad. Storlek och läge i
# css/site.css (.wordmark__flag).
BANNER_FLAG_SVG = ('<svg class="wordmark__flag" viewBox="0 0 16 10" width="16" height="10" aria-hidden="true" focusable="false">'
                   '<rect width="16" height="10" fill="#0A2260"/><rect x="5" width="2" height="10" fill="#FECC00"/>'
                   '<rect y="4" width="16" height="2" fill="#FECC00"/></svg>')
def flag(a, where):
    if not a.get("sweden"): return ""
    return f'<span class="flag flag--{where}" role="img" aria-label="Gäller Sverige" title="Gäller Sverige">{FLAG_SVG}</span>'

def meta_flag(a, has_img):
    """Utan bild hamnar flaggan vid kategorin."""
    return "" if has_img else flag(a, "inline")

# ---------- front page ----------
LEAD_SIZES = "(min-width: 60rem) 38rem, 100vw"
def lead(a):
    img = a["img"]
    media = (f'<figure class="lead__media"><div class="lead__frame">{flag(a, "lead")}{img_tag(img, img["alt"], eager=True, sizes=LEAD_SIZES)}</div>'
             f'<figcaption>{esc(img["credit"])}</figcaption></figure>') if img else ""
    return f'''
    <article class="lead{" lead--img" if img else " lead--text"}">
      <a href="{a["url"]}">
        {media}
        <div class="lead__body">
          <div class="lead__kicker"><span class="hero__label"><span class="pulse-dot" aria-hidden="true"></span>Senaste nytt</span>
          {meta_line(a, flag_html=meta_flag(a, img))}</div>
          <h2 class="lead__title">{nbnum(esc(a["title"]))}</h2>
          <p class="lead__dek">{nbnum(esc(a["excerpt"]))}</p>
          <span class="lead__more">Läs artikeln <span aria-hidden="true">→</span></span>
        </div>
      </a>
    </article>'''

def feed_item(a):
    # krediten visas vid varje bild, även miniatyrer (villkor för pressbilder och CC-licenser)
    thumb = (f'<figure class="item__img">{flag(a, "thumb")}{img_tag(a["img"], "", sizes="(min-width: 48rem) 15rem, 6.5rem")}'
             f'<figcaption class="item__credit">{esc(a["img"]["credit"])}</figcaption></figure>') if a["img"] else ""
    return f'''
          <li class="item{"" if a["img"] else " item--noimg"}" data-cat="{a["cat"]}">
            <a href="{a["url"]}">
              <div class="item__text">
                {meta_line(a, with_date=False, flag_html=meta_flag(a, a["img"]))}
                <h4>{esc(a["title"])}</h4>
                <p>{esc(a["excerpt"])}</p>
              </div>
              {thumb}
            </a>
          </li>'''

POPULAR_MAX = 4
POP_SIZES = "(min-width: 60rem) 17rem, (min-width: 40rem) 30vw, 46vw"

def popular_slugs():
    p = os.path.join(ROOT, "data/popular.json")
    if not os.path.exists(p): return []
    try: d = json.load(open(p, encoding="utf-8"))
    except ValueError as e: raise SystemExit(f"data/popular.json: {e}")
    items = d.get("articles", d) if isinstance(d, dict) else d
    return [x["slug"] if isinstance(x, dict) else x for x in items]

def pick_popular(arts, shown):
    """Populära först (i filens ordning), sedan de senaste som inte redan syns, sist de som syns i Senaste-listan."""
    by_slug = {a["slug"]: a for a in arts}
    picked = [by_slug[s] for s in dict.fromkeys(popular_slugs()) if s in by_slug]
    picked += [a for a in arts if a not in picked and a["slug"] not in shown]
    picked += [a for a in arts[1:] if a not in picked]
    return picked[:POPULAR_MAX]

def popular_card(a, rank):
    img = a["img"]
    media = (f'<figure class="pop__media"><div class="pop__frame">{flag(a, "thumb")}{img_tag(img, "", sizes=POP_SIZES)}</div>'
             f'<figcaption class="item__credit">{esc(img["credit"])}</figcaption></figure>') if img else ""
    return f'''
        <li class="pop__card{"" if img else " pop__card--noimg"}">
          <a href="{a["url"]}">
            {media}
            <div class="pop__body">
              <span class="meta"><span class="pop__rank" aria-hidden="true">{rank:02d}</span><span class="tag">{esc(a["category"])}</span>{meta_flag(a, img)}</span>
              <h3>{esc(a["title"])}</h3>
            </div>
          </a>
        </li>'''

def popular_section(arts, shown):
    pop = pick_popular(arts, shown)
    if len(pop) < 2: return ""
    return f'''
    <section class="pop" aria-labelledby="pop-h">
      <h2 id="pop-h"><span class="pulse-dot" aria-hidden="true"></span>Populärt just nu</h2>
      <ol class="pop__list">{"".join(popular_card(a, i) for i, a in enumerate(pop, 1))}
      </ol>
    </section>'''

def index(arts):
    first, rest = arts[0], arts[1:]
    h = head(f"{SITE}: korta bilnyheter med källor", SITE_DESC, "/", image=DEFAULT_OG,
             preload_img=first["img"], preload_sizes=LEAD_SIZES, feeds=FEEDS)
    if rest:
        side = f'<aside class="latest" aria-labelledby="latest-h"><h2 id="latest-h"><span class="pulse-dot" aria-hidden="true"></span>Senaste</h2><ol>' + "".join(
            f'<li><a href="{a["url"]}">{meta_line(a, flag_html=flag(a, "inline"))}<h3>{esc(a["title"])}</h3></a></li>' for a in rest[:5]) + "</ol></aside>"
    else:
        side = ""  # one article: the lead card stands alone
    feed = ""
    if len(arts) > 1:
        days, order = {}, []
        for a in arts:
            if a["date"] not in days: days[a["date"]] = []; order.append(a["date"])
            days[a["date"]].append(a)
        cats = []
        for a in arts:
            if (a["cat"], a["category"]) not in cats: cats.append((a["cat"], a["category"]))
        chips = ""
        if len(cats) > 1:
            chips = ('<nav aria-label="Kategorier"><ul class="chips"><li><button class="chip" type="button" data-filter="alla" aria-pressed="true">Alla</button></li>'
                     + "".join(f'<li><button class="chip" type="button" data-filter="{k}" aria-pressed="false">{esc(v)}</button></li>' for k, v in cats) + "</ul></nav>")
        sections = "".join(f'''
      <section class="day" aria-labelledby="d-{d.isoformat()}">
        <h3 class="day__label" id="d-{d.isoformat()}"><time datetime="{d.isoformat()}">{sv_day(d)}</time></h3>
        <ol class="feed">{"".join(feed_item(a) for a in days[d])}
        </ol>
      </section>''' for d in order)
        feed = f'''
  <section class="feed-section" id="flodet" aria-labelledby="feed-h">
    <div class="wrap">
      <div class="section-head">
        <h2 id="feed-h">Alla artiklar</h2>
        {chips}
      </div>
      <p id="filter-status" class="visually-hidden" role="status" aria-live="polite"></p>
      {sections}
    </div>
  </section>'''
    body = f'''
<main id="innehall" class="front{" front--single" if not rest else ""}">
  <div class="wrap">
    <h1 class="visually-hidden">Motorpuls, senaste bilnyheterna</h1>
    <div class="hero-grid">{lead(first)}
      {side}
    </div>{popular_section(arts, {first["slug"]} | {a["slug"] for a in rest[:5]})}
  </div>
{feed}
</main>{push_box("front")}
'''
    return page(h, body)

# ---------- article ----------
HERO_SIZES = "(min-width: 66rem) 62rem, calc(100vw - 2.5rem)"

def caption(im):
    parts = [esc(x) for x in (im["caption"], im["credit"]) if x]
    return f'<figcaption><span>{" <span aria-hidden=\"true\">·</span> ".join(parts)}</span></figcaption>' if parts else ""

def gallery(imgs, flag_html=""):
    """En bild: figur i bildens eget format. Flera: bildspel (scroll-snap, utan JS en rad att svepa i).
    Bild 1 laddas direkt med hög prioritet, övriga lazy. Ingen beskärning: object-fit contain på svart scen."""
    if not imgs: return ""
    if len(imgs) == 1:
        im = imgs[0]
        return f'''
      <figure class="article__figure article__figure--natural">
        <div class="frame">{flag_html}{img_tag(im, im["alt"], eager=True, sizes=HERO_SIZES)}</div>
        {caption(im)}
      </figure>'''
    n = len(imgs)
    slides = "".join(f'''
          <div class="gallery__slide" role="group" aria-roledescription="bild" aria-label="{i} av {n}"><figure>
            <div class="gallery__stage">{img_tag(im, im["alt"], eager=(i == 1), sizes=HERO_SIZES)}</div>
            {caption(im)}
          </figure></div>''' for i, im in enumerate(imgs, 1))
    return f'''
      <section class="gallery" aria-roledescription="bildspel" aria-label="Bildspel, {n} bilder" data-gallery>{flag_html}
        <div class="gallery__track" tabindex="0" role="group" aria-label="Bilder. Bläddra med piltangenterna eller svep.">{slides}
        </div>
        <div class="gallery__nav" hidden>
          <button class="gallery__btn" type="button" data-dir="-1" aria-label="Föregående bild"><svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M11 3.5 5.5 9l5.5 5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
          <span class="gallery__count" aria-live="polite" aria-atomic="true"><span class="visually-hidden">Bild </span><b data-current>1</b><span aria-hidden="true"> / </span><span class="visually-hidden"> av </span>{n}</span>
          <button class="gallery__btn" type="button" data-dir="1" aria-label="Nästa bild"><svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M7 3.5 12.5 9 7 14.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
        </div>
      </section>'''

def summary_box(a):
    if not a.get("summary"): return ""
    lis = "".join(f"\n            <li>{nbnum(esc(x.strip()))}</li>" for x in a["summary"])
    return f'''
      <section class="summary article__col" aria-labelledby="summary-h">
        <h2 id="summary-h">Kort om nyheten</h2>
        <ul>{lis}
        </ul>
      </section>'''

LD_RATIOS = (("16x9", 16, 9), ("4x3", 4, 3), ("1x1", 1, 1))
LD_W = 1200
NO_CROP = re.compile(r"beskär|oförändrad|får inte ändras", re.I)  # licenstext (huvudbilden) som utesluter beskärning

def ld_images(a):
    """Huvudbilden beskuren till 16:9, 4:3 och 1:1 för NewsArticle (Google rekommenderar alla tre, Discover vill ha
    bilder minst 1200 px breda). Största möjliga mittbeskärning, högst 1200 px bred, aldrig uppskalad. 16:9 och 4:3
    hoppas över om beskärningen blir smalare än 1200 px, 1:1 om den blir under 800 px. Inga beskärningar alls om
    huvudbildens licens förbjuder det (NO_CROP), då används bara originalbilderna. Sajtens egna bilder beskärs aldrig. Bara incheckade filer används (som img/og/), i --out-läget allt som finns."""
    img = a["img"]
    if not img or NO_CROP.search(img["license"]): return []  # licensen förbjuder beskärning: originalbilderna räcker
    from PIL import Image, ImageOps
    res = []
    for name, rw, rh in LD_RATIOS:
        w = min(LD_W, img["w"], img["h"] * rw // rh); h = round(w * rh / rw)
        if w < (800 if name == "1x1" else LD_W): continue
        rel = f"img/ld/{a['slug']}-{name}.jpg"
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with Image.open(os.path.join(ROOT, img["src"].lstrip("/"))) as im:
                ImageOps.fit(im.convert("RGB"), (w, h), Image.LANCZOS).save(p, "JPEG", quality=84, optimize=True, progressive=True)
        if committed(rel):
            with Image.open(p) as im: res.append(dict(src="/" + rel, w=im.width, h=im.height))
    return res

# ---------- författare ----------
# data/authors.json: {"<id>": {name, url (författarsidan), avatar_src, bio, ai_signature}}. Artikelns author är id:t
# eller namnet (author: Lukas -> lukas). avatar_src är en fil i repot (t.ex. brand/authors/...); den beskärs till en
# kvadrat i mitten (färdiga <namn>-192/-96 bredvid källan används i första hand) och blir img/authors/<id>.webp (192 px) och img/authors/<id>-96.webp. Byt bild genom att peka
# avatar_src på en ny fil (WebP-filerna byggs om när källan är nyare). Ordet TODO i bio ger en varning i bygget.
AUTHORS = {}
AVATAR_SIZES = ((192, ""), (96, "-96"))

def load_authors():
    p = os.path.join(ROOT, "data/authors.json")
    if not os.path.exists(p): return {}
    try: d = json.load(open(p, encoding="utf-8"))
    except ValueError as e: raise SystemExit(f"data/authors.json: {e}")
    for k, v in d.items():
        for f in ("name", "url", "bio"):
            if not str(v.get(f) or "").strip(): raise SystemExit(f"data/authors.json: {k} saknar {f}")
        if re.search(r"\bTODO\b", v["bio"]): print(f"varning: data/authors.json: {k}: bio innehåller TODO")
        v["id"] = k
        v["avatar"] = author_avatar(k, v.get("avatar_src"))
    return d

def author_avatar(aid, src):
    """[(url, bredd)] för avataren, största först. Tom lista om ingen bild finns."""
    from PIL import Image, ImageOps
    base = f"img/authors/{aid}"
    main = os.path.join(ROOT, base + ".webp")
    sp = os.path.join(ROOT, src) if src and not os.path.isabs(src) else src
    if sp and os.path.isfile(sp) and (not os.path.exists(main) or os.path.getmtime(sp) > os.path.getmtime(main)):
        os.makedirs(os.path.dirname(main), exist_ok=True)
        with Image.open(sp) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGBA" if "A" in im.getbands() else "RGB")  # transparenta hörn behålls
            for w, suf in AVATAR_SIZES:
                # färdig storlek bredvid källan (lukas-avatar-1024.png -> lukas-avatar-192.png) används i första hand
                pre = re.sub(r"-\d+(\.\w+)$", rf"-{w}\1", sp)
                if pre != sp and os.path.isfile(pre):
                    with Image.open(pre) as pi: r = pi.convert(im.mode); r.load()
                else: r = ImageOps.fit(im, (w, w), Image.LANCZOS)
                r.save(os.path.join(ROOT, f"{base}{suf}.webp"), "WEBP", quality=90, method=6)
    return [(f"/{base}{suf}.webp", w) for w, suf in AVATAR_SIZES if committed(f"{base}{suf}.webp")]

def find_author(name):
    return AUTHORS.get(slugify(name)) or next((v for v in AUTHORS.values() if v["name"] == name), None)

def author_ld(name):
    au = find_author(name)
    return {"@type": "Person", "name": au["name"], "url": DOMAIN + au["url"]} if au else {"@type": "Person", "name": name}

def author_box(name):
    """Skribentruta längst ner i varje artikel. En mall för alla författare, data från data/authors.json.
    Visar bara namn (länk till författarsidan), avatar, "Skriver på Motorpuls.se", bio och sist det orange märket."""
    au = find_author(name)
    if not au: return ""
    av = au["avatar"]
    img = (f'<img class="author-box__avatar" src="{av[0][0]}" srcset="{", ".join(f"{u} {w}w" for u, w in reversed(av))}" sizes="4rem" '
           f'width="64" height="64" alt="" loading="lazy" decoding="async">') if av else ""
    ai = '<p class="author-box__ai"><span class="author-box__badge">Skrivet med AI-stöd</span></p>' if au.get("ai_signature") else ""
    return f'''
        <aside class="author-box" aria-labelledby="author-box-h">
          {img}
          <div class="author-box__body">
            <h2 class="author-box__name" id="author-box-h"><a href="{au["url"]}" rel="author">{esc(au["name"])}</a></h2>
            <p class="author-box__role">Skriver på Motorpuls.se</p>
            <p class="author-box__bio">{nbnum(esc(au["bio"]))}</p>
            {ai}
          </div>
        </aside>'''

def article(a):
    img, imgs = a["img"], a["images_out"]
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": a["title"], "description": a["excerpt"],
          "datePublished": a["published"], "dateModified": a["modified"], "inLanguage": "sv-SE",
          "articleSection": a["category"], "keywords": a.get("tags") or [],
          "mainEntityOfPage": {"@type": "WebPage", "@id": DOMAIN + a["url"]}, "url": DOMAIN + a["url"],
          "author": author_ld(a["author"]),
          "publisher": {"@type": "Organization", "name": SITE, "url": DOMAIN + "/",
                        "logo": {"@type": "ImageObject", "url": DOMAIN + "/favicon/android-chrome-512.png", "width": 512, "height": 512}}}
    if imgs:
        credit = {k: v for k, v in {"creditText": img["credit"].removeprefix("Foto: ") or None,
                                    "copyrightNotice": img["license"] or None}.items() if v}
        ld["image"] = [dict({"@type": "ImageObject", "url": DOMAIN + c["src"], "width": c["w"], "height": c["h"]}, **credit)
                       for c in ld_images(a)] + [{k: v for k, v in {"@type": "ImageObject", "url": DOMAIN + im["src"], "width": im["w"], "height": im["h"],
                                          "caption": im["alt"], "creditText": im["credit"].removeprefix("Foto: ") or None,
                                          "copyrightNotice": im["license"] or None}.items() if v} for im in imgs]
    if a.get("sources"): ld["citation"] = [u for _, u in a["sources"]]
    jsonld = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    h = head(short_title(a["title"]), a["excerpt"], a["url"], og_type="article", image=og_image(a), og_title=a["title"],
             extra=f'<meta property="article:published_time" content="{a["published"]}">\n'
                   f'<meta property="article:section" content="{esc(a["category"])}">\n'
                   + "".join(f'<meta property="article:tag" content="{esc(t)}">\n' for t in a.get("tags") or []) + jsonld,
             preload_img=img, preload_sizes=HERO_SIZES, robots="max-image-preview:large", feeds=[feed_for(a)])
    sources = ""
    if a["sources"]:
        lis = "".join(f'''
            <li><div><a href="{esc(u)}" rel="noopener" target="_blank">{esc(t)}<span class="visually-hidden"> (öppnas i ny flik)</span></a>
              <div class="meta"><span>{esc(host(u))}</span></div></div></li>''' for t, u in a["sources"])
        sources = f'''
        <section class="sources" aria-labelledby="kallor-h">
          <h2 id="kallor-h">Källor</h2>
          <ol>{lis}
          </ol>
        </section>'''
    updated = (f'<span>Uppdaterad <b><time datetime="{a["modified"]}">{sv_date(a["mod_date"])}</time></b></span>'
               if a["mod_when"] > a["when"] else "")
    au = find_author(a["author"])
    author = f'<a href="{au["url"]}" rel="author">{esc(au["name"])}</a>' if au else esc(a["author"])
    body = f'''
<main id="innehall" class="article">
  <div class="wrap">
    <article>
      <header class="article__head article__col">
        <nav class="crumbs" aria-label="Brödsmulor"><a href="/">Start</a><span aria-hidden="true">/</span><span class="tag">{esc(a["category"])}</span>{meta_flag(a, imgs)}</nav>
        <h1 class="article__title">{nbnum(esc(a["headline"]))}</h1>
        <p class="article__dek">{nbnum(esc(a["excerpt"]))}</p>
        <p class="byline"><span>Publicerad <b><time datetime="{a["published"]}">{sv_date(a["date"])}</time></b></span>{updated}<span>Läsetid <b>{a["minutes"]} min</b></span><span>Av <b>{author}</b></span></p>
      </header>{summary_box(a)}{gallery(imgs, flag(a, "hero"))}
      <div class="article__layout article__col">
        <div class="prose">
{nbnum_html(a["body_html"])}
        </div>
{sources}
        <aside class="ai-note" aria-label="Om texten">
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M8 7v4.5M8 4.6v.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <p>Texten är skriven med hjälp av AI och faktagranskad mot källorna ovan. <a href="/om/">Så arbetar Motorpuls</a></p>
        </aside>
{author_box(a["author"])}{push_box("article")}{rss_row(a)}
        <p class="more"><a class="btn" href="/">Fler nyheter på startsidan</a></p>
      </div>
    </article>
  </div>
</main>
'''
    return page(h, body)

def notfound():
    h = head(f"Sidan finns inte · {SITE}", SITE_DESC, None, noindex=True)
    body = '''
<main id="innehall" class="article">
  <div class="wrap">
    <header class="article__head">
      <h1 class="article__title">Sidan finns inte</h1>
      <p class="article__dek">Länken kan vara fel eller sidan flyttad.</p>
      <p class="more"><a class="btn" href="/">Till startsidan</a></p>
    </header>
  </div>
</main>
'''
    return page(h, body)

def load_pages():
    pages = []
    for path in sorted(glob.glob(os.path.join(ROOT, "content/pages/*.md"))):
        raw = open(path, encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
        if not m: raise SystemExit(f"saknar front matter: {path}")
        fm, body = yaml.safe_load(m.group(1)), m.group(2)
        for k in ("title", "path", "description"):
            if not fm.get(k): raise SystemExit(f"{path}: saknar {k}")
        if not re.fullmatch(r"/([a-z0-9-]+/)+", fm["path"]): raise SystemExit(f"{path}: path ska se ut som /om/")
        todos = len(re.findall(r"\bTODO\b", body))
        if todos: print(f"varning: {os.path.relpath(path, ROOT)}: {todos} TODO kvar att skriva")
        pages.append(dict(fm, file=os.path.basename(path), body_html=markdown.markdown(body.strip(), extensions=["toc"])))
    if len({p["path"] for p in pages}) != len(pages): raise SystemExit("content/pages: dubbla path")
    return pages

def info_page(p, arts):
    """Om-sidor och författarsidor: samma artikelmall som nyheterna, utan bilder och utan extra JS."""
    extra, listing = "", ""
    if p.get("author"):
        ld = {"@context": "https://schema.org", "@type": "ProfilePage", "url": DOMAIN + p["path"],
              "mainEntity": dict(author_ld(p["author"]), description=p["description"])}
        extra = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
        au = find_author(p["author"])
        if not au or au["url"] != p["path"]: raise SystemExit(f"content/pages/{p['file']}: author {p['author']!r} saknas i data/authors.json eller har en annan url")
        mine = [a for a in arts if find_author(a["author"]) is au]
        if mine:
            lis = "".join(f'''
            <li><div><a href="{a["url"]}">{esc(a["title"])}</a>
              <div class="meta"><time datetime="{a["published"]}">{sv_date(a["date"])}</time></div></div></li>''' for a in mine)
            listing = f'''
        <section class="sources sources--internal" aria-labelledby="art-h">
          <h2 id="art-h">Artiklar</h2>
          <ol>{lis}
          </ol>
        </section>'''
    h = head(short_title(p["title"]), p["description"], p["path"], og_title=p["title"], extra=extra)
    body = f'''
<main id="innehall" class="article">
  <div class="wrap">
    <article>
      <header class="article__head article__col">
        <nav class="crumbs" aria-label="Brödsmulor"><a href="/">Start</a><span aria-hidden="true">/</span><span class="tag">Om Motorpuls</span></nav>
        <h1 class="article__title">{esc(p["title"])}</h1>
        <p class="article__dek">{esc(p["description"])}</p>
      </header>
      <div class="article__layout article__col">
        <div class="prose">
{p["body_html"]}
        </div>{listing}
      </div>
    </article>
  </div>
</main>
'''
    return page(h, body)

def news_sitemap(arts):
    """Google News-sitemap: artiklar publicerade de senaste NEWS_DAYS dygnen räknat från byggtiden (kan bli tom,
    det är tillåtet). publication_date är den ursprungliga publiceringstidpunkten."""
    cutoff = now() - dt.timedelta(days=NEWS_DAYS)
    items = "".join(f"""  <url>
    <loc>{DOMAIN}{a["url"]}</loc>
    <news:news>
      <news:publication>
        <news:name>{esc(SITE)}</news:name>
        <news:language>{NEWS_LANG}</news:language>
      </news:publication>
      <news:publication_date>{a["published"]}</news:publication_date>
      <news:title>{esc(a["headline"])}</news:title>
    </news:news>
  </url>
""" for a in arts if a["when"] >= cutoff)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n' + items + "</urlset>\n")

def write(rel, text):
    WRITTEN.append(rel)
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)

def main():
    global FEEDS
    arts = load_articles()
    if not arts: raise SystemExit("inga artiklar i content/articles/")
    pages = load_pages()
    AUTHORS.update(load_authors())
    for a in arts:
        if not find_author(a["author"]): print(f"varning: {a['file']}: författaren {a['author']!r} saknas i data/authors.json")
    for a in arts:
        a["images_out"] = ensure_images(a)
        a["img"] = a["images_out"][0] if a["images_out"] else None
    FEEDS = category_feeds(arts)
    # clean old article output so removed articles disappear
    shutil.rmtree(os.path.join(ROOT, "artikel"), ignore_errors=True)
    if os.path.exists(os.path.join(ROOT, "artikel.html")): os.remove(os.path.join(ROOT, "artikel.html"))
    write("index.html", index(arts))
    for a in arts: write(f"artikel/{a['slug']}/index.html", article(a))
    shutil.rmtree(os.path.join(ROOT, "om"), ignore_errors=True)
    for p in pages: write(p["path"].lstrip("/") + "index.html", info_page(p, arts))
    write("404.html", notfound())
    urls = [("/", arts[0]["date"])] + [(a["url"], a["date"]) for a in arts]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{DOMAIN}{u}</loc><lastmod>{lastmod(u, arts)}</lastmod></url>\n" for u, d in urls)
          + "".join(f"  <url><loc>{DOMAIN}{p['path']}</loc></url>\n" for p in pages) + "</urlset>\n")
    write("sitemap-news.xml", news_sitemap(arts))
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\nSitemap: {DOMAIN}/sitemap-news.xml\n")
    write("feed.xml", rss(arts))
    shutil.rmtree(os.path.join(ROOT, "feed"), ignore_errors=True)  # borttagna kategorier försvinner
    for f in FEEDS:
        write(f"feed/{f['key']}.xml", rss(f["arts"], title=f"{SITE}: {f['name']}",
              desc=f"Artiklar i kategorin {f['name']} på {SITE}. {SITE_DESC}", path=f["path"]))
    for rel in ("sw.js", "push.js"):  # gammal förhandsvisning i projektroten tas bort
        if os.path.exists(os.path.join(ROOT, rel)): os.remove(os.path.join(ROOT, rel))
    if os.path.exists(os.path.join(ROOT, "nyhetsbrev.js")): os.remove(os.path.join(ROOT, "nyhetsbrev.js"))
    if NEWSLETTER_BOX: write("nyhetsbrev.js", nl_src("nyhetsbrev.js"))
    if PUSH_BOX:
        write("sw.js", push_src("sw.js"))  # i roten så att service workern gäller hela sajten (scope /)
        write("push.js", push_src("push.js"))
    print(f"built {len(arts)} artiklar: " + ", ".join(a["slug"] for a in arts))

def out_dir(o):
    out = os.path.abspath(o)
    top = os.path.relpath(out, ROOT).split(os.sep)[0]
    if out == ROOT or ROOT.startswith(out + os.sep) or top in PUBLIC_DIRS + ("artikel", "content", "drafts", "brand", ".git"):
        raise SystemExit(f"--out {out}: välj en egen katalog som rensas vid varje bygge (t.ex. _site)")
    return out

def publish(out):
    """Kopiera den publika delen av sajten till out (tom katalog först)."""
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    skip = shutil.ignore_patterns("__pycache__", ".DS_Store", "*-original.*")
    for d in PUBLIC_DIRS:
        if os.path.isdir(os.path.join(ROOT, d)): shutil.copytree(os.path.join(ROOT, d), os.path.join(out, d), ignore=skip)
    for rel in [f for f in PUBLIC_FILES if os.path.exists(os.path.join(ROOT, f))] + sorted(set(WRITTEN)):
        os.makedirs(os.path.dirname(os.path.join(out, rel)), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), os.path.join(out, rel))
    return out

def check_links(out):
    """Varje lokal URL i html (href, src, srcset, og:image m.fl.), css (url()) och webbmanifest ska finnas i out."""
    refs = []  # (fil, url)
    for dirpath, _, files in os.walk(out):
        for fn in files:
            p = os.path.join(dirpath, fn); rel = os.path.relpath(p, out)
            if fn.endswith((".html", ".xml")):
                t = open(p, encoding="utf-8").read()
                for attr, v in re.findall(r'(href|src|srcset|content)="([^"]*)"', t):
                    if attr == "srcset": refs += [(rel, x.split()[0]) for x in v.split(",") if x.strip()]
                    elif attr == "content" and not v.startswith((DOMAIN + "/", "/")): continue
                    else: refs.append((rel, v))
                if fn.endswith(".xml"): refs += [(rel, u) for u in re.findall(r"<(?:loc|link)>([^<]+)</", t)]
            elif fn.endswith(".css"):
                refs += [(rel, u.strip("'\"")) for u in re.findall(r"url\(([^)]+)\)", open(p, encoding="utf-8").read())]
            elif fn.endswith(".webmanifest"):
                refs += [(rel, i["src"]) for i in json.load(open(p, encoding="utf-8")).get("icons", [])]
    missing = []
    for rel, u in refs:
        if u.startswith(DOMAIN): u = u[len(DOMAIN):] or "/"
        if not u or u.startswith(("#", "data:", "mailto:", "tel:", "javascript:")) or re.match(r"^[a-z]+:", u): continue
        path = urllib.parse.urlsplit(u).path
        target = os.path.normpath(os.path.join(out, path.lstrip("/")) if path.startswith("/")
                                  else os.path.join(out, os.path.dirname(rel), path))
        if path.endswith("/") or os.path.isdir(target): target = os.path.join(target, "index.html")
        if not os.path.isfile(target): missing.append(f"{rel}: {u}")
    if missing: raise SystemExit("saknade filer i utdata:\n  " + "\n  ".join(sorted(set(missing))))
    return len(refs)

def check_no_push(out):
    """Flaggan av: inget av push-rutan får finnas i utdata (ingen ruta, ingen push.js, ingen sw.js, ingen registrering)."""
    bad = [f for f in ("sw.js", "push.js") if os.path.exists(os.path.join(out, f))]
    for dirpath, _, files in os.walk(out):
        for fn in files:
            if fn.endswith((".html", ".js")):
                t = open(os.path.join(dirpath, fn), encoding="utf-8").read()
                if re.search(r'id="push"|serviceWorker|/sw\.js|/push\.js|PushManager', t): bad.append(os.path.relpath(os.path.join(dirpath, fn), out))
    if bad: raise SystemExit("PUSH_BOX är av men push finns i utdata: " + ", ".join(sorted(bad)))

def check_no_newsletter(out):
    """Flaggan av: inget av sidfotens nyhetsbrevsruta får finnas i utdata (ingen ruta, ingen nyhetsbrev.js, ingen Supabase-adress)."""
    bad = ["nyhetsbrev.js"] if os.path.exists(os.path.join(out, "nyhetsbrev.js")) else []
    for dirpath, _, files in os.walk(out):
        for fn in files:
            if fn.endswith((".html", ".js")):
                t = open(os.path.join(dirpath, fn), encoding="utf-8").read()
                if re.search(r'id="nyhetsbrev-fot"|/nyhetsbrev\.js|newsletter_subscribers|site-footer--nl', t): bad.append(os.path.relpath(os.path.join(dirpath, fn), out))
    if bad: raise SystemExit("NEWSLETTER_BOX är av men nyhetsbrevsrutan finns i utdata: " + ", ".join(sorted(bad)))

def _rebuild_root_without_previews():
    global PUSH_BOX, NEWSLETTER_BOX, OUT
    PUSH_BOX, NEWSLETTER_BOX, OUT = False, False, None
    WRITTEN.clear(); main()
    print("projektroten byggd om utan förhandsrutorna (förhandsvisningen finns bara i --out)")

def cli():
    global OUT
    args = sys.argv[1:]
    if args[:1] == ["--out"] and len(args) == 2: OUT = out_dir(args[1])
    elif args: raise SystemExit("användning: build.py [--out _site]")
    if PUSH_BOX and not OUT: raise SystemExit("MOTORPULS_PUSH=1 är bara för förhandsbygge: använd --out (t.ex. _preview), aldrig utan")
    if NEWSLETTER_BOX and not OUT: raise SystemExit("MOTORPULS_NYHETSBREV=1 är bara för förhandsbygge: använd --out (t.ex. _preview), aldrig utan")
    main()
    if OUT:
        out = publish(OUT)
        if not PUSH_BOX: check_no_push(out)
        if not NEWSLETTER_BOX: check_no_newsletter(out)
        n = check_links(out)
        files = sum(len(f) for _, _, f in os.walk(out))
        print(f"publicerat till {out}: {files} filer, {n} lokala länkar kontrollerade")
    if PUSH_BOX or NEWSLETTER_BOX:  # bygget skriver även i projektroten: bygg om den utan rutorna så att inget av förhandsvisningen checkas in
        _rebuild_root_without_previews()

if __name__ == "__main__":
    cli()
