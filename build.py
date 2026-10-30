# Bygger Motorpuls från content/articles/*.md. Kör: .venv/bin/python build.py (kräver markdown och pyyaml).
#
# Utdata:
#   index.html                    startsida, riktiga artiklar, nyast först
#   artikel/<slug>/index.html     en sida per artikel (rena URL:er: /artikel/<slug>/)
#   404.html, sitemap.xml, robots.txt
#
# Artiklar: markdown med YAML-front matter (title, date, slug, tags, sources, excerpt, category, author,
# valfritt summary, images, äldre image/image_credit). Brödtexten renderas oförändrad. Rubriken (#) i texten
# blir sidans h1, avsnittet "## Källor" renderas i källistan. Ordning: datum, sedan filnamn (nyast först).
#
# sweden:  valfritt, true när nyheten gäller Sverige. Då visas en liten svensk flagga (äldre, mörkare färger)
#          som ett eget element ovanpå huvudbildens hörn och på startsidans kort, eller vid kategorin om
#          artikeln saknar bild. Bildfilerna ändras aldrig.
# summary: lista med 2 till 4 korta punkter (vanlig text), visas i rutan "Kort om nyheten".
# images:  lista med {src, alt, credit, license, valfritt caption}. src är en lokal fil: ett filnamn som
#          letas upp i drafts/img/<slug>/, utkastens form img/<slug>/fil (relativ till drafts/), en sökväg
#          relativ till projektroten eller en absolut sökväg. Okända fält (t.ex. source_url) ignoreras.
#          Filen kopieras till img/articles/<slug>/ och får WebP-versioner (1600 och 800 px bred, bara
#          storleksändring, aldrig beskärning). Finns WebP-filen redan byggs den inte om (källan behövs inte).
#          Första bilden är huvudbild (og:image), fler bilder blir ett bildspel.
# image:   äldre fält (en URL). Laddas ned till img/articles/<slug>.webp om filen saknas, kredit i image_credit.
import datetime as dt, glob, hashlib, html, json, math, os, re, shutil, urllib.request
import markdown, yaml

DRAFTS_IMG = os.environ.get("MOTORPULS_DRAFTS_IMG")  # valfri extra källmapp, standard: <root>/drafts/img

ROOT = os.path.dirname(os.path.abspath(__file__))
DOMAIN = "https://motorpuls.se"
SITE = "Motorpuls"
SITE_DESC = "Korta, sakliga nyheter om elbilar, sportbilar, laddning och förnybara bränslen. Varje text länkar till sina källor."
MAX_W = 1600

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

ANALYTICS = """<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "bace28864ae04c6fa5e9f4a98ca70f94"}'></script><!-- End Cloudflare Web Analytics -->
"""

# ---------- content ----------
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
        d = fm["date"] if isinstance(fm["date"], dt.date) else dt.date.fromisoformat(str(fm["date"]))
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
        words = len(re.findall(r"\w+", body))
        arts.append(dict(fm, date=d, headline=headline, body_html=markdown.markdown(body.strip()),
                         sources=sources, file=os.path.basename(path), minutes=max(1, math.ceil(words/200)),
                         url=f"/artikel/{fm['slug']}/", cat=slugify(fm["category"])))
    arts.sort(key=lambda a: (a["date"], a["file"]), reverse=True)
    if len({a["slug"] for a in arts}) != len(arts): raise SystemExit("dubbla slugs")
    return arts

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
    """Skriver <out_base>.webp (max 1600 px) och <out_base>-800.webp (om bilden är bredare än 800 px).
    Samma bildformat: bara storleksändring, aldrig beskärning."""
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = None  # pressbilder kan vara över 100 megapixel, källorna är våra egna filer
    im = Image.open(src_path); im.load()
    im = ImageOps.exif_transpose(im)  # följ EXIF-orienteringen (vrider bara, beskär aldrig)
    icc = im.info.get("icc_profile")  # färgprofilen följer med oförändrad (t.ex. Adobe RGB, P3), inga färgändringar
    if im.mode not in ("RGB", "RGBA"): im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
    for w, suffix in ((MAX_W, ""), (800, "-800")):
        if suffix and im.width <= 800: break
        tw = min(w, im.width)
        if tw == im.width and src_path.lower().endswith(".webp"):  # redan WebP i rätt storlek: kopiera, koda inte om
            shutil.copyfile(src_path, os.path.join(ROOT, f"{out_base}{suffix}.webp")); continue
        r = im if tw == im.width else im.resize((tw, round(im.height * tw / im.width)), Image.LANCZOS)
        r.save(os.path.join(ROOT, f"{out_base}{suffix}.webp"), "WEBP", quality=86, method=6, **({"icc_profile": icc} if icc else {}))

