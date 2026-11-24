# Sidorna /verktyg/ och /verktyg/laddkostnad/. build.py anropar render() och lägger in path() i sitemap.xml.
# Kalkylatorn är js/laddkostnad.js. Stilen är css/verktyg.css och bäddas bara in här, inte i övriga sidor.
import os

UPDATED = "2026-11-23T01:00:00+01:00"
NB = "\u00a0"
INDEX_PATH = "/verktyg/"
TOOL_PATH = "/verktyg/laddkostnad/"
TOOL_NAME = "Laddkostnad: vad kostar det att ladda elbilen?"
INDEX_DESC = "Verktyg från Motorpuls som räknar i webbläsaren. Först ut: vad det kostar att ladda elbilen."
TOOL_DESC = ("Räkna vad det kostar att ladda elbilen per mil, månad och år. "
             "Startvärdena är exempel. Jämför hemma, snabbladdning och bensin.")
OG = dict(src="/img/og/verktyg-laddkostnad.jpg", w=1200, h=630,
          alt="Laddkostnad: vad kostar det att ladda elbilen? Verktyg på Motorpuls.")


def paths():
    return ((INDEX_PATH, UPDATED), (TOOL_PATH, UPDATED))


def faq_pairs():
    """Samma strängar i den synliga FAQ-sektionen och i FAQPage."""
    n = NB
    return [
        ("Hur räknas kostnaden per mil?",
         "Förbrukningen i kWh per 100 km delas med 10, eftersom 1 mil är 10 km. Det är kilowattimmar ur batteriet per mil. "
         "Hemma multipliceras det med 1 plus laddförlusten i procent delat med 100, och sedan med elpriset. "
         "Snabbladdning multipliceras bara med snabbladdningspriset. Kostnaden per mil är andelen hemma gånger "
         "hempriset per mil plus resten gånger snabbladdningspriset per mil."),
        ("Vad är andel hemmaladdning?",
         "Det är hur stor del av körsträckan du räknar som hemmaladdning. Resten räknas som snabbladdning. "
         "80 procent hemma betyder att 20 procent av milen får snabbladdningspriset."),
        ("Ska elpriset hemma innehålla nät, skatt och moms?",
         "Ja. Skriv det du betalar per kilowattimme från väggen, med elhandel, elnät, energiskatt och moms. "
         f"Exemplet 2,34 kronor är SCB:s totalpris för hushåll med minst 15{n}000 kWh per år under första halvåret 2026, "
         "avrundat från 234,26 öre. Det är ett genomsnitt, inte din faktura. Fasta avgifter är utslagna på varje "
         "kilowattimme, så priset för en extra laddad kilowattimme kan vara ett annat."),
        ("Varför finns laddförlust bara för hemma?",
         "Förlusten hemma är el som mäts i huset men inte hamnar i batteriet, till exempel i laddbox och ombordladdare. "
         "På en publik snabbladdare betalar du oftast per kilowattimme som laddaren debiterar. Verktyget antar att den "
         "mängden motsvarar förbrukningen ur batteriet. Sätt förlusten till 0 om din förbrukning redan är mätt från väggen."),
        ("Är värdena i fälten aktuella priser?",
         "De är startvärden som du ska byta. Elpriset 2,34 kronor per kWh kommer från SCB, första halvåret 2026. "
         "Snabbladdningen 6 kronor, förbrukningen 18 kWh per 100 km, 100 mil i månaden, 80 procent hemma, "
         "10 procent förlust, 0,7 liter bensin per mil och 18 kronor litern är runda exempel, inte uppmätta fakta. "
         "Ditt avtal, din bil och stationen du använder styr resultatet."),
    ]


def _css(b):
    with open(os.path.join(b.ROOT, "css", "verktyg.css"), encoding="utf-8") as f:
        t = f.read()
    if "</" in t:
        raise SystemExit("css/verktyg.css innehåller </ och kan inte bäddas in i <style>")
    return "<style>\n" + t + "</style>\n"


