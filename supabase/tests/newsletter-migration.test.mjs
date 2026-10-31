// Kör migrationen för nyhetsbrevet i PGlite ovanpå tabellen som den ser ut i projektet motorpuls i dag (2026-10-31),
// två gånger (ska gå att köra om), och kontrollerar rättigheter, koder, gränsfunktionen och utskicksloggen.
// Kör: cd supabase/tests && npm ci && npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { PGlite } from "@electric-sql/pglite";

const migration = readFileSync(new URL("../migrations/20261031130000_newsletter_double_opt_in.sql", import.meta.url), "utf8");
const vaultMigration = readFileSync(new URL("../migrations/20261031140000_newsletter_vault_secrets.sql", import.meta.url), "utf8");

// Supabase Vault finns inte i PGlite: en minimal ersättare med samma vy (vault.decrypted_secrets).
const VAULT_STUB = `
create schema if not exists vault;
create table if not exists vault.decrypted_secrets (name text primary key, decrypted_secret text);
revoke all on schema vault from public;
insert into vault.decrypted_secrets values ('newsletter_send_secret', 's1'), ('newsletter_hash_salt', 's2'), ('annan_hemlighet', 'nej')
  on conflict do nothing;
`;

// Läget i produktion före migrationen (avläst skrivskyddat ur katalogen 2026-10-31).
const LIVE_BEFORE = `
create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;
create table public.newsletter_subscribers (
  id uuid primary key default gen_random_uuid(),
  email text not null unique check (char_length(email) between 6 and 254 and email = lower(btrim(email))
    and email ~ '^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$'),
  created_at timestamptz not null default now(),
  source text check (source is null or char_length(source) <= 300),
  consent boolean not null
);
alter table public.newsletter_subscribers enable row level security;
grant insert (email, source, consent) on public.newsletter_subscribers to anon;
create policy "anon kan anmala sig" on public.newsletter_subscribers for insert to anon
  with check (consent = true and char_length(email) < 255);
grant usage on schema public to anon, authenticated, service_role;
`;

async function db() {
  const pg = new PGlite();
  await pg.exec(LIVE_BEFORE);
  return pg;
}

test("före migrationen kan anon anmäla direkt (som i dag)", async () => {
  const pg = await db();
  await pg.exec("set role anon; insert into public.newsletter_subscribers (email, source, consent) values ('fore@exempel.se', '/', true); reset role;");
  const { rows } = await pg.query("select count(*)::int n from public.newsletter_subscribers");
  assert.equal(rows[0].n, 1);
});

test("migrationen går att köra två gånger och ger gamla rader koder", async () => {
  const pg = await db();
  await pg.exec("insert into public.newsletter_subscribers (email, source, consent) values ('gammal@exempel.se', '/', true)");
  await pg.exec(migration);
  await pg.exec(migration);
  const { rows } = await pg.query("select status, confirm_token, unsubscribe_token, consent_at <= created_at ok, confirmed_at from public.newsletter_subscribers");
  assert.equal(rows.length, 1);
  assert.equal(rows[0].status, "pending");
  assert.match(rows[0].confirm_token, /^[0-9a-f]{64}$/);
  assert.match(rows[0].unsubscribe_token, /^[0-9a-f]{64}$/);
  assert.notEqual(rows[0].confirm_token, rows[0].unsubscribe_token);
  assert.equal(rows[0].ok, true);
  assert.equal(rows[0].confirmed_at, null);
});

test("efter migrationen: anon och authenticated kommer inte åt något", async () => {
  const pg = await db();
  await pg.exec(migration);
  for (const role of ["anon", "authenticated"]) {
    for (const sql of [
      "insert into public.newsletter_subscribers (email, source, consent) values ('ny@exempel.se', '/', true)",
      "select * from public.newsletter_subscribers",
      "select * from public.newsletter_sends",
      "select * from public.newsletter_rate_hits",
      "select public.newsletter_rate_hit('x', 5, 3600)",
    ]) {
      await assert.rejects(pg.exec(`set role ${role}; ${sql}`), /permission denied/, `${role}: ${sql}`);
      await pg.exec("reset role");
    }
  }
  const { rows } = await pg.query("select count(*)::int n from pg_policies where tablename = 'newsletter_subscribers'");
  assert.equal(rows[0].n, 0);
});