def read_variants(out_base):
    from PIL import Image
    res = []
    for suffix in ("", "-800"):
        rel = f"{out_base}{suffix}.webp"
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
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

# ---------- shared html ----------
def asset(rel):
    """URL med ?v=<kort innehållshash> så att webbläsare (Safari) alltid hämtar aktuell css/js efter en ändring."""
    with open(os.path.join(ROOT, rel.lstrip("/")), "rb") as f:
        return f"{rel}?v={hashlib.sha256(f.read()).hexdigest()[:10]}"


def head(title, desc, path, og_type="website", image=None, extra="", preload_img=None, og_title=None, preload_sizes="100vw"):
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
<meta name="robots" content="noindex">
{f'<link rel="canonical" href="{canon}">' + chr(10) if canon else ""}<meta property="og:site_name" content="{SITE}">
<meta property="og:locale" content="sv_SE">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(og_title)}">
<meta property="og:description" content="{esc(desc)}">
{f'<meta property="og:url" content="{canon}">' + chr(10) if canon else ""}{og_img}<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}">
<meta name="twitter:title" content="{esc(og_title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="theme-color" content="#0B0D10">
<meta name="color-scheme" content="dark">
<link rel="icon" href="/favicon/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="/favicon/favicon-16.png" sizes="16x16" type="image/png">
<link rel="apple-touch-icon" href="/favicon/apple-touch-icon.png">
<link rel="manifest" href="/favicon/site.webmanifest">
<link rel="preload" href="/fonts/archivo-var.woff2" as="font" type="font/woff2" crossorigin>
{pre}<link rel="stylesheet" href="{asset("/css/site.css")}">
<script src="{asset("/js/site.js")}" defer></script>
{extra}</head>
<body>
<a class="skip" href="#innehall">Hoppa till innehållet</a>
<header class="masthead">
  <div class="wrap masthead__row">
    <a class="wordmark" href="/"><img class="logo" src="/img/logo.svg" alt="Motorpuls" width="872" height="88"></a>
  </div>
</header>
'''

FOOTER = f'''
<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div>
        <a class="wordmark" href="/"><img class="logo logo--footer" src="/img/logo.svg" alt="Motorpuls" width="872" height="88" loading="lazy"></a>
        <p style="margin-top:1rem">{SITE_DESC}</p>
      </div>
    </div>
    <p class="fine">© 2026 Motorpuls</p>
  </div>
</footer>
'''

def page(h, body): return h + body + FOOTER + ANALYTICS + "</body>\n</html>\n"

def meta_line(a, with_date=True, flag_html=""):
    t = f'<time datetime="{a["date"].isoformat()}">{sv_date(a["date"])}</time>' if with_date else ""
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
    media = (f'<figure class="lead__media">{flag(a, "lead")}{img_tag(img, img["alt"], eager=True, sizes=LEAD_SIZES)}'
             f'<figcaption>{esc(img["credit"])}</figcaption></figure>') if img else ""
    return f'''
    <article class="lead{" lead--img" if img else " lead--text"}">
      <a href="{a["url"]}">
        {media}
        <div class="lead__body">
          <span class="hero__label"><span class="pulse-dot" aria-hidden="true"></span>Senaste nytt</span>
          {meta_line(a, flag_html=meta_flag(a, img))}
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
                <h3>{esc(a["title"])}</h3>
                <p>{esc(a["excerpt"])}</p>
              </div>
              {thumb}
            </a>
          </li>'''

def index(arts):
    first, rest = arts[0], arts[1:]
    h = head(f"{SITE}: korta bilnyheter med källor", SITE_DESC, "/",
             preload_img=first["img"], preload_sizes=LEAD_SIZES)
    if rest:
        side = f'<aside class="latest" aria-labelledby="latest-h" style="--n:{min(len(rest),5)}"><h2 id="latest-h"><span class="pulse-dot" aria-hidden="true"></span>Senaste</h2><ol>' + "".join(
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
    </div>
  </div>
{feed}
</main>
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
          <figure class="gallery__slide" role="group" aria-roledescription="bild" aria-label="{i} av {n}">
            <div class="gallery__stage">{img_tag(im, im["alt"], eager=(i == 1), sizes=HERO_SIZES)}</div>
            {caption(im)}
          </figure>''' for i, im in enumerate(imgs, 1))
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