def _sources(b):
    items = (
        ("SCB: Priser på el för hushåll, första halvåret 2026. Hushåll med 15 000 kWh eller mer: totalpris 234,26 öre/kWh "
         "(elhandel 94,42, elnät 56,99, energiskatt 36,00, moms 46,85). Hämtat från SCB:s API 23 november 2026.",
         "https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__EN__EN0301__EN0301A/SSDHalvarElHus/"),
        ("Skatteverket: Skatt på el. Skattesatsen för 2026 är 36,0 öre per kWh exklusive moms. Läst 23 november 2026.",
         "https://www.skatteverket.se/foretag/skatterochavdrag/punktskatter/energiskatter/skattpael.4.15532c7b1442f256bae5e4c.html"),
        ("Trafikanalys: Körsträckor 2025, Statistik 2026:10, publicerad 21 september 2026. En personbil körde i genomsnitt "
         "1 243 mil. Elbilar och laddhybrider körde ungefär 1 700 mil.",
         "https://www.trafa.se/globalassets/statistik/vagtrafik/korstrackor/2025/korstrackor-2025---2026-09-21.pdf"),
        ("OKQ8: Kostnad ladda elbil, egna laddare i Sverige. 5,44 kr/kWh vid 50 kW och 5,69 kr/kWh vid 150 till 200 kW. "
         "Lokala avvikelser kan förekomma. Läst 23 november 2026.",
         "https://www.okq8.se/elbilsladdning/kostnad-ladda-elbil/"),
        ("Circle K: Laddning, priser för privatkunder. Ultrasnabbladdare 300 till 400 kW: 6,69 kr/kWh i appen och vid "
         "engångsbetalning. Läst 23 november 2026.",
         "https://www.circlek.se/laddning/priser"),
        ("Energimarknadsinspektionen: jämför elavtal på Elpriskollen. Där jämför du elhandeln, inte nätet och inte skatten.",
         "https://ei.se/konsument/el/elavtal/jamfor-elavtal-pa-elpriskollen"),
    )
    lis = "".join(
        f'''
            <li><div><a href="{b.esc(u)}" rel="noopener" target="_blank">{b.nbnum(b.esc(t))}<span class="visually-hidden"> (öppnas i ny flik)</span></a>
              <div class="meta"><span>{b.esc(b.host(u))}</span></div></div></li>'''
        for t, u in items)
    return f'''
        <section class="sources" aria-labelledby="kallor-h">
          <h2 id="kallor-h">Källor</h2>
          <ol>{lis}
          </ol>
        </section>'''


def _kr(whole, frac=None):
    """Visning som js/laddkostnad.js formatKr: hårt mellanslag i tusental och före kr."""
    body = f"{whole}{NB}{frac}" if frac else str(whole)
    # tusental: 7040 -> 7 040 redan skickas in uppdelat när det behövs
    return body + NB + "kr"


