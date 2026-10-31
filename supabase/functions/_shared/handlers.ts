// HTTP-hanterare för newsletter-subscribe, -confirm, -unsubscribe och -send. Beroenden (lagring, utskick, klocka,
// hämtning av feed) skickas in, så att testerna kan köra allt utan nätverk. index.ts i varje funktion kopplar in de riktiga.
import {
  clientIp, CONSENT_TEXT, isToken, issueKey, links, normalizeEmail, normalizeSource, parseFeed, PENDING_DAYS, pickArticles,
  planSubscription, renderConfirmEmail, renderIssue, safeEqual, sha256Hex, unsubscribeHeaders,
} from "./newsletter.ts";
import type { Mailer, Outbound } from "./mail.ts";
import type { Store } from "./store.ts";

export type Config = {
  site: string; // https://motorpuls.se
  functionsUrl: string; // https://<projekt>.supabase.co/functions/v1
  allowedOrigins: string[];
  hashSalt: string;
  sendSecret?: string;
  sendEnabled: boolean;
  feedUrl: string;
};

export type Deps = { store: Store; mailer: Mailer; config: Config; now?: () => Date; fetchFeed?: (url: string) => Promise<string> };

// Gränser som BuildShipper: 5 försök per timme och IP, 3 per timme och adress.
export const RATE = { ipPerHour: 5, emailPerHour: 3 };

function json(body: unknown, status = 200, extra: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...extra } });
}

function cors(origin: string | null, config: Config): Record<string, string> {
  if (!origin || !config.allowedOrigins.includes(origin)) return {};
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-methods": "POST, OPTIONS",
    "access-control-allow-headers": "content-type, apikey, authorization, x-client-info",
    "access-control-max-age": "86400",
    vary: "Origin",
  };
}

