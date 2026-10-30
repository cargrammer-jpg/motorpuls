# Bygger index.html och artikel.html från delade bitar. Kör: python3 build.py
DOMAIN = "https://motorpuls.example"  # exempeldomän tills motorpuls.se är köpt

def head(title, desc, path, preload):
    return f'''<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex">
<link rel="canonical" href="{DOMAIN}{path}">
<meta name="theme-color" content="#0B0D10">
<meta name="color-scheme" content="dark">
<link rel="icon" href="favicon/favicon.ico" sizes="48x48">
<link rel="icon" href="favicon/favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="favicon/favicon-16.png" sizes="16x16" type="image/png">
<link rel="apple-touch-icon" href="favicon/apple-touch-icon.png">
<link rel="manifest" href="favicon/site.webmanifest">
<link rel="preload" href="fonts/archivo-var.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" as="image" href="{preload}-1600.webp" imagesrcset="{preload}-800.webp 800w, {preload}-1600.webp 1600w" imagesizes="(min-width: 80rem) 76rem, 100vw" fetchpriority="high">
<link rel="stylesheet" href="css/site.css">
<script src="js/site.js" defer></script>
</head>
<body>
<a class="skip" href="#innehall">Hoppa till innehållet</a>
<div class="example-bar" role="note"><strong>EXEMPEL</strong> · Prototyp med påhittat innehåll. Inga riktiga nyheter.</div>
<header class="masthead">
  <div class="wrap masthead__row">
    <a class="wordmark" href="index.html"><img class="logo" src="img/logo.svg" alt="Motorpuls" width="872" height="88"></a>
    <nav class="mainnav" aria-label="Huvudmeny">
      <ul>
        <li><a href="index.html#flodet">Elbil</a></li>
        <li><a href="index.html#flodet">Sportbil</a></li>
        <li><a href="index.html#flodet">Tesla</a></li>
        <li><a href="index.html#flodet">Laddning</a></li>
        <li><a href="index.html#flodet">Bränsle</a></li>
      </ul>
    </nav>
    <span class="masthead__date"><time datetime="2026-10-29">tors 29 okt</time></span>
  </div>
</header>
'''

ANALYTICS = """<!-- Cloudflare Web Analytics --><script defer src='https://static.cloudflareinsights.com/beacon.min.js' data-cf-beacon='{"token": "bace28864ae04c6fa5e9f4a98ca70f94"}'></script><!-- End Cloudflare Web Analytics -->
"""

NEWSLETTER = '''
<aside id="nyhetsbrev" class="nl" popover="manual" aria-labelledby="nl-title">
  <button type="button" class="nl__close" aria-label="Stäng">
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M3 3l12 12M15 3L3 15" stroke="currentColor" stroke-width="1.6" fill="none"/></svg>
  </button>
  <p class="nl__kicker"><span class="pulse-dot" aria-hidden="true"></span>Nyhetsbrev · fredagar</p>
  <h2 id="nl-title">Veckans viktigaste, på tre minuter</h2>
  <p id="nl-desc">Fem korta nyheter med källor. Ingen spam, avsluta när du vill.</p>
  <form action="#" novalidate>
    <label for="nl-email">E-postadress</label>
    <input id="nl-email" type="email" name="email" autocomplete="email" placeholder="din@e-post.se" required>
    <button class="btn" type="submit">Prenumerera</button>
  </form>
  <p class="nl__status" role="status" aria-live="polite"></p>
  <p class="nl__fine">Exempel: formuläret skickar inget ännu.</p>
</aside>
'''

FOOTER = '''
<footer class="site-footer">
  <div class="wrap">
    <div class="footer-grid">
      <div>
        <a class="wordmark" href="index.html"><img class="logo logo--footer" src="img/logo.svg" alt="Motorpuls" width="872" height="88" loading="lazy"></a>
        <p style="margin-top:1rem">Korta, sakliga nyheter om elbilar, sportbilar, laddning och förnybara bränslen. Varje text länkar till sina källor.</p>
      </div>
      <nav aria-label="Om Motorpuls"><ul>
        <li><a href="#">Så arbetar vi</a></li><li><a href="#">AI och faktagranskning</a></li><li><a href="#">Rättelser</a></li>
      </ul></nav>
      <nav aria-label="Följ"><ul>
        <li><a href="#" onclick="document.getElementById('nyhetsbrev')?.showPopover?.();return false">Nyhetsbrev</a></li><li><a href="#">RSS</a></li><li><a href="#">Kontakt</a></li>
      </ul></nav>
    </div>
    <p class="fine">© 2026 Motorpuls (prototyp) · Exempeldomän motorpuls.example · Bilder är abstrakta platshållare.</p>
  </div>
</footer>
'''

def pic(name, alt, sizes, eager=False, w=1600, h=1000):
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<img src="img/{name}-1600.webp" srcset="img/{name}-800.webp 800w, img/{name}-1600.webp 1600w" '
            f'sizes="{sizes}" width="{w}" height="{h}" alt="{alt}" {load}>')

CATS = {"elbil":"Elbil","sportbil":"Sportbil","tesla":"Tesla","laddning":"Laddning","bransle":"Bränsle"}

