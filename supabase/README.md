# Supabase för Motorpuls

Den här katalogen publiceras inte (build.py kopierar bara den publika delen till `_site`). Inget här är kört eller driftsatt.

## Nyhetsbrevet (dubbel bekräftelse, utskick via Resend, inte inkopplat)

Samma upplägg och samma tjänst som BuildShipper: Resend skickar, Supabase lagrar, dubbel bekräftelse, separat kod för att
bekräfta och för att avsluta, one-click-avregistrering med `List-Unsubscribe` och `List-Unsubscribe-Post`.

### Vad som finns
- `migrations/20261031130000_newsletter_double_opt_in.sql`: bygger ut `public.newsletter_subscribers` med `status`
  (pending/confirmed), `confirm_token`, `unsubscribe_token` (64 hex vardera), `consent_at`, `consent_text`, `confirm_sent_at`,
  `confirmed_at`. Tar bort anons INSERT (rutan skriver inte längre direkt i tabellen). Nya tabeller `newsletter_rate_hits`
  (gränser, bara hashar) och `newsletter_sends` (en rad per utskick, stoppar dubbla utskick). Funktionen `newsletter_rate_hit`.
  Återställnings-SQL står sist i filen. Testas i `tests/` med PGlite mot tabellen som den ser ut i projektet i dag.
- `functions/newsletter-subscribe`: POST från rutan. Origin måste vara motorpuls.se, honungsfälla, högst 5 försök per timme och
  IP och 3 per timme och adress. Ny adress: väntande rad och bekräftelsemejl. Väntande adress: samma länk skickas igen.
  Bekräftad adress: inget mejl. Svaret är detsamma i alla fallen.
- `functions/newsletter-confirm`: POST `{token}` från `/prenumeration/bekrafta/`. GET ändrar inget.
- `functions/newsletter-unsubscribe`: one-click POST från mejlprogrammet (`?token=`, utan Origin) eller POST `{token}` från
  `/prenumeration/avsluta/`. Raden raderas helt. GET skickas vidare till sidan.
- `functions/newsletter-send`: utskick med artiklarna i `feed.xml` sedan förra utskicket (annars senaste dygnet), till alla
  bekräftade, 100 per anrop till Resend med Idempotency-Key. Skyddas av `x-newsletter-secret`. Standard är dry-run (räknar bara).
  `{"mode": "test", "test_to": "..."}` skickar ett provmejl. `{"mode": "send"}` skickar bara när `NEWSLETTER_SEND_ENABLED=true`.
  Nyckeln är dagens datum i Stockholm, så samma dag skickas aldrig två gånger. Raderar obekräftade adresser äldre än 30 dagar.
- `functions/_shared/`: logik, svenska mallar (HTML och text), Resend-klient (fetch, ingen SDK), lagring.
- `functions/tests/`: Deno-tester utan nätverk (`deno test supabase/functions/tests/`).

Sidorna `/prenumeration/bekrafta/`, `/prenumeration/avsluta/` och `/integritet/` byggs av build.py med `NEWSLETTER_BOX`.
De ligger på motorpuls.se eftersom Supabase inte visar HTML från sin egen domän.

### Hemligheter och inställningar (sätts med `supabase secrets set`, aldrig i repot)
| Namn | Krävs | Vad |
| --- | --- | --- |
| `RESEND_API_KEY` | för att skicka | Ny nyckel i BuildShippers Resend-konto, bara sändning och bara domänen motorpuls.se. Utan den loggas mejlen och inget skickas |
| `NEWSLETTER_FROM` | nej | Avsändare. Standard `Motorpuls <nyhetsbrev@motorpuls.se>` |
| `NEWSLETTER_REPLY_TO` | nej | Svarsadress (en brevlåda som läses). Visas aldrig på sajten |
| `NEWSLETTER_HASH_SALT` | ja | Lång slumpsträng för hasharna i `newsletter_rate_hits` |
| `NEWSLETTER_SEND_SECRET` | för utskick | Hemligheten i `x-newsletter-secret` |
| `NEWSLETTER_SEND_ENABLED` | nej | Exakt `true` för riktiga utskick. Annars dry-run |
| `NEWSLETTER_ALLOWED_ORIGINS` | nej | Standard `https://motorpuls.se,https://www.motorpuls.se` |
| `NEWSLETTER_SITE_URL`, `NEWSLETTER_FEED_URL` | nej | Standard `https://motorpuls.se` och `<sajt>/feed.xml` |

`SUPABASE_URL` och `SUPABASE_SERVICE_ROLE_KEY` finns automatiskt i funktionerna.

### Kvar innan nyhetsbrevet fungerar (kräver ALX:s OK)
1. Resend (BuildShippers konto): lägg till domänen `motorpuls.se` i regionen eu-west-1 (Irland) och skapa en sändningsnyckel
   som bara gäller den domänen.
2. DNS hos Strato: de fyra posterna Resend visar (DKIM `resend._domainkey`, `send` MX och TXT, `rsend` CNAME). motorpuls.se
   har DMARC `p=reject`, så inget får skickas innan domänen är grön i Resend.
3. Kör migrationen i projektet `motorpuls` (eu-north-1).
4. `supabase secrets set ...` enligt tabellen ovan.
5. Driftsätt: `supabase functions deploy newsletter-subscribe newsletter-confirm newsletter-unsubscribe newsletter-send --no-verify-jwt`.
6. Provmejl: `newsletter-send` med `{"mode": "test", "test_to": "<ALX>"}`. Kontrollera DKIM/SPF/DMARC och avregistrering.
7. Slå på `NEWSLETTER_BOX` i build.py (rutan, sidorna och integritetssidan blir publika).
8. Bestäm hur ofta utskicken går och vad som startar dem (t.ex. GitHub Actions schedule eller pg_cron som anropar
   `newsletter-send`), och sätt `NEWSLETTER_SEND_ENABLED=true`.

## Push-notiser (inte inkopplat)

- `migrations/20261031120000_push_subscriptions.sql`: tabellen `public.push_subscriptions`. RLS på, `anon` får bara INSERT av
  `endpoint`, `p256dh`, `auth` och `source`. Ingen läsning för anon.
- `functions/send-push/index.ts`: stub för utskick med `web-push`. Läser prenumerationer med service role och tar bort dem som
  push-tjänsten svarar 404/410 på.

### Kvar innan notiser fungerar (kräver ALX:s OK)
1. Kör migrationen i Supabase-projektet `motorpuls` (eu-north-1).
2. Skapa VAPID-nycklar (`npx web-push generate-vapid-keys`). Den privata nyckeln sparas bara som hemlighet:
   `supabase secrets set VAPID_PUBLIC_KEY=... VAPID_PRIVATE_KEY=... VAPID_SUBJECT=mailto:... PUSH_SEND_SECRET=...`
3. Driftsätt funktionen: `supabase functions deploy send-push --no-verify-jwt` (skyddas av `x-push-secret`).
4. Fyll i `PUSH_CONFIG` i build.py: `vapidPublicKey` (publik), `subscribeUrl`
   (`https://<projekt>.supabase.co/rest/v1/push_subscriptions`) och `anonKey` (publishable).
5. Utlösare vid publicering: ett steg i `.github/workflows/pages.yml` efter deploy som anropar funktionen för nya artiklar
   (jämför feed.xml före och efter). Hemligheten `PUSH_SEND_SECRET` läggs som GitHub Actions-secret.
6. Uppdatera integritetssidan (vad som sparas: push-adress och nycklar, sida, tidpunkt).
7. Slå på `PUSH_BOX` i build.py.