def tool_inner():
    """Formulär, resultatexempel och förklaring. Siffrorna matchar js/laddkostnad.js med startvärdena."""
    mil, manad, ar = _kr("5,87"), _kr("587"), _kr("7", "040")
    hemma_mil, hemma_m, hemma_a = _kr("4,63"), _kr("371"), _kr("4", "448")
    snabb_mil, snabb_m, snabb_a = _kr("10,80"), _kr("216"), _kr("2", "592")
    bensin_mil, bensin_m, bensin_a = _kr("12,60"), _kr("1", "260"), _kr("15", "120")
    diff = _kr("8", "080")
    return f'''
    <div class="tool__stage">
      <div class="tool__grid">
        <section class="tool__panel tool__result" aria-labelledby="resultat-h">
          <h2 id="resultat-h">Resultat</h2>
          <div id="ladd-resultat" aria-live="polite" aria-atomic="true">
            <p class="tool__status" id="ladd-status">Räkneexempel med startvärdena i formuläret. Med JavaScript uppdateras siffrorna när du ändrar ett fält. Formeln står under kalkylatorn.</p>
            <p class="tool__err" id="ladd-fel" hidden></p>
            <div id="ladd-siffror">
              <p class="tool__kwh" id="out-kwh">1,80 kWh per mil ur batteriet, 1,98 kWh från väggen hemma.</p>
              <div class="tool__figs">
                <p class="tool__hero"><span class="tool__figlabel">Per mil</span> <strong id="out-mil">{mil}</strong></p>
                <ul class="tool__pair">
                  <li><span class="tool__figlabel">Per månad</span> <strong id="out-manad">{manad}</strong></li>
                  <li><span class="tool__figlabel">Per år</span> <strong id="out-ar">{ar}</strong></li>
                </ul>
              </div>
              <div class="tool__split">
                <div class="tool__card">
                  <h3 id="out-hemma-rubrik">Hemma, 80 procent</h3>
                  <p id="out-hemma-mil">{hemma_mil} per mil vid hemmaladdning</p>
                  <p id="out-hemma-tid">{hemma_m} per månad, {hemma_a} per år för den andelen</p>
                </div>
                <div class="tool__card">
                  <h3 id="out-snabb-rubrik">Snabbladdning, 20 procent</h3>
                  <p id="out-snabb-mil">{snabb_mil} per mil vid snabbladdning</p>
                  <p id="out-snabb-tid">{snabb_m} per månad, {snabb_a} per år för den andelen</p>
                </div>
                <div class="tool__card" id="out-bensin">
                  <h3>Bensinbil, exempel</h3>
                  <p id="out-bensin-mil">{bensin_mil} per mil</p>
                  <p id="out-bensin-tid">{bensin_m} per månad, {bensin_a} per år</p>
                  <p id="out-bensin-diff">Elbilen kostar {diff} mindre per år i drivmedel.</p>
                </div>
                <p class="tool__note" id="out-bensin-tom" hidden>Fyll i liter per mil och bensinpris om du vill jämföra. Lämna båda tomma för att hoppa över.</p>
              </div>
            </div>
          </div>
        </section>
        <form id="laddkostnad" class="tool__panel tool__form" action="{TOOL_PATH}#ladd-resultat" method="get" autocomplete="off" novalidate>
          <h2 id="uppgifter-h">Uppgifter</h2>
          <p class="tool__hint" id="uppgifter-hint">Alla startvärden är exempel. Byt till dina egna.</p>
          <div class="tool__fields">
            <div class="tool__field">
              <label for="ladd-forbrukning">Förbrukning, kWh per 100 km</label>
              <input id="ladd-forbrukning" name="forbrukning" type="text" inputmode="decimal" enterkeyhint="done" autocapitalize="off" autocorrect="off" spellcheck="false" value="18" required aria-describedby="hint-forbrukning" data-hint="hint-forbrukning">
              <p class="tool__hint" id="hint-forbrukning">Exempel, inte ett testvärde. 18 är ett runt startvärde. Byt till din bil.</p>
            </div>
            <div class="tool__field">
              <label for="ladd-stracka">Körsträcka i mil</label>
              <input id="ladd-stracka" name="stracka" type="text" inputmode="decimal" enterkeyhint="done" autocapitalize="off" autocorrect="off" spellcheck="false" value="100" required aria-describedby="hint-stracka" data-hint="hint-stracka">
              <p class="tool__hint" id="hint-stracka">Exempel. 1 mil är 10 km. Siffran är per månad eller per år, beroende på valet under.</p>
            </div>
            <div class="tool__field">
              <label for="ladd-period">Körsträckan gäller</label>
              <select id="ladd-period" name="period" aria-describedby="hint-period" data-hint="hint-period">
                <option value="manad" selected>Per månad</option>
                <option value="ar">Per år</option>
              </select>
              <p class="tool__hint" id="hint-period">Byter du period räknas samma siffra om, den växlas inte automatiskt.</p>
            </div>
            <div class="tool__field tool__span">
              <label for="ladd-hemma">Andel hemmaladdning, procent</label>
              <input id="ladd-hemma" name="hemma" type="text" inputmode="decimal" enterkeyhint="done" autocapitalize="off" autocorrect="off" spellcheck="false" value="80" required aria-describedby="hint-hemma ladd-rest" data-hint="hint-hemma">
              <p class="tool__hint" id="hint-hemma">Exempel. Resten räknas som snabbladdning.</p>
              <output class="tool__rest" id="ladd-rest" for="ladd-hemma">20 procent räknas som snabbladdning.</output>
            </div>
            <div class="tool__field">
              <label for="ladd-elpris">Elpris hemma, kronor per kWh</label>
              <input id="ladd-elpris" name="elpris" type="text" inputmode="decimal" enterkeyhint="done" autocapitalize="off" autocorrect="off" spellcheck="false" value="2,34" required aria-describedby="hint-elpris" data-hint="hint-elpris">
              <p class="tool__hint" id="hint-elpris">Exempel från SCB, inte din faktura. Hushåll med minst 15{NB}000 kWh per år, första halvåret 2026: 234,26 öre per kWh inklusive elhandel, nät, energiskatt och moms, avrundat till 2,34. Byt till priset på din faktura.</p>
            </div>
            <div class="tool__field">
              <label for="ladd-snabb">Snabbladdning, kronor per kWh</label>
              <input id="ladd-snabb" name="snabb" type="text" inputmode="decimal" enterkeyhint="done" autocapitalize="off" autocorrect="off" spellcheck="false" value="6" required aria-describedby="hint-snabb" data-hint="hint-snabb">
              <p class="tool__hint" id="hint-snabb">Runt exempel, inte ett listpris. Byt till priset på stationen du använder.</p>
            </div>
            <div class="tool__field tool__span">
              <label for="ladd-forlust">Laddförluster hemma, procent</label>
              <input id="ladd-forlust" name="forlust" type="text" inputmode="decimal" enterkeyhint="done" autocapitalize="off" autocorrect="off" spellcheck="false" value="10" required aria-describedby="hint-forlust" data-hint="hint-forlust">
              <p class="tool__hint" id="hint-forlust">Runt exempel. Extra el från väggen hemma. 10 betyder att du köper 1,10 gånger det som hamnar i batteriet. Snabbladdningen räknas utan det påslaget.</p>
            </div>
          </div>
          <fieldset class="tool__set">
            <legend>Jämför med bensinbil, valfritt</legend>
            <div class="tool__fields">
              <div class="tool__field">
                <label for="ladd-bensin-l">Förbrukning, liter per mil</label>
                <input id="ladd-bensin-l" name="bensinl" type="text" inputmode="decimal" enterkeyhint="done" autocapitalize="off" autocorrect="off" spellcheck="false" value="0,7" aria-describedby="hint-bensin-l" data-hint="hint-bensin-l">
                <p class="tool__hint" id="hint-bensin-l">Valfritt exempel. Lämna tomt tillsammans med priset om du inte vill jämföra.</p>
              </div>
              <div class="tool__field">
                <label for="ladd-bensin-pris">Bensinpris, kronor per liter</label>
                <input id="ladd-bensin-pris" name="bensinpris" type="text" inputmode="decimal" enterkeyhint="done" autocapitalize="off" autocorrect="off" spellcheck="false" value="18" aria-describedby="hint-bensin-pris" data-hint="hint-bensin-pris">
                <p class="tool__hint" id="hint-bensin-pris">Valfritt exempel, inte ett uppmätt pumpris. Jämförelsen räknar bara drivmedel.</p>
              </div>
            </div>
          </fieldset>
          <div class="tool__actions">
            <button class="tool__reset" id="ladd-reset" type="button" hidden>Återställ exempel</button>
          </div>
        </form>
      </div>
    </div>
    <div class="tool__read">
      <div class="prose">
        <h2>Så räknas det</h2>
        <p>En mil är 10 kilometer. Förbrukningen i kilowattimmar per mil ur batteriet är därför kWh per 100 km delat med 10.</p>
        <p>Hemma tillkommer laddförlust. Fältet är procent extra el som huset köper utöver det som hamnar i batteriet. 10 procent betyder att väggen levererar 1,10 gånger batteriets förbrukning. Snabbladdningens pris multipliceras med batteriets förbrukning, utan det påslaget. På en publik laddare betalar du oftast det laddaren debiterar, och den mängden är inte samma sak som förlusten i laddboxen hemma.</p>
        <p>Kostnad per mil = andel hemma × kostnad hemma per mil + andel snabbladdning × kostnad snabbt per mil. Månad och år är den kostnaden gånger körsträckan. Väljer du mil per månad blir året tolv gånger. Väljer du mil per år blir månaden en tolftedel. Summorna avrundas till hela kronor från milpriset innan det avrundas till ören.</p>
        <p>Bensinjämförelsen är liter per mil gånger bensinpriset. Den visas när båda fälten är ifyllda och räknar bara drivmedel, inte försäkring, service eller däck.</p>
        <h2>Räkneexempel med startvärdena</h2>
        <p>18 kWh per 100 km är 1,80 kWh per mil ur batteriet. Hemma, 10 procent förlust: 1,80 × 1,10 = 1,98 kWh från väggen. 1,98 × 2,34 kronor = 4,6332 kronor, som visas som 4,63 kronor per mil. Snabbladdning: 1,80 × 6 kronor = 10,80 kronor per mil.</p>
        <p>Med 80 procent hemma blir milpriset 5,86656 kronor, som visas som 5,87 kronor. 100 mil i månaden är 1{NB}200 mil på ett år. Det oavrundade milpriset gånger körsträckan, avrundat till hela kronor, är 587 kronor per månad och 7{NB}040 kronor per år. Av året är 4{NB}448 kronor hemmaladdning och 2{NB}592 kronor snabbladdning.</p>
        <p>Bensinexemplet är 0,7 liter per mil × 18 kronor = 12,60 kronor per mil, 15{NB}120 kronor per år. Skillnaden mot elbilen i exemplet är 8{NB}080 kronor per år. Byt siffrorna om exemplet inte liknar din bil.</p>
        <h2>Tips</h2>
        <p>Elpriset hemma ska vara det du betalar från väggen. SCB-siffran i fältet är ett genomsnitt där fasta nätavgifter är utslagna per kilowattimme. Priset för en extra laddad kilowattimme, det som styr laddkostnaden, kan vara lägre. Jämför elhandeln på <a href="https://elpriskollen.se/">Elpriskollen</a>. Där ingår inte nät och skatt.</p>
        <p>Publik laddning skiljer mellan operatör, effekt och om du betalar i operatörens app. Listpriser lästa 23 november 2026: OKQ8 tar 5,44 kronor per kWh på egna 50 kW-laddare och 5,69 kronor på 150 till 200 kW. Circle K tar 6,69 kronor per kWh på egna laddare på 300 till 400 kW. Startvärdet 6 kronor är ett runt exempel mellan de priserna, inte ett rikspris. En längre genomgång med fler operatörer, kontrollerad 17 november 2026, finns i guiden <a href="/artikel/laddkostnad-elbil-hemma-supercharger/">Vad kostar det att ladda elbilen hemma och längs vägen</a>.</p>
        <p>En personbil körde i genomsnitt 1{NB}243 mil under 2025, enligt Trafikanalys (publicerad 21 september 2026). Elbilar och laddhybrider körde ungefär 1{NB}700 mil. Startvärdet 100 mil i månaden är 1{NB}200 mil på ett år, ett runt exempel nära snittet för alla personbilar, inte en uppgift om din bil.</p>
        <p>Förbrukningen på vintern, på motorväg och med last är ofta högre än broschyrens siffra. Laddförluster i ett test av flera elbilar låg mellan några procent och uppåt 18 procent. Mer om det testet finns i <a href="/artikel/ecobest-laddforluster-volvo-ex60-tesla-model-y/">artikeln om laddförluster</a>. 10 procent i fältet är ett runt exempel.</p>
      </div>
      {{FAQ}}
      {{SOURCES}}
    </div>'''


