# Motorpuls

Motorpuls är en svensk bilnyhetssajt: https://motorpuls.se

Sajten är statisk HTML, CSS och JavaScript och publiceras med GitHub Pages från `main`.

## Bygga

Artiklar ligger som markdown med YAML-front matter i `content/articles/`. `build.py` genererar:

- `index.html` (startsidan, nyast först)
- `artikel/<slug>/index.html` (en sida per artikel, URL `/artikel/<slug>/`)
- `404.html`, `sitemap.xml`, `robots.txt`, `feed.xml` (RSS)
- `img/og/<slug>.jpg` (delningsbild 1200×630, checka in den tillsammans med artikeln)

Kräver Python 3.12 eller senare (build.py använder bland annat nästlade citattecken i f-strängar).

```
python3 -m venv .venv && .venv/bin/pip install markdown pyyaml pillow
.venv/bin/python build.py
```

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

Sidorna indexeras av sökmotorer. Bara `404.html` har `<meta name="robots" content="noindex">`.
