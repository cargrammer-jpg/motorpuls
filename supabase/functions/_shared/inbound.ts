// Vidarebefordran av mejl till hello@motorpuls.se (Resend tar emot, MX pekar på Resend). Resend skickar en webhook
// (email.received) med bara metadata; funktionen verifierar Svix-signaturen, hämtar hela mejlet och bilagorna från
// Resends API och skickar en kopia till FORWARD_TO från hello@motorpuls.se med Reply-To satt till avsändaren.
// Skydd: bara mejl till hello@motorpuls.se, inga mejl från motorpuls.se själv (slingor), varje email_id bara en gång.
import { esc, safeEqual } from "./newsletter.ts";

export const INBOX = "hello@motorpuls.se";
export const FORWARD_FROM = "Motorpuls <hello@motorpuls.se>";
export const FORWARD_TO_DEFAULT = "moedare@mail.grokbot.com";
export const OWN_DOMAIN = "motorpuls.se";
const TOLERANCE_S = 300;
const MAX_ATTACH_BYTES = 30 * 1024 * 1024; // Resend tar högst 40 MB per mejl inklusive kodning

/** Svix (Resends webhooks): HMAC-SHA256 över "id.timestamp.body" med nyckeln efter "whsec_" (base64). */
export async function verifySvix(secret: string, h: Headers, body: string, nowS = Math.floor(Date.now() / 1000)): Promise<boolean> {
  const id = h.get("svix-id"), ts = h.get("svix-timestamp"), sig = h.get("svix-signature");
  if (!id || !ts || !sig || !/^\d+$/.test(ts) || Math.abs(nowS - Number(ts)) > TOLERANCE_S) return false;
  const raw = Uint8Array.from(atob(secret.replace(/^whsec_/, "")), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey("raw", raw, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${id}.${ts}.${body}`)));
  const expected = btoa(String.fromCharCode(...mac));
  return sig.split(" ").some((part) => {
    const [v, s] = part.split(",");
    return v === "v1" && typeof s === "string" && safeEqual(s, expected);
  });
}

export const bareAddress = (s: string) => (s.match(/<([^>]+)>/)?.[1] ?? s).trim().toLowerCase();
const domainOf = (s: string) => bareAddress(s).split("@")[1] ?? "";

export type Received = {
  id: string; from: string; to: string[]; cc?: string[]; subject?: string; created_at?: string; html?: string | null; text?: string | null;
  headers?: Record<string, string>; reply_to?: string[] | null; message_id?: string;
};
export type AttachmentMeta = { id: string; filename?: string; content_type?: string; size?: number; download_url?: string; content_id?: string; content_disposition?: string };
export type OutAttachment = { filename: string; content: string; content_type?: string; content_id?: string };
export type ForwardMail = { from: string; to: string[]; reply_to: string; subject: string; html: string; text: string; attachments: OutAttachment[]; headers: Record<string, string> };

export interface InboundDeps {
  webhookSecret?: string;
  forwardTo: string;
  getEmail(id: string): Promise<Received>;
  listAttachments(id: string): Promise<AttachmentMeta[]>;
  download(url: string): Promise<Uint8Array>;
  send(mail: ForwardMail, idempotencyKey: string): Promise<string>;
  /** Tar email_id. false om det redan är taget (vidarebefordrat eller pågår). */
  claim(id: string): Promise<boolean>;
  finish(id: string, status: "forwarded" | "skipped" | "failed", forwardedId?: string): Promise<void>;
  now?: () => number;
}

const b64 = (bytes: Uint8Array) => {
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
};

/** Bygger kopian: ursprunglig Från, Till, Datum och Ämne överst, sedan originalets html och text. */
export function buildForward(e: Received, forwardTo: string, attachments: OutAttachment[], skipped: string[]): ForwardMail {
  const subject = `Fwd: ${e.subject?.trim() || "(inget ämne)"}`;
  const date = e.created_at ? new Date(e.created_at).toLocaleString("sv-SE", { timeZone: "Europe/Stockholm" }) : "";
  const rows: [string, string][] = [["Från", e.from], ["Till", e.to.join(", ")], ...(e.cc?.length ? [["Kopia", e.cc.join(", ")] as [string, string]] : []), ["Datum", date], ["Ämne", e.subject ?? ""]];
  const note = skipped.length ? `Bilagor som inte kom med (för stora eller gick inte att hämta): ${skipped.join(", ")}. De finns kvar i Resend under Emails, Receiving.` : "";
  const headHtml = `<div style="font-family:Arial,sans-serif;font-size:13px;line-height:19px;color:#333;background:#f4f4f4;border-left:3px solid #FF5B1F;padding:10px 12px;margin:0 0 16px;">
<strong>Vidarebefordrat från ${INBOX}</strong><br>${rows.map(([k, v]) => `${k}: ${esc(v)}`).join("<br>")}${note ? `<br><em>${esc(note)}</em>` : ""}</div>`;
  const original = e.html ?? (e.text ? `<pre style="white-space:pre-wrap;font-family:inherit;">${esc(e.text)}</pre>` : "");
  const text = [`Vidarebefordrat från ${INBOX}`, ...rows.map(([k, v]) => `${k}: ${v}`), ...(note ? [note] : []), "", "", e.text ?? "(bara html)"].join("\n");
  const replyTo = e.reply_to?.[0] ? bareAddress(e.reply_to[0]) : bareAddress(e.from);
  return { from: FORWARD_FROM, to: [forwardTo], reply_to: replyTo, subject, html: headHtml + original, text, attachments, headers: { "X-Motorpuls-Forwarded-For": e.id } };
}

const json = (b: unknown, status = 200) => new Response(JSON.stringify(b), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

export function inboundHandler(d: InboundDeps) {
  return async (req: Request): Promise<Response> => {
    if (req.method !== "POST") return json({ error: "method" }, 405);
    const body = await req.text();
    if (!d.webhookSecret) return json({ error: "not configured" }, 503);
    if (!(await verifySvix(d.webhookSecret, req.headers, body, Math.floor((d.now?.() ?? Date.now()) / 1000)))) return json({ error: "signature" }, 401);
    let event: { type?: string; data?: { email_id?: string; from?: string; to?: string[]; received_for?: string[] } };
    try { event = JSON.parse(body); } catch { return json({ error: "json" }, 400); }
    if (event.type !== "email.received" && event.type !== "inbox.email.received") return json({ ignored: "type" });
    const id = event.data?.email_id;
    if (!id || !/^[\w-]{1,100}$/.test(id)) return json({ error: "email_id" }, 400);
    const rcpts = [...(event.data?.to ?? []), ...(event.data?.received_for ?? [])].map(bareAddress);
    if (!rcpts.includes(INBOX)) return json({ ignored: "recipient" });
    if (!(await d.claim(id))) return json({ ignored: "duplicate" });
    try {
      const e = await d.getEmail(id);
      const sender = bareAddress(e.from ?? event.data?.from ?? "");
      // Slingskydd: kopior och svar från vår egen domän skickas inte vidare, utom det uttryckliga provet från
      // nyhetsbrev@ (adressen tar aldrig emot svar själv och har inget som vidarebefordrar dit).
      if ((domainOf(sender) === OWN_DOMAIN && sender !== "nyhetsbrev@motorpuls.se") || e.headers?.["x-motorpuls-forwarded-for"] || e.headers?.["X-Motorpuls-Forwarded-For"]) {
        await d.finish(id, "skipped");
        return json({ ignored: "loop" });
      }
      const metas = await d.listAttachments(id);
      const atts: OutAttachment[] = [];
      const skipped: string[] = [];
      let total = 0;
      for (const m of metas) {
        const name = m.filename || "bilaga";
        try {
          if (!m.download_url || (m.size ?? 0) + total > MAX_ATTACH_BYTES) throw new Error("size");
          const bytes = await d.download(m.download_url);
          total += bytes.length;
          if (total > MAX_ATTACH_BYTES) throw new Error("size");
          atts.push({ filename: name, content: b64(bytes), ...(m.content_type ? { content_type: m.content_type } : {}), ...(m.content_id ? { content_id: m.content_id } : {}) });
        } catch {
          skipped.push(name);
        }
      }
      const sentId = await d.send(buildForward(e, d.forwardTo, atts, skipped), `inbound-${id}`);
      await d.finish(id, "forwarded", sentId);
      return json({ forwarded: sentId, attachments: atts.length, skipped: skipped.length });
    } catch (err) {
      await d.finish(id, "failed").catch(() => {});
      console.error(`[inbound] vidarebefordran misslyckades: ${(err as Error).message}`);
      return json({ error: "server" }, 502);
    }
  };
}
