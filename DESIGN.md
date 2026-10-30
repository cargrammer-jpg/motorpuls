# Motorpuls: designriktning (v1, prototyp)

**Tes:** "Instrumentpanel möter tidning." Mörk, premium redaktionell yta, stor tung rubrik, stora bilder,
och ett tydligt daterat flöde där källan står överst. Inga klickbeten, inga versaler-skrik, inga reklamplatser (än).

## Palett v1 (mörk, "lite coolare"): roller låsta
| Token | Hex | Roll |
|---|---|---|
| bg | `#0B0D10` | sidbakgrund, nära-svart grafit + svag orange glöd upptill + filmkorn 5 % |
| surface / raised | `#151A20` / `#1B2129` | kort, chips, popup |
| line / line-strong | `#252C35` / `#3A434E` | hårlinjer |
| text | `#EEF1F4` | rubriker, brödtext (17:1) |
| text-2 | `#C3CAD1` | ingress, sekundär (11,8:1) |
| muted | `#929CA7` | metadata, tider (7:1) |
| pulse | `#FF5B1F` | dekor: prickar, aktiv-markering, glöd |
| pulse-text | `#FF8A5C` | kategoritaggar, länkar (8,4:1) |

Logga: riktning A, Heartline. `img/logo.svg` är en kopia av `brand/final/motorpuls-wordmark-light-on-dark.svg` (kurvor). Favicons i `favicon/` (kopior från `brand/final/favicon/`).
Copy: inga tankstreck (en- eller em-streck) i rubriker eller text; använd komma eller kolon.

## Typografi (fria, självhostade woff2, subset Latin+svenska)
- **Archivo** (variabel, wdth 62 till 125, wght 100 till 900): rubriker i *expanded* bredd 112 till 125, vikt 750 till 800, tät spärr (-0.02em). Wordmark: wdth 125 / 850. UI-text i normalbredd.
- **Newsreader** (variabel, opsz): ingress och artikeltext, 19 till 20px, radhöjd 1,6, max 66 tecken.
- **DM Mono**: tidsstämplar, datumrubriker, källdomäner: "instrument"-detaljen.

## Layout
- Mobil först, 4 → 12 kolumner, max 1280px, generös luft (Top Gear).
- Startsida: toppnyhet med stor 16:10-bild + jättelik rubrik (The Verge-tyngd), bredvid en kompakt "Senaste"-lista.
- Kategorichips (Elbil, Sportbil, Tesla, Laddning, Bränsle) filtrerar flödet.
- Flöde grupperat per dag med mono-datumrubrik; varje post: källa + tid överst (Electrek), rubrik, en mening ingress, liten bild.
- Artikel: kicker → rubrik → ingress → bild → "I korthet" (3 punkter) → kort text → **Källor** → AI-notis.

## Rörelse
Sparsam: långsam puls på prick i loggan, 180 ms hover/fokus, popup glider upp 220 ms,
cross-document view transition. Allt av under `prefers-reduced-motion: reduce`.

## Bilder
Artikelbilder (t.ex. pressbilder) visas alltid i sitt eget format: ingen beskärning, ingen text eller toning ovanpå, fotokredit i bildtexten. Artiklar utan bild visas utan bildruta.

Prototypen (historik):
Inga pressbilder. Lokalt genererade abstrakta "långexponering"-platshållare (tools_placeholders.py),
mörk studio + färgad horisont per kategori. Ersätts senare av licensierade/egna foton i samma format (16:10).

## Nyhetsbrev
Liten icke-modal `<aside popover="manual">`-ruta (toast-mönster, ingen modal) nere till höger (bottom sheet på mobil), visas en gång
efter ~55 % scroll, stängs med knapp eller Esc, minns valet i localStorage. Stjäl inte fokus.
