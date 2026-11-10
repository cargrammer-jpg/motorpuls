// Utskick via Resend (samma tjänst som BuildShipper). Utan RESEND_API_KEY loggas mejlen och inget skickas.
// Resends REST-API anropas direkt med fetch (inget SDK behövs i Deno). Batch: högst 100 mejl per anrop.
import { BATCH } from "./newsletter.ts";

export type Outbound = { to: string; subject: string; html: string; text: string; headers: Record<string, string> };

export interface Mailer {
  /** Skickar alla mejl. idempotencyKey (valfri) gör att samma omgång inte skickas två gånger hos Resend. */
  send(messages: Outbound[], idempotencyKey?: string): Promise<{ sent: number; logged: boolean; ids?: string[] }>;
}

export function resendMailer(opts: { apiKey?: string; from: string; replyTo?: string; fetchImpl?: typeof fetch }): Mailer {
  const doFetch = opts.fetchImpl ?? fetch;
  return {
    async send(messages, idempotencyKey) {
      if (messages.length === 0) return { sent: 0, logged: !opts.apiKey };
      if (!opts.apiKey) {
        for (const m of messages) console.info(`[nyhetsbrev] bara loggat (RESEND_API_KEY saknas) till=${m.to.replace(/^(.).*@/, "$1***@")} amne=${m.subject}`);
        return { sent: 0, logged: true };
      }
      let sent = 0;
      const ids: string[] = [];
      for (let i = 0; i < messages.length; i += BATCH) {
        const chunk = messages.slice(i, i + BATCH).map((m) => ({
          from: opts.from,
          to: [m.to],
          subject: m.subject,
          html: m.html,
          text: m.text,
          headers: m.headers,
          ...(opts.replyTo ? { reply_to: opts.replyTo } : {}),
        }));
        const headers: Record<string, string> = { Authorization: `Bearer ${opts.apiKey}`, "Content-Type": "application/json" };
        if (idempotencyKey) headers["Idempotency-Key"] = `${idempotencyKey}-${i / BATCH}`;
        const res = await doFetch("https://api.resend.com/emails/batch", { method: "POST", headers, body: JSON.stringify(chunk) });
        if (!res.ok) {
          await res.body?.cancel();
          throw new Error(`Resend svarade ${res.status} efter ${sent} mejl`);
        }
        const out = await res.json().catch(() => null) as { data?: { id?: string }[] } | null;
        for (const d of out?.data ?? []) if (d?.id) ids.push(d.id);
        sent += chunk.length;
      }
      return { sent, logged: false, ids };
    },
  };
}
