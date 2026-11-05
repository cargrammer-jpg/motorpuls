-- Nyhetsbrevet: dubbel bekräftelse, avregistreringskod, gränser och utskickslogg. INTE körd. Körs först när ALX har
-- godkänt (se supabase/README.md). Modell: BuildShipper (0004, 0023, 0024).
--
-- Före: rutan på motorpuls.se gjorde INSERT direkt i public.newsletter_subscribers med den publika nyckeln (anon).
-- Efter: anon har ingen åtkomst alls. Anmälan går via edge-funktionen newsletter-subscribe (service role), som skickar
-- bekräftelsemejlet. Bara bekräftade adresser får nyhetsbrev. Avregistrering raderar raden.
--
-- Säker att köra flera gånger. Tabellen hade 0 rader 2026-10-31; ev. gamla rader blir 'pending' och får koder.

begin;

-- Tabellen finns redan i projektet (skapad för PR #15). Här för att migrationen ska fungera även på en tom databas.
create table if not exists public.newsletter_subscribers (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  created_at timestamptz not null default now(),
  source text,
  consent boolean not null
);

-- 64 hex-tecken (2 x 122 slumpbitar från gen_random_uuid, inbyggd från Postgres 13, inget tillägg behövs).
create or replace function public.newsletter_token() returns text
language sql volatile set search_path = pg_catalog as $$
  select replace(gen_random_uuid()::text, '-', '') || replace(gen_random_uuid()::text, '-', '')
$$;

alter table public.newsletter_subscribers
  add column if not exists status text not null default 'pending',
  add column if not exists consent_at timestamptz not null default now(),
  add column if not exists consent_text text,
  add column if not exists confirm_token text not null default public.newsletter_token(),
  add column if not exists unsubscribe_token text not null default public.newsletter_token(),
  add column if not exists confirm_sent_at timestamptz,
  add column if not exists confirmed_at timestamptz;

alter table public.newsletter_subscribers alter column consent set default true;

-- Gamla rader: anmälningstiden är när raden skapades.
update public.newsletter_subscribers set consent_at = created_at where consent_at > created_at;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'newsletter_subscribers_status_check') then
    alter table public.newsletter_subscribers add constraint newsletter_subscribers_status_check check (status in ('pending', 'confirmed'));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'newsletter_subscribers_confirmed_at_check') then
    alter table public.newsletter_subscribers add constraint newsletter_subscribers_confirmed_at_check
      check ((status = 'confirmed') = (confirmed_at is not null));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'newsletter_subscribers_confirm_token_key') then
    alter table public.newsletter_subscribers add constraint newsletter_subscribers_confirm_token_key unique (confirm_token);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'newsletter_subscribers_unsubscribe_token_key') then
    alter table public.newsletter_subscribers add constraint newsletter_subscribers_unsubscribe_token_key unique (unsubscribe_token);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'newsletter_subscribers_tokens_check') then
    alter table public.newsletter_subscribers add constraint newsletter_subscribers_tokens_check
      check (confirm_token ~ '^[0-9a-f]{64}$' and unsubscribe_token ~ '^[0-9a-f]{64}$' and confirm_token <> unsubscribe_token);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'newsletter_subscribers_consent_text_check') then
    alter table public.newsletter_subscribers add constraint newsletter_subscribers_consent_text_check
      check (consent_text is null or char_length(consent_text) <= 500);
  end if;
end $$;

create index if not exists newsletter_subscribers_pending_idx on public.newsletter_subscribers (consent_at) where status = 'pending';

comment on table public.newsletter_subscribers is
  'Nyhetsbrevet (motorpuls.se). Dubbel bekräftelse: pending tills länken i mejlet bekräftas. Avregistrering raderar raden. '
  'Bara edge-funktionerna newsletter-* (service role) läser och skriver. Ingen åtkomst för anon eller authenticated.';

