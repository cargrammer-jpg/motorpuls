// Riktiga beroenden för edge-funktionerna (Supabase med service role och Resend). Hemligheter finns aldrig i repot.
// SUPABASE_URL och SUPABASE_SERVICE_ROLE_KEY finns automatiskt i funktionen. Övriga hemligheter läses i första hand från
// miljön (`supabase secrets set`) och annars från Supabase Vault via public.newsletter_vault_secrets(), som bara
// service_role får köra (se migrationen). Vault-namnen står i VAULT_KEYS.
import { createClient } from "npm:@supabase/supabase-js@2";
import { configFromEnv, type Deps, headImage } from "./handlers.ts";
import { resendMailer } from "./mail.ts";
import { FROM_DEFAULT, REPLY_TO_DEFAULT } from "./newsletter.ts";
import { supabaseStore } from "./store.ts";

/** Miljövariabel och namnet på samma hemlighet i Supabase Vault. */
export const VAULT_KEYS: Record<string, string> = {
  RESEND_API_KEY: "newsletter_resend_api_key",
  NEWSLETTER_HASH_SALT: "newsletter_hash_salt",
  NEWSLETTER_SEND_SECRET: "newsletter_send_secret",
  RESEND_INBOUND_WEBHOOK_SECRET: "resend_inbound_webhook_secret",
  RESEND_INBOUND_API_KEY: "resend_inbound_api_key", // läsrätt till mottagna mejl (sändningsnyckeln räcker inte)
};

/** Hemligheterna som nyhetsbrevsfunktionerna får läsa. Nyckeln med full åtkomst (RESEND_INBOUND_API_KEY) och webhookens
 *  signeringsnyckel läses bara av inbound-forward. */
export const NEWSLETTER_KEYS = ["RESEND_API_KEY", "NEWSLETTER_HASH_SALT", "NEWSLETTER_SEND_SECRET"];
export const INBOUND_KEYS = ["RESEND_API_KEY", "RESEND_INBOUND_WEBHOOK_SECRET", "RESEND_INBOUND_API_KEY"];

/** Läser värden: miljön först, Vault för det som saknas. Bara namnen i names läses, och Vault anropas bara om något saknas. */
export async function liveGetter(url: string, key: string, names: string[]): Promise<(k: string) => string | undefined> {
  const env = (k: string) => Deno.env.get(k) || undefined;
  const allowed = new Set(names.filter((k) => VAULT_KEYS[k]));
  const missing = [...allowed].filter((k) => !env(k));
  let vault: Record<string, string> = {};
  if (missing.length > 0) {
    const db = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } });
    const { data, error } = await db.rpc("newsletter_vault_secrets", { p_names: missing.map((k) => VAULT_KEYS[k]) });
    if (error) throw new Error(`vault: ${error.message}`);
    vault = (data ?? {}) as Record<string, string>;
  }
  return (k: string) => {
    if (VAULT_KEYS[k] && !allowed.has(k)) return undefined; // hemligheter utanför names läses aldrig, inte ens från miljön
    return env(k) ?? (VAULT_KEYS[k] ? vault[VAULT_KEYS[k]] || undefined : undefined);
  };
}

export async function liveDeps(): Promise<Deps> {
  const url = Deno.env.get("SUPABASE_URL");
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !key) throw new Error("saknar SUPABASE_URL eller SUPABASE_SERVICE_ROLE_KEY");
  const get = await liveGetter(url, key, NEWSLETTER_KEYS);
  return {
    store: supabaseStore(url, key),
    mailer: resendMailer({ apiKey: get("RESEND_API_KEY"), from: get("NEWSLETTER_FROM") || FROM_DEFAULT, replyTo: get("NEWSLETTER_REPLY_TO") || REPLY_TO_DEFAULT }),
    config: configFromEnv(get),
    imageExists: headImage,
  };
}

/** Kopplar en hanterare till de riktiga beroendena. Beroendena hämtas vid första anropet och sparas; misslyckas det
 *  svarar funktionen 503 och försöker igen nästa gång (inga hemligheter i felet). */
export function serveLive(make: (deps: Deps) => (req: Request) => Promise<Response>): (req: Request) => Promise<Response> {
  let ready: Promise<(req: Request) => Promise<Response>> | null = null;
  return async (req) => {
    ready ??= liveDeps().then(make);
    try {
      return await (await ready)(req);
    } catch (e) {
      ready = null;
      console.error(`[nyhetsbrev] start misslyckades: ${(e as Error).message}`);
      return new Response(JSON.stringify({ error: "unavailable" }), { status: 503, headers: { "content-type": "application/json", "cache-control": "no-store" } });
    }
  };
}
