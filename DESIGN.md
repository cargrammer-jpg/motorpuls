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
- **Newsreader** (variabel, opsz): ingress och artikeltext. Brödtext 17px mobil, 18px från 48rem, radhöjd 1,6, spalt 40rem (cirka 65 tecken per rad). Se Artikelmall v2.
- **DM Mono**: tidsstämplar, datumrubriker, källdomäner: "instrument"-detaljen.

## Layout
- Mobil först, 4 → 12 kolumner, max 1280px, generös luft (Top Gear).
- Startsida: toppnyhet med stor 16:10-bild + jättelik rubrik (The Verge-tyngd), bredvid en kompakt "Senaste"-lista.
- Kategorichips (Elbil, Sportbil, Tesla, Laddning, Bränsle) filtrerar flödet.
- Flöde grupperat per dag med mono-datumrubrik; varje post: källa + tid överst (Electrek), rubrik, en mening ingress, liten bild.
- Artikel (v2): kategori, rubrik, ingress, byline, "Kort om nyheten" (2 till 4 punkter), huvudbild eller bildspel, text, **Källor**, AI-notis.

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

## Artikelmall v2 (lättare läsning)
Mål: mindre brödtext, kortare stycken, en lugn läsrad och en tydlig sammanfattning överst.

**Läsyta.** En centrerad spalt `.article__col`, max 40rem, för rubrik, sammanfattning, text och källor. Bilder får en bredare scen, max 62rem.
Rubrik 2 till 3,4rem (Archivo 115 % bredd, 820). Ingress Newsreader 1,15 till 1,3rem, radhöjd 1,5.
Brödtext Newsreader 17px (mobil) och 18px (från 48rem), radhöjd 1,6, färg `#DCE1E6` (14,8:1 mot bg), 1,3em mellan stycken.
H2: Archivo 1,2 till 1,35rem, 760, med en liten orange pulsprick före. 2,4em luft ovanför och 0,6em under, så avsnitten syns när man skummar.
Tusentalsavgränsare ("1 079 hk") renderas med hårt mellanslag så att tal aldrig bryts över två rader.
Redaktionellt: sikta på stycken om 2 till 3 meningar. Mallen kan inte korta texten, det gör skribenten.

**Sammanfattning, "Kort om nyheten"** (`summary` i front matter, 2 till 4 punkter). `<section class="summary" aria-labelledby>` med `h2` och `ul`.
Står direkt efter bylinen, före bilden, så att den syns utan scroll även på mobil.
Accent: 3px vänsterkant i `pulse` `#FF5B1F`, tonad bakgrund (pulse 13 % till 5 % över bg) och en tunn orange kontur.
Etikett i DM Mono versaler, `pulse-text` `#FF8A5C` (7,3:1 mot rutan). Punkterna i Archivo 1rem, `text` `#EEF1F4` (15:1), orange prickar.

**Bilder** (`images` i front matter). Första bilden är huvudbild och og:image: laddas direkt med `fetchpriority="high"` och preload.
Övriga laddas lazy. Bilder beskärs aldrig: en enda bild visas i sitt eget format, flera bilder delar en 3:2-scen med
`object-fit: contain` och svart kant (letterbox) när formatet skiljer sig. Ingen text eller toning ovanpå bilden.
Bildtext under bilden i DM Mono, `muted` (7:1): valfri `caption`, punkt, sedan kredit ("Foto: Aston Martin").
Bygget gör WebP i 1600 och 800 px bredd (srcset), bara storleksändring.

**Bildspel** (två eller fler bilder). Utan JS: en vågrät rad med scroll-snap där nästa bild sticker fram (88 % bredd), att svepa i.
Med JS (`js/site.js`, inga bibliotek): helbreda bilder, runda knappar "Föregående bild" och "Nästa bild" (2,75rem, aria-label),
räknare "2 / 5" (läses upp som "Bild 2 av 5", aria-live polite), svep via inbyggd scroll-snap, piltangenter samt Home och End
när bildspelet har fokus. Knappar och räknare ligger till höger på bildtextraden. Smidig scroll bara utan `prefers-reduced-motion: reduce`.

**Äldre artiklar.** Fältet `image` (en URL) med `image_credit` fungerar som förut och ger en bild i eget format. Artiklar utan bild eller sammanfattning visas utan de rutorna.