def index_page(b):
    crumbs_html, crumbs_ld = b.breadcrumbs([("Start", "/"), ("Verktyg", INDEX_PATH)])
    url = b.DOMAIN + INDEX_PATH
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "@id": url, "name": f"Verktyg · {b.SITE}", "description": INDEX_DESC,
         "url": url, "inLanguage": "sv-SE", "isPartOf": {"@id": b.DOMAIN + "/#website"},
         "breadcrumb": {k: v for k, v in crumbs_ld.items() if k != "@context"},
         "mainEntity": {"@type": "ItemList", "numberOfItems": 1, "itemListElement": [
             {"@type": "ListItem", "position": 1, "url": b.DOMAIN + TOOL_PATH, "name": TOOL_NAME}]}}]}
    h = b.head(b.page_title("Verktyg"), INDEX_DESC, INDEX_PATH, image=b.DEFAULT_OG,
               extra=_css(b) + b.ld_script(ld))
    body = f'''
<main id="innehall" class="tool">
  <div class="wrap">
    <header class="tool__head">
      {crumbs_html}
      <h1 class="tool__title">Verktyg</h1>
      <p class="tool__dek">{b.esc(INDEX_DESC)}</p>
    </header>
    <ul class="tool-index">
      <li>
        <a class="tool-card" href="{TOOL_PATH}">
          <h2>{b.esc(TOOL_NAME)}</h2>
          <p>Kostnad per mil, månad och år. Hemma, snabbladdning och en valfri jämförelse med en bensinbil.</p>
        </a>
      </li>
    </ul>
  </div>
</main>
'''
    return b.page(h, body)