-- Anon får inte längre skriva direkt i tabellen (förut: policyn "anon kan anmala sig" och INSERT på tre kolumner).
drop policy if exists "anon kan anmala sig" on public.newsletter_subscribers;
alter table public.newsletter_subscribers enable row level security;
revoke all on table public.newsletter_subscribers from public, anon, authenticated;
revoke all (email, source, consent) on table public.newsletter_subscribers from anon;

-- Gränser för anmälan (antal försök per IP och per adress). bucket är en SHA-256 med salt, aldrig IP eller adress i klartext.
create table if not exists public.newsletter_rate_hits (
  id bigint generated always as identity primary key,
  bucket text not null check (char_length(bucket) <= 100),
  hit_at timestamptz not null default now()
);
create index if not exists newsletter_rate_hits_bucket_idx on public.newsletter_rate_hits (bucket, hit_at);
alter table public.newsletter_rate_hits enable row level security;
revoke all on table public.newsletter_rate_hits from public, anon, authenticated;

-- Räknar ett försök och svarar true om det ryms inom p_max per p_window_seconds. Rensar träffar äldre än ett dygn.
create or replace function public.newsletter_rate_hit(p_bucket text, p_max integer, p_window_seconds integer)
returns boolean
language plpgsql volatile set search_path = public, pg_catalog as $$
declare n integer;
begin
  delete from public.newsletter_rate_hits where hit_at < now() - interval '1 day';
  insert into public.newsletter_rate_hits (bucket) values (p_bucket);
  select count(*) into n from public.newsletter_rate_hits
    where bucket = p_bucket and hit_at > now() - make_interval(secs => p_window_seconds);
  return n <= p_max;
end $$;
revoke all on function public.newsletter_rate_hit(text, integer, integer) from public, anon, authenticated;
revoke all on function public.newsletter_token() from public, anon, authenticated;

-- Utskickslogg: en rad per utskick. Nyckeln (datum) tas innan något skickas, så samma utskick går aldrig ut två gånger.
create table if not exists public.newsletter_sends (
  issue_key text primary key check (char_length(issue_key) between 1 and 40),
  status text not null default 'sending' check (status in ('sending', 'sent', 'failed')),
  article_urls text[] not null default '{}',
  recipient_count integer not null default 0 check (recipient_count >= 0),
  started_at timestamptz not null default now(),
  finished_at timestamptz
);
alter table public.newsletter_sends enable row level security;
revoke all on table public.newsletter_sends from public, anon, authenticated;

-- service_role (edge-funktionerna) behöver rättigheterna uttryckligen när de har tagits bort från public.
grant select, insert, update, delete on public.newsletter_subscribers, public.newsletter_rate_hits, public.newsletter_sends to service_role;
grant execute on function public.newsletter_rate_hit(text, integer, integer), public.newsletter_token() to service_role;

commit;

-- Återställning (bara om ALX vill tillbaka till direkt INSERT från rutan):
-- begin;
-- drop table if exists public.newsletter_sends, public.newsletter_rate_hits;
-- drop function if exists public.newsletter_rate_hit(text, integer, integer);
-- alter table public.newsletter_subscribers drop constraint if exists newsletter_subscribers_status_check,
--   drop constraint if exists newsletter_subscribers_confirmed_at_check, drop constraint if exists newsletter_subscribers_confirm_token_key,
--   drop constraint if exists newsletter_subscribers_unsubscribe_token_key, drop constraint if exists newsletter_subscribers_tokens_check,
--   drop constraint if exists newsletter_subscribers_consent_text_check;
-- drop index if exists public.newsletter_subscribers_pending_idx;
-- alter table public.newsletter_subscribers drop column if exists status, drop column if exists consent_at,
--   drop column if exists consent_text, drop column if exists confirm_token, drop column if exists unsubscribe_token,
--   drop column if exists confirm_sent_at, drop column if exists confirmed_at;
-- alter table public.newsletter_subscribers alter column consent drop default;
-- drop function if exists public.newsletter_token();
-- grant insert (email, source, consent) on table public.newsletter_subscribers to anon;
-- create policy "anon kan anmala sig" on public.newsletter_subscribers for insert to anon
--   with check (consent = true and char_length(email) < 255);
-- commit;