async function readJson(req: Request): Promise<Record<string, unknown>> {
  try {
    const body = await req.json();
    return body && typeof body === "object" ? body as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

/** POST {email, source, webbplats} från rutan på motorpuls.se. Svarar alltid likadant när adressen är giltig,
 *  så att ingen kan se vilka adresser som redan prenumererar. */
export function subscribeHandler(deps: Deps) {
  const { store, mailer, config } = deps;
  return async (req: Request): Promise<Response> => {
    const origin = req.headers.get("origin");
    const h = cors(origin, config);
    if (req.method === "OPTIONS") return new Response(null, { status: origin && h["access-control-allow-origin"] ? 204 : 403, headers: h });
    if (req.method !== "POST") return json({ error: "method" }, 405, h);
    if (!h["access-control-allow-origin"]) return json({ error: "origin" }, 403);
    const body = await readJson(req);
    if (typeof body.webbplats === "string" && body.webbplats.trim() !== "") return json({ ok: true }, 200, h); // honungsfälla
    const email = normalizeEmail(body.email);
    if (!email) return json({ error: "email" }, 400, h);
    const ipKey = await sha256Hex(`${config.hashSalt}|ip|${clientIp(req.headers)}`);
    const mailKey = await sha256Hex(`${config.hashSalt}|email|${email}`);
    try {
      if (!(await store.rateHit(`ip:${ipKey}`, RATE.ipPerHour, 3600))) return json({ error: "rate" }, 429, h);
      if (!(await store.rateHit(`email:${mailKey}`, RATE.emailPerHour, 3600))) return json({ error: "rate" }, 429, h);
      const current = await store.findByEmail(email);
      const plan = planSubscription(current);
      if (plan === "already") return json({ ok: true }, 200, h);
      const row = current ?? await store.insertPending({ email, source: normalizeSource(body.source), consent_text: CONSENT_TEXT });
      if (row.status !== "pending") return json({ ok: true }, 200, h);
      const l = links(config.site, config.functionsUrl, row.confirm_token, row.unsubscribe_token);
      const mail = renderConfirmEmail(l);
      await mailer.send([{ to: email, ...mail, headers: unsubscribeHeaders(l.oneClickUrl) }]);
      await store.markConfirmSent(row.id);
      return json({ ok: true }, 200, h);
    } catch (e) {
      console.error(`[nyhetsbrev] anmälan misslyckades: ${(e as Error).message}`);
      return json({ error: "server" }, 502, h);
    }
  };
}

/** POST {token} från sidan /prenumeration/bekrafta/. GET ändrar aldrig något (länkskannrar i mejl öppnar med GET). */
export function confirmHandler(deps: Deps) {
  const { store, config } = deps;
  return async (req: Request): Promise<Response> => {
    const origin = req.headers.get("origin");
    const h = cors(origin, config);
    if (req.method === "OPTIONS") return new Response(null, { status: origin && h["access-control-allow-origin"] ? 204 : 403, headers: h });
    if (req.method !== "POST") return json({ error: "method" }, 405, h);
    if (!h["access-control-allow-origin"]) return json({ error: "origin" }, 403);
    const { token } = await readJson(req);
    if (!isToken(token)) return json({ status: "missing" }, 404, h);
    try {
      const status = await store.confirm(token);
      return json({ status }, status === "missing" ? 404 : 200, h);
    } catch (e) {
      console.error(`[nyhetsbrev] bekräftelse misslyckades: ${(e as Error).message}`);
      return json({ error: "server" }, 502, h);
    }
  };
}

/** Avregistrering. Två vägar:
 *  1. One-click (RFC 8058): mejlprogrammet POSTar "List-Unsubscribe=One-Click" till ?token=..., utan Origin.
 *  2. Sidan /prenumeration/avsluta/ på motorpuls.se POSTar {token} med Origin motorpuls.se.
 *  GET ändrar inget: den skickas vidare till sidan med knappen. Raden raderas helt (inget sparas efteråt). */
export function unsubscribeHandler(deps: Deps) {
  const { store, config } = deps;
  return async (req: Request): Promise<Response> => {
    const origin = req.headers.get("origin");
    const h = cors(origin, config);
    const url = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { status: origin && h["access-control-allow-origin"] ? 204 : 403, headers: h });
    if (req.method === "GET") {
      const t = url.searchParams.get("token");
      const to = `${config.site}/prenumeration/avsluta/${isToken(t) ? `?token=${t}` : ""}`;
      return new Response(null, { status: 303, headers: { location: to, "cache-control": "no-store" } });
    }
    if (req.method !== "POST") return json({ error: "method" }, 405, h);
    if (origin && !h["access-control-allow-origin"]) return json({ error: "origin" }, 403);
    let token: unknown = url.searchParams.get("token");
    if (!isToken(token) && (req.headers.get("content-type") ?? "").includes("application/json")) token = (await readJson(req)).token;
    if (!isToken(token)) return json({ status: "missing" }, 400, h);
    try {
      const removed = await store.unsubscribe(token);
      return json({ status: removed ? "unsubscribed" : "missing" }, 200, h);
    } catch (e) {
      console.error(`[nyhetsbrev] avregistrering misslyckades: ${(e as Error).message}`);
      return json({ error: "server" }, 502, h);
    }
  };
}

/** Utskick av nyhetsbrevet. POST med x-newsletter-secret. Body (JSON):
 *   {"mode": "dry-run"}                standard: räknar bara, inga mejl, inget raderas
 *   {"mode": "test", "test_to": "..."} ett provmejl till en adress (avregistreringslänken pekar inte på någon rad)
 *   {"mode": "send"}                   riktigt utskick, bara när NEWSLETTER_SEND_ENABLED=true
 *   valfritt "since" (ISO-tid): artiklar efter den tiden. Annars efter förra utskicket, eller senaste dygnet.
 *   valfritt "issue_key": standard är dagens datum i Stockholm, så samma dag skickas aldrig två gånger. */
export function sendHandler(deps: Deps) {
  const { store, mailer, config } = deps;
  const now = deps.now ?? (() => new Date());
  const fetchFeed = deps.fetchFeed ?? (async (u: string) => {
    const r = await fetch(u, { headers: { "user-agent": "motorpuls-nyhetsbrev" } });
    if (!r.ok) throw new Error(`feed ${r.status}`);
    return await r.text();
  });
  return async (req: Request): Promise<Response> => {
    if (req.method !== "POST") return json({ error: "method" }, 405);
    if (!config.sendSecret || !safeEqual(req.headers.get("x-newsletter-secret") ?? "", config.sendSecret)) return json({ error: "auth" }, 401);
    const body = await readJson(req);
    const mode = body.mode === "send" || body.mode === "test" ? body.mode : "dry-run";
    const at = now();
    try {
      const sinceArg = typeof body.since === "string" ? new Date(body.since) : null;
      const since = sinceArg && !Number.isNaN(sinceArg.getTime()) ? sinceArg : (await store.lastSentAt()) ?? new Date(at.getTime() - 86400_000);
      const articles = pickArticles(parseFeed(await fetchFeed(config.feedUrl), config.site), since);
      const key = typeof body.issue_key === "string" && /^[\w-]{1,40}$/.test(body.issue_key) ? body.issue_key : issueKey(at);
      const preview = renderIssue(articles, at, `${config.site}/prenumeration/avsluta/`);

      if (mode === "test") {
        const to = normalizeEmail(body.test_to);
        if (!to) return json({ error: "test_to" }, 400);
        if (articles.length === 0) return json({ mode, skipped: "inga nya artiklar", since: since.toISOString() });
        const r = await mailer.send([{ to, ...preview, headers: {} }]);
        return json({ mode, subject: preview.subject, articles: articles.length, logged: r.logged });
      }

      if (mode === "dry-run" || !config.sendEnabled) {
        return json({
          mode: "dry-run",
          forced: mode === "send" && !config.sendEnabled ? "NEWSLETTER_SEND_ENABLED är inte true" : undefined,
          issue_key: key, since: since.toISOString(), subject: preview.subject, articles: articles.length,
          recipients: await store.countConfirmed(), expired_pending: await store.countExpiredPending(PENDING_DAYS),
        });
      }

      const expired = await store.deleteExpiredPending(PENDING_DAYS);
      if (articles.length === 0) return json({ mode, skipped: "inga nya artiklar", expired_deleted: expired });
      if (!(await store.claimIssue(key, articles.map((a) => a.url)))) return json({ mode, skipped: "redan skickat", issue_key: key }, 409);
      const people = await store.confirmedRecipients();
      const messages: Outbound[] = people.map((p) => {
        const l = links(config.site, config.functionsUrl, "", p.unsubscribe_token);
        return { to: p.email, ...renderIssue(articles, at, l.unsubscribePage), headers: unsubscribeHeaders(l.oneClickUrl) };
      });
      try {
        const r = await mailer.send(messages, `motorpuls-${key}`);
        await store.finishIssue(key, "sent", r.sent);
        return json({ mode, issue_key: key, subject: preview.subject, articles: articles.length, sent: r.sent, logged: r.logged, expired_deleted: expired });
      } catch (e) {
        // Nyckeln står kvar som failed: ingen automatisk ny sändning (hellre ett missat än ett dubbelt utskick).
        await store.finishIssue(key, "failed", 0);
        throw e;
      }
    } catch (e) {
      console.error(`[nyhetsbrev] utskick misslyckades: ${(e as Error).message}`);
      return json({ error: "server", message: (e as Error).message }, 502);
    }
  };
}

/** Läser konfigurationen från miljön i edge-funktionen. */
export function configFromEnv(get: (k: string) => string | undefined): Config {
  const site = (get("NEWSLETTER_SITE_URL") || "https://motorpuls.se").replace(/\/$/, "");
  const supabaseUrl = (get("SUPABASE_URL") || "").replace(/\/$/, "");
  return {
    site,
    functionsUrl: `${supabaseUrl}/functions/v1`,
    allowedOrigins: (get("NEWSLETTER_ALLOWED_ORIGINS") || "https://motorpuls.se,https://www.motorpuls.se").split(",").map((s) => s.trim()).filter(Boolean),
    hashSalt: get("NEWSLETTER_HASH_SALT") || "motorpuls-nyhetsbrev",
    sendSecret: get("NEWSLETTER_SEND_SECRET") || undefined,
    sendEnabled: get("NEWSLETTER_SEND_ENABLED") === "true",
    feedUrl: get("NEWSLETTER_FEED_URL") || `${site}/feed.xml`,
  };
}