def tool_page(b):
    crumbs_html, crumbs_ld = b.breadcrumbs([("Start", "/"), ("Verktyg", INDEX_PATH), ("Laddkostnad", TOOL_PATH)])
    url = b.DOMAIN + TOOL_PATH
    pairs = faq_pairs()
    app = {"@type": "WebApplication", "@id": url + "#app", "name": TOOL_NAME, "url": url,
           "description": TOOL_DESC, "applicationCategory": "UtilitiesApplication",
           "operatingSystem": "Webbläsare",
           "browserRequirements": "JavaScript för att räkna om. Formeln förklaras på sidan utan JavaScript.",
           "inLanguage": "sv-SE", "isAccessibleForFree": True,
           "offers": {"@type": "Offer", "price": "0", "priceCurrency": "SEK"},
           "publisher": {"@id": b.ORG_ID}}
    webpage = {"@type": "WebPage", "@id": url + "#webpage", "url": url, "name": TOOL_NAME,
               "description": TOOL_DESC, "inLanguage": "sv-SE", "isPartOf": {"@id": b.DOMAIN + "/#website"},
               "primaryImageOfPage": {"@type": "ImageObject", "url": b.DOMAIN + OG["src"], "width": OG["w"], "height": OG["h"]},
               "breadcrumb": {k: v for k, v in crumbs_ld.items() if k != "@context"},
               "mainEntity": {"@id": url + "#app"}}
    graph = {"@context": "https://schema.org", "@graph": [webpage, app, b.organization_ld()]}
    extra = _css(b) + b.ld_script(graph) + b.ld_script(b.faq_ld(pairs)) + f'<script src="{b.asset("/js/laddkostnad.js")}" defer></script>\n'
    h = b.head(b.page_title(TOOL_NAME), TOOL_DESC, TOOL_PATH, og_title=TOOL_NAME, image=OG, extra=extra)
    inner = tool_inner().replace("{{FAQ}}", b.faq_section(pairs)).replace("{{SOURCES}}", _sources(b))
    body = f'''
<main id="innehall" class="tool">
  <div class="wrap">
    <header class="tool__head">
      {crumbs_html}
      <h1 class="tool__title">{b.esc(TOOL_NAME)}</h1>
      <p class="tool__dek">{b.esc(TOOL_DESC)}</p>
      <p class="tool__banner"><span class="tag">Exempel</span> Värdena i fälten är startvärden som du ska byta, inte priser som gäller dig.</p>
    </header>
{inner}
  </div>
</main>
'''
    return b.page(h, body)


def render(b):
    return (("verktyg/index.html", index_page(b)), ("verktyg/laddkostnad/index.html", tool_page(b)))
