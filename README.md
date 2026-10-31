# Motorpuls

Motorpuls är en svensk bilnyhetssajt: https://motorpuls.se

Sajten är statisk HTML, CSS och JavaScript och publiceras med GitHub Pages från `main`.

## Bygga

Artiklar ligger som markdown med YAML-front matter i `content/articles/`. `build.py` genererar:

- `index.html` (startsidan, nyast först)
- `artikel/<slug>/index.html` (en sida per artikel, URL `/artikel/<slug>/`)
- `404.html`, `sitemap.xml`, `robots.txt`, `feed.xml` (RSS)
- `feed/<kategori>.xml` (RSS per kategori, plus `feed/sverige.xml` när någon artikel har `sweden: true`)
- `img/og/<slug>.jpg` (delningsbild 1200×630, checka in den tillsammans med artikeln)
- `sitemap-news.xml` (Google News-sitemap, bara artiklar från de senaste två dygnen räknat vid bygget, så sajten bör byggas om minst en gång per dygn, se schemat som föreslås i PR:en)
- `om/` och `om/lukas/` ur `content/pages/*.md` (om-sidan och författarsidan för Lukas)
- `img/ld/<slug>-16x9.jpg`, `-4x3.jpg`, `-1x1.jpg` (bilder för NewsArticle-JSON-LD, checka in dem som `img/og/`; skapas inte om huvudbildens licens förbjuder beskärning)

### Google Nyheter och Discover

Artiklarna har NewsArticle-JSON-LD (författare med länk till `/om/lukas/`, utgivare med logotyp, bilder i 16:9, 4:3 och 1:1),
`<meta name="robots" content="max-image-preview:large">` och en synlig byline med publiceringsdatum och, om fältet `updated`
finns, "Uppdaterad <datum>". För Search Console-verifiering med HTML-tagg: sätt `GOOGLE_SITE_VERIFICATION` i `build.py`
till koden från Search Console, då hamnar taggen på startsidan.

Kräver Python 3.12 eller senare (build.py använder bland annat nästlade citattecken i f-strängar).

```
python3 -m venv .venv && .venv/bin/pip install markdown pyyaml pillow
.venv/bin/python build.py
```

### Populärt just nu

Startsidans "Populärt just nu" läser `data/popular.json` (artiklar i ordning efter sidvisningar). Uppdatera den med
`CLOUDFLARE_ANALYTICS_TOKEN=... .venv/bin/python tools/update_popular.py` (Cloudflare Web Analytics, senaste 7 dygnen;
token med Account Analytics: Read, skrivs aldrig ut). Saknas filen fylls rutan med de senaste artiklarna.

### RSS

`feed.xml` har alla artiklar, `feed/<kategori>.xml` bara en kategori (RSS 2.0, samma ordning som startsidan). Alla sidor har
`<link rel="alternate" type="application/rss+xml">` till `feed.xml`. Startsidan listar även kategoriflödena och varje artikel sitt
kategoriflöde. Sidfoten har länken RSS (ikon + text) och RSS per kategori. Artiklar slutar med raden "Prenumerera via RSS".
Det finns inga kategorisidor ännu; när de kommer ska raden "Prenumerera via RSS" även stå där.

### Push-rutan (förhandsvisning, av i produktion)

Feature-flaggan `PUSH_BOX` i build.py är av. Förhandsbygge med rutan: `MOTORPULS_PUSH=1 .venv/bin/python build.py --out _preview`
(fungerar bara med `--out`; projektroten byggs om utan rutan efteråt). Visa rutan direkt med `?push=visa`, iPhone-tipset med `?push=ios`.
Källor i `push/` (push.js, push.css, sw.js), backend-utkast i `supabase/` (inte kört). Med flaggan av stoppar bygget om något av
push finns i utdata. Se `DESIGN.md` (Push-rutan) och `supabase/README.md`.

### Publicering

GitHub Pages byggs av GitHub Actions (`.github/workflows/pages.yml`). Vid varje push till `main` körs
`python build.py --out _site`, och bara den publika delen publiceras: genererade sidor, `css/`, `js/`, `fonts/`, `img/`, `favicon/` och `CNAME`.
`build.py`, `content/`, `DESIGN.md`, `brand/` och `drafts/` hamnar inte på sajten. Bygget skapar också bilder som saknas
(WebP-varianter, `img/og/<slug>.jpg`) och kontrollerar att alla lokala länkar finns. Pull requests byggs och kontrolleras men publiceras inte.
Det genererade resultatet i roten checkas fortfarande in som förut (`.venv/bin/python build.py`), så det går att granska i diffar.
Beroenden med fasta versioner finns i `requirements.txt`.

Valfria fält i front matter (se kommentaren överst i `build.py` och `DESIGN.md`, Artikelmall v2):

```yaml
summary:
  - "Valhalla Spider har samma drivlina som kupén: 1 079 hk."
  - "Leveranserna börjar tredje kvartalet 2027."
images:
  - src: valhalla-spider-fram.jpg        # letas i drafts/img/<slug>/, eller relativ/absolut sökväg
    alt: "Valhalla Spider snett framifrån med taket av"
    credit: "Foto: Aston Martin"
    license: "Pressbild, endast redaktionell användning"
    caption: "Valfri bildtext"           # valfritt
sweden: true                           # valfritt: nyheten gäller Sverige, visar en liten svensk flagga
```

`sweden: true` ger en liten svensk flagga (äldre, mörkare färger) i övre vänstra hörnet av huvudbilden eller bildspelet
och på artikelns kort på startsidan. Saknar artikeln bild hamnar flaggan vid kategorin. Flaggan är ett eget element ovanpå
bilden, bildfilerna ändras aldrig. Utelämnat eller `false` betyder ingen flagga.

Bilderna kopieras till `img/articles/<slug>/` och får WebP-versioner (1600, 800 och 400 px bred, ingen beskärning).
Den första blir huvudbild (och beskärs till delningsbilden `img/og/<slug>.jpg`), fler bilder blir ett bildspel. Checka in `img/articles/<slug>/` tillsammans med artikeln.
Det äldre fältet `image` (en URL, med `image_credit`) laddas ned till `img/articles/<slug>.webp` som förut.

## Nyhetsbrev i sidfoten (förhandsvisning)

Feature-flaggan `NEWSLETTER_BOX` i build.py är av. Förhandsbygge med rutan: `MOTORPULS_NYHETSBREV=1 .venv/bin/python build.py --out _preview`
(bara med `--out`, projektroten byggs om utan rutan). Källor i `nyhetsbrev/` (nyhetsbrev.css, nyhetsbrev.js, nyhetsbrev-sida.js). Med flaggan av stoppar
bygget om något av nyhetsbrevet finns i utdata. Anmälan går till edge-funktionen `newsletter-subscribe` med dubbel bekräftelse
och utskick via Resend (se `supabase/README.md`). Med flaggan på byggs också `/integritet/`, `/prenumeration/bekrafta/` och
`/prenumeration/avsluta/`. Ingen kontaktadress visas på sajten.

Sidorna har tills vidare `<meta name="robots" content="noindex">`.
