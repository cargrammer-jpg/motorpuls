-- Hemligheter för edge-funktionerna newsletter-* och inbound-forward via Supabase Vault (inga värden här).
-- Funktionerna läser i första hand miljövariabler (`supabase secrets set`). Saknas de läses samma hemligheter ur Vault
-- med den här funktionen, som bara service_role får köra. Värdena läggs in separat med vault.create_secret och finns
-- aldrig i repot. Bara namnen nedan kan läsas, inga andra hemligheter i Vault.
--
-- Säker att köra flera gånger.

begin;

create or replace function public.newsletter_vault_secrets(p_names text[])
returns jsonb
language plpgsql stable security definer set search_path = pg_catalog as $$
begin
  return coalesce((
    select jsonb_object_agg(s.name, s.decrypted_secret)
    from vault.decrypted_secrets s
    where s.name = any (p_names)
      and s.name in ('newsletter_resend_api_key', 'newsletter_hash_salt', 'newsletter_send_secret', 'resend_inbound_webhook_secret', 'resend_inbound_api_key')
  ), '{}'::jsonb);
end $$;

revoke all on function public.newsletter_vault_secrets(text[]) from public, anon, authenticated;
grant execute on function public.newsletter_vault_secrets(text[]) to service_role;

comment on function public.newsletter_vault_secrets(text[]) is
  'Läser nyhetsbrevets hemligheter ur Vault åt edge-funktionerna. Bara service_role. Bara namnen i funktionen.';

-- Idempotens för inbound-forward: ett mottaget mejl (Resends email_id) vidarebefordras bara en gång.
create table if not exists public.inbound_forwards (
  email_id text primary key check (char_length(email_id) between 1 and 100),
  status text not null default 'forwarding' check (status in ('forwarding', 'forwarded', 'skipped', 'failed')),
  forwarded_id text,
  created_at timestamptz not null default now(),
  finished_at timestamptz
);
alter table public.inbound_forwards enable row level security;
revoke all on table public.inbound_forwards from public, anon, authenticated;
grant select, insert, update, delete on public.inbound_forwards to service_role;

commit;

-- Återställning:
-- drop function if exists public.newsletter_vault_secrets(text[]);
-- drop table if exists public.inbound_forwards;
