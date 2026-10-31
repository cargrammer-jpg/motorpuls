-- Web Push: prenumerationer från push-rutan på motorpuls.se. INTE körd. Körs först när ALX har godkänt (se supabase/README.md).
-- Samma mönster som nyhetsbrevet: RLS på, rollen anon får bara INSERT av de kolumner rutan skickar. Ingen SELECT, UPDATE
-- eller DELETE för anon eller authenticated. Bara utskicksfunktionen (service role, på servern) läser och rensar tabellen.

create table if not exists public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  endpoint text not null unique check (endpoint ~ '^https://' and char_length(endpoint) <= 1000),
  p256dh text not null check (p256dh ~ '^[A-Za-z0-9_-]+=*$' and char_length(p256dh) between 80 and 100),
  auth text not null check (auth ~ '^[A-Za-z0-9_-]+=*$' and char_length(auth) between 16 and 32),
  source text check (source is null or (source ~ '^/' and char_length(source) <= 300)),
  created_at timestamptz not null default now(),
  last_sent_at timestamptz,
  failures smallint not null default 0
);

comment on table public.push_subscriptions is 'Web Push-prenumerationer (motorpuls.se). Anon: bara insert. Läses bara av send-push med service role.';

alter table public.push_subscriptions enable row level security;

revoke all on table public.push_subscriptions from public, anon, authenticated;
grant insert (endpoint, p256dh, auth, source) on table public.push_subscriptions to anon;

drop policy if exists push_subscriptions_anon_insert on public.push_subscriptions;
create policy push_subscriptions_anon_insert on public.push_subscriptions
  for insert to anon
  with check (true);
