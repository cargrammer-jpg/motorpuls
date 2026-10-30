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

Har en artikel `image` i front matter laddas bilden ned till `img/articles/` och konverteras till WebP
(samma bildformat, ingen beskärning, max 1600 px bred).

Sidorna har tills vidare `<meta name="robots" content="noindex">`.
