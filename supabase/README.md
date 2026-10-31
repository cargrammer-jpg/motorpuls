# Supabase för Motorpuls (push-notiser, inte inkopplat)

Den här katalogen publiceras inte (build.py kopierar bara den publika delen till `_site`). Inget här är kört eller driftsatt.

## Vad som finns
- `migrations/20261031120000_push_subscriptions.sql`: tabellen `public.push_subscriptions`. RLS på, `anon` får bara INSERT av
  `endpoint`, `p256dh`, `auth` och `source`. Ingen läsning för anon. Samma mönster som nyhetsbrevets tabell.
- `functions/send-push/index.ts`: stub för utskick med `web-push`. Läser prenumerationer med service role och tar bort dem som
  push-tjänsten svarar 404/410 på.

## Kvar innan notiser fungerar (kräver ALX:s OK)
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
