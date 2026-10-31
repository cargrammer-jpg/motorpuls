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
- **Newsreader** (variabel, opsz): ingress och artikeltext. Brödtext 16px mobil, flytande upp till 17px på dator, radhöjd 1,6, spalt 40rem (cirka 65 tecken per rad). Se Artikelmall v2.
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

## Nyhetsbrevsrutan i sidfoten (förhandsvisning, `NEWSLETTER_BOX` av)
**Utseende.** Synlig etikett "Din e-postadress". Mörk panel `surface` `#151A20` med 1px hårlinje `line` och 2px orange topplinje (`pulse`). Etiketten "Nyhetsbrev" i `pulse-text` `#FF8A5C`, rubrik i `text`, brödtext i `text-2` som resten av sidfoten. Mörkt fält med 1px kant `#6B7682` (3,9:1 mot fältet, 3,6:1 mot panelen), orange knapp "Prenumerera" med mörk text (6,3:1). Fokus: 2px orange ring (`pulse-text`), 2px avstånd. Ingen orange fyllning eller glöd.
Text: "Få Motorpuls i inkorgen" och "De viktigaste bilnyheterna, korta och med källor. Du hänger med utan att leta." Under fältet: "Helt gratis, avsluta när du vill."

**Placering.** Dator (från 56rem): höger kolumn bredvid sidfotens logga, text och länkar. Mobil: under länkarna, före raden med ©, knappen i full bredd.
Rutan står i HTML från början och statusraden har reserverad höjd, så inget layoutskift. Utan JS döljs formuläret och en rad säger att anmälan kräver JavaScript.

**Funktion** (`nyhetsbrev/nyhetsbrev.js`, laddas bara med flaggan på). `fetch` POST till edge-funktionen `newsletter-subscribe`
med adressen, sidans sökväg och honungsfältet. Dubbel bekräftelse: tackraden säger "Nästan klart! Vi har skickat ett mejl till dig..."
och får fokus. 400 och 429 ger egna felrader. Samma svar oavsett om adressen redan prenumererar. Under fältet: "Helt gratis, avsluta
när du vill. Du får ett mejl där du bekräftar först." och länken "Så hanterar vi din adress" till `/integritet/`. Rörelse bara utan
`prefers-reduced-motion: reduce`.

**Bekräfta och avsluta** (`/prenumeration/bekrafta/` och `/prenumeration/avsluta/`, `nyhetsbrev/nyhetsbrev-sida.js`). Länkarna i
mejlen går hit med `?token=`. Att öppna sidan ändrar inget; först knappen (samma orange knapp som rutan) POSTar koden. Koden tas
bort ur adressfältet. Svaret står i en statusrad som får fokus. noindex. Supabase visar inte HTML från sin egen domän, därför ligger
sidorna på motorpuls.se.

**Integritet** (`/integritet/`, bara med flaggan på). Ingen kontaktadress (ALX:s beslut). Tjänster: Supabase (lagring, Stockholm),
Resend (utskick), Cloudflare Web Analytics.

## RSS
Sidfoten: länken "RSS" med ikon (orange ruta, mörka vågor) och "RSS per kategori" med en länk per kategori. Artikelns slut: en
lugn rad "Prenumerera via RSS: <kategori> · Alla nyheter" i muted-färg, länkar i textfärg (7:1 respektive 16:1 mot bakgrunden).

## Push-rutan (förhandsvisning, `PUSH_BOX` av)
**Utseende.** Samma orange ruta som nyhetsbrevet (PR #15): gradient `#FF5B1F` till `#FF7A3D`, 8px rundning, mörk text `#0B0D10`
(6,3:1 och 7,5:1). "Ja tack": mörk knapp med vit text (19:1). "Inte nu": genomskinlig knapp med 2px mörk kant och mörk text.
Fokus: 3px mörk ring med 2px avstånd. iPhone-tipset står i en ruta med mörk vänsterkant (5,2:1).

**Beteende.** Webbläsarens fråga om notiser visas aldrig av sig själv, bara när läsaren trycker "Ja tack". "Inte nu" gömmer
rutan i 30 dagar (localStorage). Rutan visas inte om notiser redan är tillåtna eller nekade, eller om webbläsaren saknar Web Push.
iOS Safari utanför hemskärmen (`navigator.standalone === false`): tipset om Lägg till på hemskärmen visas i stället för "Ja tack".
Service workern (`/sw.js`) registreras först efter ett ja och hanterar bara `push` och `notificationclick` (ingen cache).

**Placering, utan layoutskift.** Artikel: i flödet efter AI-notisen, och bara om platsen ligger under skärmkanten när skriptet körs.
Startsida: fast ruta nere (hel bredd på mobil, nere till höger på dator) när läsaren har skrollat till "Alla artiklar". Ingen
modal, rutan tar inte fokus, Esc stänger den. Intoning bara utan `prefers-reduced-motion: reduce`.

## Artikelmall v2 (lättare läsning)
Mål: mindre brödtext, kortare stycken, en lugn läsrad och en tydlig sammanfattning överst.

**Läsyta.** En centrerad spalt `.article__col`, max 40rem, för rubrik, sammanfattning, text och källor. Bilder får en bredare scen, max 62rem.
Rubrik 1,85 till 3rem (Archivo 115 % bredd, 820). Ingress Newsreader 1,05 till 1,15rem, radhöjd 1,5.
Brödtext Newsreader 16px (mobil) till 17px (dator, flytande med clamp()), radhöjd 1,6, färg `#DCE1E6` (14,8:1 mot bg), 1,3em mellan stycken.
H2: Archivo 1,125 till 1,25rem, 760, med en liten orange pulsprick före. 2,4em luft ovanför och 0,6em under, så avsnitten syns när man skummar.
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