def article(a):
    img, imgs = a["img"], a["images_out"]
    ld = {"@context": "https://schema.org", "@type": "NewsArticle", "headline": a["title"], "description": a["excerpt"],
          "datePublished": a["date"].isoformat(), "dateModified": a["date"].isoformat(), "inLanguage": "sv-SE",
          "articleSection": a["category"], "keywords": a.get("tags") or [],
          "mainEntityOfPage": {"@type": "WebPage", "@id": DOMAIN + a["url"]}, "url": DOMAIN + a["url"],
          "author": {"@type": "Person", "name": a["author"]},
          "publisher": {"@type": "Organization", "name": SITE, "url": DOMAIN + "/",
                        "logo": {"@type": "ImageObject", "url": DOMAIN + "/favicon/android-chrome-512.png", "width": 512, "height": 512}}}
    if imgs:
        ld["image"] = [{k: v for k, v in {"@type": "ImageObject", "url": DOMAIN + im["src"], "width": im["w"], "height": im["h"],
                                          "caption": im["alt"], "creditText": im["credit"].removeprefix("Foto: ") or None,
                                          "copyrightNotice": im["license"] or None}.items() if v} for im in imgs]
    if a.get("sources"): ld["citation"] = [u for _, u in a["sources"]]
    jsonld = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    h = head(f'{a["title"]} · {SITE}', a["excerpt"], a["url"], og_type="article", image=img, og_title=a["title"],
             extra=f'<meta property="article:published_time" content="{a["date"].isoformat()}">\n'
                   f'<meta property="article:section" content="{esc(a["category"])}">\n'
                   + "".join(f'<meta property="article:tag" content="{esc(t)}">\n' for t in a.get("tags") or []) + jsonld,
             preload_img=img, preload_sizes=HERO_SIZES)
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
    body = f'''
<main id="innehall" class="article">
  <div class="wrap">
    <article>
      <header class="article__head article__col">
        <nav class="crumbs" aria-label="Brödsmulor"><a href="/">Start</a> / <span>{esc(a["category"])}</span></nav>
        <span class="meta"><span class="tag">{esc(a["category"])}</span>{meta_flag(a, imgs)}</span>
        <h1 class="article__title">{nbnum(esc(a["headline"]))}</h1>
        <p class="article__dek">{nbnum(esc(a["excerpt"]))}</p>
        <p class="byline"><span>Publicerad <b><time datetime="{a["date"].isoformat()}">{sv_date(a["date"])}</time></b></span><span>Läsetid <b>{a["minutes"]} min</b></span><span>Av <b>{esc(a["author"])}</b></span></p>
      </header>{summary_box(a)}{gallery(imgs, flag(a, "hero"))}
      <div class="article__layout article__col">
        <div class="prose">
{nbnum_html(a["body_html"])}
        </div>
{sources}
        <aside class="ai-note" aria-label="Om texten">
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M8 7v4.5M8 4.6v.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <p>Texten är skriven med hjälp av AI och faktagranskad mot källorna ovan.</p>
        </aside>

        <p class="more"><a class="btn" href="/" style="text-decoration:none;display:inline-block">Fler nyheter på startsidan</a></p>
      </div>
    </article>
  </div>
</main>
'''
    return page(h, body)

def notfound():
    h = head(f"Sidan finns inte · {SITE}", SITE_DESC, None)
    body = '''
<main id="innehall" class="article">
  <div class="wrap">
    <header class="article__head">
      <h1 class="article__title">Sidan finns inte</h1>
      <p class="article__dek">Länken kan vara fel eller sidan flyttad.</p>
      <p class="more"><a class="btn" href="/" style="text-decoration:none;display:inline-block">Till startsidan</a></p>
    </header>
  </div>
</main>
'''
    return page(h, body)

def write(rel, text):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(text)

def main():
    arts = load_articles()
    if not arts: raise SystemExit("inga artiklar i content/articles/")
    for a in arts:
        a["images_out"] = ensure_images(a)
        a["img"] = a["images_out"][0] if a["images_out"] else None
    # clean old article output so removed articles disappear
    shutil.rmtree(os.path.join(ROOT, "artikel"), ignore_errors=True)
    if os.path.exists(os.path.join(ROOT, "artikel.html")): os.remove(os.path.join(ROOT, "artikel.html"))
    write("index.html", index(arts))
    for a in arts: write(f"artikel/{a['slug']}/index.html", article(a))
    write("404.html", notfound())
    urls = [("/", arts[0]["date"])] + [(a["url"], a["date"]) for a in arts]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{DOMAIN}{u}</loc><lastmod>{d.isoformat()}</lastmod></url>\n" for u, d in urls) + "</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n")
    print(f"built {len(arts)} artiklar: " + ", ".join(a["slug"] for a in arts))

if __name__ == "__main__":
    main()
