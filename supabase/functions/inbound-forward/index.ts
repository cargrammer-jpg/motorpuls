// Vidarebefordrar mejl till hello@motorpuls.se. Resend-webhook (email.received) -> hämtar mejlet -> skickar kopian.
// POST /functions/v1/inbound-forward  (Svix-signerad av Resend). Driftsätts med --no-verify-jwt.
// Hemligheter (miljön först, annars Vault): RESEND_INBOUND_WEBHOOK_SECRET (webhookens signeringsnyckel),
// RESEND_INBOUND_API_KEY (får läsa mottagna mejl), RESEND_API_KEY (sändningsnyckeln för motorpuls.se).
// INBOUND_FORWARD_TO (valfri): mottagaren, standard moedare@mail.grokbot.com.
import { createClient } from "npm:@supabase/supabase-js@2";
import { liveGetter } from "../_shared/deps.ts";
import { FORWARD_TO_DEFAULT, type InboundDeps, inboundHandler } from "../_shared/inbound.ts";

async function live(): Promise<(req: Request) => Promise<Response>> {
  const url = Deno.env.get("SUPABASE_URL")!, key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
  const get = await liveGetter(url, key);
  const db = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } });
  const readKey = get("RESEND_INBOUND_API_KEY");
  const sendKey = get("RESEND_API_KEY");
  const api = async (path: string) => {
    if (!readKey) throw new Error("RESEND_INBOUND_API_KEY saknas");
    const r = await fetch(`https://api.resend.com${path}`, { headers: { Authorization: `Bearer ${readKey}` } });
    if (!r.ok) { await r.body?.cancel(); throw new Error(`Resend ${path.split("/").slice(0, 3).join("/")} svarade ${r.status}`); }
    return await r.json();
  };
  const deps: InboundDeps = {
    webhookSecret: get("RESEND_INBOUND_WEBHOOK_SECRET"),
    forwardTo: get("INBOUND_FORWARD_TO") || FORWARD_TO_DEFAULT,
    getEmail: (id) => api(`/emails/receiving/${id}`),
    listAttachments: async (id) => (await api(`/emails/receiving/${id}/attachments`)).data ?? [],
    async download(u) {
      const r = await fetch(u);
      if (!r.ok) { await r.body?.cancel(); throw new Error(`bilaga ${r.status}`); }
      return new Uint8Array(await r.arrayBuffer());
    },
    async send(mail, idem) {
      if (!sendKey) throw new Error("RESEND_API_KEY saknas");
      const r = await fetch("https://api.resend.com/emails", {
        method: "POST", headers: { Authorization: `Bearer ${sendKey}`, "Content-Type": "application/json", "Idempotency-Key": idem }, body: JSON.stringify(mail),
      });
      const out = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(`Resend send svarade ${r.status}`);
      return out.id as string;
    },
    async claim(id) {
      const { error } = await db.from("inbound_forwards").insert({ email_id: id });
      if (!error) return true;
      if (error.code !== "23505") throw new Error(`claim: ${error.message}`);
      // Ett misslyckat försök får tas om (Resend försöker igen); ett lyckat eller pågående aldrig.
      const { data, error: e2 } = await db.from("inbound_forwards").update({ status: "forwarding", finished_at: null })
        .eq("email_id", id).eq("status", "failed").select("email_id");
      if (e2) throw new Error(`claim: ${e2.message}`);
      return (data?.length ?? 0) > 0;
    },
    async finish(id, status, forwardedId) {
      const { error } = await db.from("inbound_forwards").update({ status, forwarded_id: forwardedId ?? null, finished_at: new Date().toISOString() }).eq("email_id", id);
      if (error) throw new Error(`finish: ${error.message}`);
    },
  };
  return inboundHandler(deps);
}

let ready: Promise<(req: Request) => Promise<Response>> | null = null;
Deno.serve(async (req) => {
  ready ??= live();
  try {
    return await (await ready)(req);
  } catch (e) {
    ready = null;
    console.error(`[inbound] start misslyckades: ${(e as Error).message}`);
    return new Response(JSON.stringify({ error: "unavailable" }), { status: 503, headers: { "content-type": "application/json" } });
  }
});
