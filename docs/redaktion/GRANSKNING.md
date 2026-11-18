# Granskning före publicering

Varje artikel granskas i två steg innan den får en PR för publicering. Granskningen görs av en annan agent än den som skrev texten (Språkrådet: AI kan hjälpa, men texten ska alltid granskas och bearbetas). Skribenten rättar, granskaren godkänner.

Underlag till granskaren: artikelns markdown (med frontmatter och `sources`), SKRIVMALL.md och dagens datum.

## Steg A: Redaktören (begriplighet)

Svara ja eller nej på varje punkt. Ett nej ger en konkret ändring.

**Rubrik**
- [ ] Säger rubriken vad som har hänt, med vem och vad?
- [ ] Skulle en 15-åring som inte är bilintresserad förstå den utan att läsa vidare?
- [ ] En mening, högst cirka 70 tecken, rak ordföljd, verb finns?
- [ ] Inga ordlekar, bilder eller gåtor ("vänder på", "sågas", "drar ifrån")?
- [ ] Har rubriken täckning i texten? Inget som överdriver, och förbehåll (USA, förslag, test utomlands, startdatum långt fram) syns.
- [ ] Lockar rubriken till klick på ett ärligt sätt (läsarens nytta, en konkret siffra, ett känt namn eller något nytt)? Är den bara korrekt men tråkig, föreslå en mer lockande variant som fortfarande är sann.
- [ ] Inga relativa tider ("om tre veckor", "i helgen")?

**Ingress**
- [ ] 1 till 2 meningar som svarar på vem, vad, var och när?
- [ ] Säger den vad nyheten betyder för en svensk bilist?
- [ ] Ger den nytt innehåll i stället för att upprepa rubriken?

**Text**
- [ ] Det viktigaste kommer först, bakgrunden sist?
- [ ] Mellanrubrikerna säger något (inte "Bakgrunden", "Siffrorna")?
- [ ] Varje fackord och förkortning förklaras första gången?
- [ ] Inga meningar över cirka 25 ord?
- [ ] Åsikt finns bara under "Lukas analys" och är märkt?
- [ ] Inga tankstreck, siffror enligt SKRIVMALL avsnitt 5?
- [ ] "Kort om nyheten" (summary) är begriplig fristående, utan förkortningar som HQ?

## Steg B: Faktakollen

Granskaren öppnar varje källa i `sources` och kontrollerar varje påstående mot den. Andrahandskällor (andra tidningar) räcker inte för siffror när en förstahandskälla finns (myndighet, bolagets pressmeddelande, domstol, testorganisation). Publicitetsreglerna: kontrollera sakuppgifter så noggrant som omständigheterna medger, även om de tidigare har publicerats.

1. Lista alla kontrollerbara uppgifter: siffror, belopp, datum, namn, titlar, modellnamn, citat, platser och påståenden om orsak.
2. Kontrollera dem mot källan. Fyll i tabellen:

Exempel på ifyllda rader:

| # | Påstående i texten | Källa (URL) | Status | Åtgärd |
|---|---|---|---|---|
| 1 | Boten är 3 000 kronor | https://www.aklagare.se/... bilaga 1A | Stämmer | Ingen |
| 2 | Arbetet tar 20 till 40 år | sverigesradio.se/... | Stämmer, men är egen uträkning av 25 till 50 per år | Skriv "i den takten kan det ta" |
| 3 | "Om fyra veckor" (publicerad 12 nov, gäller 1 dec) | Kalendern | Fel, 19 dagar | Skriv "den 1 december" |

Status är en av: **Stämmer**, **Stämmer delvis** (rätt men förbehåll saknas), **Fel**, **Hittas inte**.

3. Regler för status:
   - **Fel:** rätta, eller stoppa artikeln om felet bär rubriken.
   - **Hittas inte:** ta bort uppgiften, eller skriv vem som påstår den ("enligt The Sunday Times").
   - **Stämmer delvis:** lägg till förbehållet i samma mening.
   - Superlativ ("största", "första", "sämsta") kräver en källa som säger just det. Annars stryks det.
   - Valutaomräkning: kontrollera kurs och datum.
   - Citat ska finnas ordagrant i källan. Översatta citat märks som översatta.
   - Datum i framtiden: kontrollera att det fortfarande stämmer på publiceringsdagen (artiklar schemaläggs i förväg).
4. Kontrollera bildernas licens och fotokredit mot `source_url`.

## Utslag

- **Godkänd:** inga ändringar, eller bara stavning. Gå vidare till PR.
- **Ändra:** konkreta ändringar listade. Skribenten rättar, granskaren kontrollerar bara de ändrade raderna.
- **Stoppa:** rubriken saknar täckning, ett fel bär nyheten, källan går inte att öppna eller nyheten är för gammal. Ingen publicering. Meddela Mr. Motorpuls.

## Färdig prompt till granskaragenten

Klistra in hela blocket och lägg artikeln och SKRIVMALL.md efter.

```
Du är redaktör och faktagranskare på motorpuls.se, en svensk sajt med bilnyheter.
Du har inte skrivit texten. Din uppgift är att hitta fel och oklarheter, inte att
berömma. Skriv allt på svenska. Använd aldrig tankstreck (varken långa eller korta).

Dagens datum: [ÅÅÅÅ-MM-DD]. Artikelns publiceringstid står i frontmatter (date).

Gör så här:

1. REDAKTÖR. Läs rubrik, ingress, summary och text. Gå igenom checklistan i
   GRANSKNING.md steg A. Testa rubriken: skulle en 15-åring utan bilintresse
   förstå vad som hänt? Har rubriken täckning i texten? Lockar den till klick
   utan att överdriva? Följ SKRIVMALL.md.

2. FAKTAKOLL. Öppna varje URL i sources. Lista varje siffra, datum, namn, citat
   och påstående i texten, summary och excerpt. Kontrollera var och en mot
   källan. Hitta inte på något. Kan du inte öppna en källa, skriv det.
   Räkna själv om relativa tider, omräkningar och procent.

3. SVARA exakt i detta format:

UTSLAG: Godkänd | Ändra | Stoppa
MOTIVERING: en eller två meningar.

RUBRIK
Nu: ...
Förslag: ... (en mening, högst 70 tecken, säger vad som hänt)

INGRESS
Nu: ...
Förslag: ...

BEGRIPLIGHET
- [rad eller citat] -> [konkret ändring]

FAKTA
| # | Påstående | Källa (URL) | Status | Åtgärd |
Status: Stämmer, Stämmer delvis, Fel, Hittas inte.

BORT ELLER MJUKA UPP
- [påståenden som inte går att belägga, och föreslagen formulering]

Regler: Stoppa om rubriken saknar täckning, om ett fel bär nyheten eller om
huvudkällan inte går att öppna. Ändra om något i checklistan är nej eller om
någon uppgift är Fel, Stämmer delvis eller Hittas inte. Godkänd bara om allt
är ja och allt stämmer.
```

## Källor

- Medieombudsmannen, Publicitetsregler (Ge korrekta nyheter): https://medieombudsmannen.se/publicitetsregler/
- Språkrådet, Ta hjälp av AI (granska alltid, frågan om ord en 15-åring förstår): https://www.isof.se/svenska-spraket/klarsprak/klarsprakshjalpen/skriv-klarsprak/ta-hjalp-av-ai
- Google Search Central, Creating helpful content (rubrik utan överdrift, inga lätt kontrollerade faktafel): https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- Mediekompass, Journalistiskt skrivande (källkritik): https://mediekompass.se/publicistguiden/kapitel-10-journalistiskt-skrivande/