FEED = [
 ("Idag · torsdag 29 oktober", "2026-10-29", [
  ("07:15","tesla","Tesla, pressmeddelande (exempel)","Exempel: Tesla uppdaterar mjukvara med ny förvärmning inför vintern","Batteriet kan nu förvärmas automatiskt när en laddare väljs i navigationen."),
 ]),
 ("Igår · onsdag 28 oktober", "2026-10-28", [
  ("16:05","sportbil","Tillverkaren (exempel)","Exempel: Lätt elektrisk roadster visas, 1&nbsp;350&nbsp;kg och 420&nbsp;km räckvidd","Bilen väntas i produktion 2028. Pris är ännu inte satt."),
  ("11:30","bransle","Energimyndigheten (exempel)","HVO-andelen i svensk diesel ökade under tredje kvartalet","Förnybar diesel stod för en större del av försäljningen än året innan, enligt exempeldata."),
  ("09:10","elbil","Mobility Sweden (exempel)","Elbilar 41&nbsp;procent av nyregistreringarna i oktober, enligt exempelsiffror","Laddhybriderna minskade samtidigt för tredje månaden i rad."),
 ]),
 ("Måndag 26 oktober", "2026-10-26", [
  ("14:20","laddning","Laddoperatören (exempel)","Exempel: <span class='nobr'>Supercharger-station</span> med 24&nbsp;platser öppnar vid Exempelby handelsområde","Stationen är öppen för alla elbilsmärken via app."),
  ("10:00","elbil","Tillverkaren (exempel)","Exempel: Kompakt elbil får större batteri utan prishöjning","Räckvidden ökar till 480&nbsp;km enligt WLTP i exemplet."),
 ]),
]

def index():
    h = head("Motorpuls: korta bilnyheter med källor (exempel)", "Exempelprototyp: korta, sakliga nyheter om elbil, sportbil, Tesla, laddning och bränsle.", "/", "img/hero")
    # build latest list (first 4 items)
    flat = [(d,t,c,s,title,dek) for (_,d,its) in FEED for (t,c,s,title,dek) in its]
    latest = "".join(f'''
          <li><a href="artikel.html"><span class="meta"><time datetime="{d}T{t}">{t}</time><span class="tag">{CATS[c]}</span></span><h3>{title}</h3></a></li>''' for (d,t,c,s,title,dek) in flat[:5])
    days = ""
    for (label, d, its) in FEED:
        lis = "".join(f'''
          <li class="item" data-cat="{c}">
            <a href="artikel.html">
              <time class="item__time" datetime="{d}T{t}">{t}</time>
              <div class="item__text">
                <span class="meta"><time class="t-mobile" datetime="{d}T{t}">{t}</time><span class="tag">{CATS[c]}</span><span class="source">{s}</span></span>
                <h3>{title}</h3>
                <p>{dek}</p>
              </div>
              <div class="item__img">{pic(c, "", "(min-width: 48rem) 15rem, 6.5rem")}</div>
            </a>
          </li>''' for (t,c,s,title,dek) in its)
        days += f'''
      <section class="day" aria-labelledby="d-{d}">
        <h3 class="day__label" id="d-{d}"><time datetime="{d}">{label}</time></h3>
        <ol class="feed">{lis}
        </ol>
      </section>'''
    chips = '<li><button class="chip" type="button" data-filter="alla" aria-pressed="true">Alla</button></li>' + "".join(
        f'<li><button class="chip" type="button" data-filter="{k}" aria-pressed="false">{v}</button></li>' for k,v in CATS.items())
    body = f'''
<main id="innehall" class="front">
  <div class="wrap">
    <h1 class="visually-hidden">Motorpuls, senaste bilnyheterna</h1>
    <div class="hero-grid">
      <article class="hero">
        <a href="artikel.html">
          <div class="hero__media">{pic("hero", "Abstrakt platshållarbild: ljusstrimmor mot en orange horisont.", "(min-width: 80rem) 76rem, 100vw", eager=True)}<span class="badge-example" aria-hidden="true">Platshållare</span></div>
          <div class="hero__body">
            <span class="hero__label"><span class="pulse-dot" aria-hidden="true"></span>Toppnyhet</span>
            <span class="meta"><span class="tag">Laddning</span><span class="source">Trafikverket (exempel)</span><time datetime="2026-10-29T08:40">idag 08:40</time></span>
            <h2 class="hero__title">Ny laddkorridor längs E4 klar: 14&nbsp;stationer mellan Exempelby och Norrstad</h2>
            <p class="hero__dek">Den sista stationen öppnade i morse. Alla har minst 150&nbsp;kW och tar betalkort direkt, utan app. (Påhittad exempelnyhet.)</p>
          </div>
        </a>
      </article>
      <aside class="latest" aria-labelledby="latest-h">
        <h2 id="latest-h"><span class="pulse-dot" aria-hidden="true"></span>Senaste</h2>
        <ol>{latest}
        </ol>
      </aside>
    </div>
  </div>

  <section class="feed-section" id="flodet" aria-labelledby="feed-h">
    <div class="wrap">
      <div class="section-head">
        <h2 id="feed-h">Flödet</h2>
        <nav aria-label="Kategorier"><ul class="chips">{chips}</ul></nav>
      </div>
      <p id="filter-status" class="visually-hidden" role="status" aria-live="polite"></p>
      {days}
    </div>
  </section>
</main>
'''
    return h + body + FOOTER + NEWSLETTER + ANALYTICS + "</body>\n</html>\n"

