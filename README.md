# Motorpuls

Motorpuls är en svensk bilnyhetssajt: https://motorpuls.se

Sajten är statisk HTML, CSS och JavaScript och publiceras med GitHub Pages från `main`.

## Bygga

Artiklar ligger som markdown med YAML-front matter i `content/articles/`. `build.py` genererar:

- `index.html` (startsidan, nyast först)
- `artikel/<slug>/index.html` (en sida per artikel, URL `/artikel/<slug>/`)
- `404.html`, `sitemap.xml`, `robots.txt`

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

Bilderna kopieras till `img/articles/<slug>/` och får WebP-versioner (1600 och 800 px bred, ingen beskärning).
Den första blir huvudbild och og:image, fler bilder blir ett bildspel. Checka in `img/articles/<slug>/` tillsammans med artikeln.
Det äldre fältet `image` (en URL, med `image_credit`) laddas ned till `img/articles/<slug>.webp` som förut.

## Nyhetsbrev

Den orange nyhetsbrevsrutan läggs in av `js/site.js` (efter artikeltexten och som band på startsidan) och sparar adresser i Supabase-projektet `motorpuls`
(tabell `public.newsletter_subscribers`, bara INSERT för den publika nyckeln). Läs adresserna i Supabase (Table Editor eller SQL), inte via sajten.
Integritetssidan byggs av `build.py` till `integritet/index.html`. Kontaktadressen (`KONTAKT` i `build.py`) är en platshållare tills den är bestämd.
Se `DESIGN.md`, Nyhetsbrev.

Sidorna har tills vidare `<meta name="robots" content="noindex">`.