test("service_role: väntande rad får unika koder, bekräftelse kräver confirmed_at", async () => {
  const pg = await db();
  await pg.exec(migration);
  await pg.exec("set role service_role");
  await pg.exec("insert into public.newsletter_subscribers (email, source, consent_text) values ('a@exempel.se', '/artikel/x/', 'text'), ('b@exempel.se', null, 'text')");
  const { rows } = await pg.query("select count(distinct confirm_token)::int c, count(distinct unsubscribe_token)::int u from public.newsletter_subscribers");
  assert.deepEqual(rows[0], { c: 2, u: 2 });
  await assert.rejects(pg.exec("update public.newsletter_subscribers set status = 'confirmed' where email = 'a@exempel.se'"), /confirmed_at_check/);
  await pg.exec("update public.newsletter_subscribers set status = 'confirmed', confirmed_at = now() where email = 'a@exempel.se'");
  await assert.rejects(pg.exec("update public.newsletter_subscribers set status = 'unsubscribed' where email = 'b@exempel.se'"), /status_check/);
  await assert.rejects(pg.exec("insert into public.newsletter_subscribers (email) values ('a@exempel.se')"), /unique/);
  await pg.exec("delete from public.newsletter_subscribers where email = 'a@exempel.se'");
  await pg.exec("reset role");
});

test("gränsfunktionen: true upp till max, sedan false, per bucket", async () => {
  const pg = await db();
  await pg.exec(migration);
  await pg.exec("set role service_role");
  const hit = async (b) => (await pg.query("select public.newsletter_rate_hit($1, 3, 3600) ok", [b])).rows[0].ok;
  assert.deepEqual([await hit("ip:a"), await hit("ip:a"), await hit("ip:a"), await hit("ip:a"), await hit("ip:b")], [true, true, true, false, true]);
  await pg.exec("reset role");
  await pg.exec("update public.newsletter_rate_hits set hit_at = now() - interval '2 days'");
  await pg.exec("set role service_role");
  assert.equal(await hit("ip:a"), true); // gamla träffar rensas
  const { rows } = await pg.query("select count(*)::int n from public.newsletter_rate_hits");
  assert.equal(rows[0].n, 1);
  await pg.exec("reset role");
});

test("utskicksloggen: samma nyckel kan inte tas två gånger", async () => {
  const pg = await db();
  await pg.exec(migration);
  await pg.exec("set role service_role");
  await pg.exec("insert into public.newsletter_sends (issue_key, article_urls) values ('2026-10-31', '{https://motorpuls.se/artikel/x/}')");
  await assert.rejects(pg.exec("insert into public.newsletter_sends (issue_key) values ('2026-10-31')"), /duplicate key|unique/);
  await pg.exec("update public.newsletter_sends set status = 'sent', recipient_count = 2, finished_at = now() where issue_key = '2026-10-31'");
  await pg.exec("reset role");
});

test("vault: bara service_role läser, och bara nyhetsbrevets namn", async () => {
  const pg = await db();
  await pg.exec(migration);
  await pg.exec(VAULT_STUB);
  await pg.exec(vaultMigration);
  await pg.exec(vaultMigration);
  for (const role of ["anon", "authenticated"]) {
    for (const sql of ["select public.newsletter_vault_secrets(array['newsletter_send_secret'])", "select * from public.inbound_forwards"]) {
      await assert.rejects(pg.exec(`set role ${role}; ${sql}`), /permission denied/, `${role}: ${sql}`);
      await pg.exec("reset role");
    }
  }
  await pg.exec("set role service_role");
  const { rows } = await pg.query("select public.newsletter_vault_secrets(array['newsletter_send_secret', 'annan_hemlighet', 'newsletter_hash_salt']) s");
  assert.deepEqual(rows[0].s, { newsletter_send_secret: "s1", newsletter_hash_salt: "s2" });
  await pg.exec("insert into public.inbound_forwards (email_id) values ('e1')");
  await assert.rejects(pg.exec("insert into public.inbound_forwards (email_id) values ('e1')"), /duplicate key|unique/);
  await pg.exec("reset role");
});