def artikel():
    h = head("Ny laddkorridor längs E4 klar (exempel) · Motorpuls", "Exempelartikel: 14 snabbladdare längs E4.", "/laddning/laddkorridor-e4", "img/hero")
    body = f'''
<main id="innehall" class="article">
  <div class="wrap">
    <article>
      <header class="article__head">
        <nav class="crumbs" aria-label="Brödsmulor"><a href="index.html">Start</a> / <a href="index.html#flodet">Laddning</a></nav>
        <span class="meta"><span class="tag">Laddning</span><span class="source">Trafikverket (exempel)</span></span>
        <h1 class="article__title">Ny laddkorridor längs E4 klar: 14&nbsp;stationer mellan Exempelby och Norrstad</h1>
        <p class="article__dek">Den sista stationen öppnade i morse. Alla har minst 150&nbsp;kW och tar betalkort direkt, utan app.</p>
        <p class="byline"><span>Publicerad <b><time datetime="2026-10-29T08:40">29 okt 2026, 08:40</time></b></span><span>Läsetid <b>2 min</b></span><span>Redaktion: <b>Motorpuls</b></span></p>
      </header>
      <figure class="article__figure">
        <div class="frame">{pic("hero", "Abstrakt platshållarbild: ljusstrimmor mot en orange horisont.", "(min-width: 80rem) 76rem, 100vw", eager=True)}</div>
        <figcaption>Platshållarbild (abstrakt). Ersätts av licensierat foto.</figcaption>
      </figure>
      <div class="article__layout">
        <section class="brief" aria-labelledby="brief-h">
          <h2 id="brief-h">I korthet</h2>
          <ul>
            <li>14 snabbladdare på cirka 60 mils sträcka (exempel).</li>
            <li>Minst 150&nbsp;kW per plats, fyra platser per station.</li>
            <li>Betalning med kort i laddaren, utan medlemskap.</li>
          </ul>
        </section>
        <div class="prose">
          <p><strong>EXEMPELTEXT.</strong> Den nya korridoren betyder att det som längst är 55 kilometer mellan två snabbladdare på sträckan, enligt Trafikverkets exempeluppgifter.<sup><a href="#kalla-1" aria-label="Källa 1">1</a></sup></p>
          <p>Utbyggnaden har fått stöd ur ett påhittat statligt program. Operatören uppger att alla platser är anpassade för bilar med släp, något som tidigare saknats på flera ställen längs vägen.<sup><a href="#kalla-2" aria-label="Källa 2">2</a></sup></p>
          <h2>Vad det kostar</h2>
          <p>Priset är i exemplet 5,90 kronor per kWh, med lägre pris nattetid. Det motsvarar ungefär vad andra snabbladdare i regionen tar.<sup><a href="#kalla-2" aria-label="Källa 2">2</a></sup></p>
          <p>Nästa etapp, längs en annan europaväg, är planerad till 2027.<sup><a href="#kalla-1" aria-label="Källa 1">1</a></sup></p>
        </div>

        <section class="sources" aria-labelledby="kallor-h">
          <h2 id="kallor-h">Källor</h2>
          <ol>
            <li id="kalla-1"><div><a href="https://example.com/trafikverket-laddkorridor" rel="noopener" target="_blank">Laddkorridor längs E4 färdigställd (exempel)<span class="visually-hidden"> (öppnas i ny flik)</span></a>
              <div class="meta"><span>Trafikverket</span><span>example.com</span><time datetime="2026-10-29">29 okt 2026</time></div></div></li>
            <li id="kalla-2"><div><a href="https://example.org/operator-pressmeddelande" rel="noopener" target="_blank">Pressmeddelande: 14&nbsp;stationer i drift (exempel)<span class="visually-hidden"> (öppnas i ny flik)</span></a>
              <div class="meta"><span>Laddoperatören</span><span>example.org</span><time datetime="2026-10-28">28 okt 2026</time></div></div></li>
          </ol>
        </section>

        <aside class="ai-note" aria-label="Om texten">
          <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M8 7v4.5M8 4.6v.1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          <p>Texten är skriven med hjälp av AI och faktagranskad mot källorna ovan. Hittar du ett fel? <a href="#">Rapportera en rättelse</a>.</p>
        </aside>

        <p class="more"><a class="btn" href="index.html#flodet" style="text-decoration:none;display:inline-block">Fler nyheter i flödet</a></p>
      </div>
    </article>
  </div>
</main>
'''
    return h + body + FOOTER + NEWSLETTER + ANALYTICS + "</body>\n</html>\n"

open("index.html","w").write(index())
open("artikel.html","w").write(artikel())
print("built")
