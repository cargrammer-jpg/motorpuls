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

## Nyhetsbrev (orange ruta, v2)
Den gamla popupen smälte in och sparade inga adresser, så den är borttagen. Ersatt av en orange ruta som syns.

**Utseende.** Kort med orange gradient, `pulse` `#FF5B1F` till `#FF7A3D`, 8px rundning och en mjuk orange skugga.
All text är mörk `#0B0D10`: 6,3:1 mot `#FF5B1F` och 7,5:1 mot `#FF7A3D` (WCAG AA). Vit text på orange ger bara 3,1:1 och används inte.
Etikett "Nyhetsbrev" i DM Mono versaler, rubrik "Få Motorpuls i inkorgen" i Archivo 820, en rad i Newsreader.
Fält med ljus bakgrund `#FFF7F2` och 2px mörk kant (18:1), mörk knapp "Prenumerera" med vit text (19:1).
Fokus: 3px mörk ring med 2px avstånd. Felmeddelanden står i en ruta med mörk vänsterkant, aldrig röd text på orange.

**Placering.** Ingen popup och ingen sticky-list.
- Artikel: efter text, källor och AI-notisen, före "Fler nyheter". Läsaren har läst klart och källorna hör ihop med texten.
- Startsida: som band i flödet "Alla artiklar", efter dagen med den tredje artikeln. Bara en artikel: efter huvudkortet.

**Funktion** (`js/site.js`). Rutan läggs in med JS, eftersom anmälan kräver JS. Utan JS visas ingen ruta. Därför behöver sidorna inte byggas om för att rutan ska synas.
Anmälan är en vanlig `fetch` POST till Supabase REST (`/rest/v1/newsletter_subscribers`, `Prefer: return=minimal`) med projektets publika nyckel (publishable). Inget supabase-js.
Adressen trimmas och görs om till gemener. Honungsfälla (dolt fält `webbplats`): ifyllt ger ett "tack" men inget sparas.
Statusrad med `role="status"` och `aria-live="polite"`. Klar: formuläret ersätts av "Tack! Du är anmäld." som får fokus.
En adress som redan finns (HTTP 409) visas som lyckad anmälan, så att ingen kan ta reda på vilka adresser som är anmälda.
Rörelse: bara en kort intoning av tackmeddelandet, och bara utan `prefers-reduced-motion: reduce`.

**Data.** Supabase-projektet `motorpuls` (Stockholm, eu-north-1). Tabellen `public.newsletter_subscribers`: `id`, `email` (unik, gemener, kontrollerat format, max 254 tecken), `created_at`, `source` (sidans sökväg), `consent`.
RLS är på. Rollen anon får bara INSERT av `email`, `source` och `consent`, med kravet `consent = true`. Ingen SELECT, UPDATE eller DELETE för anon. Service-role-nyckeln används aldrig på sajten.
Utskick görs senare med Resend. Sidan `/integritet/` beskriver vad som sparas.

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
`object-fit: contain` och svart kant (letterbox) när formatet skiljer sig. Ingen text eller toning ovanpå bilden (enda undantaget är den lilla svenska flaggan, se nedan).
Bildtext under bilden i DM Mono, `muted` (7:1): valfri `caption`, punkt, sedan kredit ("Foto: Aston Martin").
Bygget gör WebP i 1600 och 800 px bredd (srcset), bara storleksändring.

**Bildspel** (två eller fler bilder). Utan JS: en vågrät rad med scroll-snap där nästa bild sticker fram (88 % bredd), att svepa i.
Med JS (`js/site.js`, inga bibliotek): helbreda bilder, runda knappar "Föregående bild" och "Nästa bild" (2,75rem, aria-label),
räknare "2 / 5" (läses upp som "Bild 2 av 5", aria-live polite), svep via inbyggd scroll-snap, piltangenter samt Home och End
när bildspelet har fokus. Knappar och räknare ligger till höger på bildtextraden. Smidig scroll bara utan `prefers-reduced-motion: reduce`.

**Äldre artiklar.** Fältet `image` (en URL) med `image_credit` fungerar som förut och ger en bild i eget format. Artiklar utan bild eller sammanfattning visas utan de rutorna.

## Svensk flagga (`sweden: true`)
Önskemål från ALX: när en nyhet gäller Sverige visas en liten svensk flagga i kanten av bilden eller artikeln.

**Färger och form.** Den äldre, mörkare flaggan: blå `#005293`, gul `#FECB00`. Proportioner 5:2:9 vågrätt och 4:2:4 lodrätt (16x10).
Inline-SVG i `build.py` (`FLAG_SVG`), 2px rundade hörn, tunn mörk kontur och en mjuk skugga så att den syns mot både ljusa och mörka bilder.

**Placering.** Övre vänstra hörnet, där varken kredit (under bilden) eller bildspelets knappar och räknare (nere till höger) ligger.
- Artikel: över huvudbilden eller bildspelets scen, 28px bred på mobil och 34px från 48rem. I bildspelet sitter flaggan på bildspelet, inte på varje bild, så den står still när man bläddrar.
- Startsida: 28 till 32px på huvudkortets bild, 18px på miniatyren i flödet och 20px vid kategorin i listan "Senaste".
- Utan bild: 20px bredvid kategorin, i artikelns huvud och på korten.

**Bildvillkor.** Flaggan är ett eget DOM-element (`.flag`, `pointer-events: none`) ovanpå bilden. Bildfilerna ändras aldrig, vilket pressvillkoren kräver.
Det är det enda tillåtna elementet ovanpå en bild.

**Tillgänglighet.** `role="img"`, `aria-label="Gäller Sverige"` och `title` med samma text. SVG:n är `aria-hidden`.

