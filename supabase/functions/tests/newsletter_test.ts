// Enhetstester för nyhetsbrevets edge-funktioner. Inga nätverksanrop: lagring, Resend och feed är falska.
// Kör: deno test supabase/functions/tests/
import { assert, assertEquals, assertMatch, assertNotEquals } from "jsr:@std/assert@1";
import { confirmHandler, type Config, sendHandler, subscribeHandler, unsubscribeHandler } from "../_shared/handlers.ts";
import { type Mailer, type Outbound, resendMailer } from "../_shared/mail.ts";
import {
  CONSENT_TEXT, isToken, issueKey, normalizeEmail, normalizeSource, parseFeed, pickArticles, planSubscription,
  renderConfirmEmail, renderIssue, safeEqual, svDate,
} from "../_shared/newsletter.ts";
import type { Store, Subscriber } from "../_shared/store.ts";

const SITE = "https://motorpuls.se";
const FN = "https://yhxnrcykinmuoqbgboda.supabase.co/functions/v1";
const config: Config = { site: SITE, functionsUrl: FN, allowedOrigins: [SITE, "https://www.motorpuls.se"], hashSalt: "test", sendSecret: "hemligt", sendEnabled: true, feedUrl: `${SITE}/feed.xml` };
const tok = () => [...crypto.getRandomValues(new Uint8Array(32))].map((b) => b.toString(16).padStart(2, "0")).join("");

type Row = Subscriber & { source: string | null; consent_text: string; consent_at: Date; confirm_sent: number };

function fakeStore() {
  const rows: Row[] = [];
  const hits = new Map<string, number>();
  const sends = new Map<string, { status: string; recipients: number; at: Date }>();
  const store: Store = {
    findByEmail: (email) => Promise.resolve(rows.find((r) => r.email === email) ?? null),
    insertPending(row) {
      const r: Row = { id: crypto.randomUUID(), status: "pending", confirm_token: tok(), unsubscribe_token: tok(), consent_at: new Date(), confirm_sent: 0, ...row };
      rows.push(r);
      return Promise.resolve(r);
    },
    markConfirmSent(id) { rows.find((r) => r.id === id)!.confirm_sent++; return Promise.resolve(); },
    rateHit(bucket, max) { const n = (hits.get(bucket) ?? 0) + 1; hits.set(bucket, n); return Promise.resolve(n <= max); },
    confirm(token) {
      const r = rows.find((x) => x.confirm_token === token);
      if (!r) return Promise.resolve("missing");
      if (r.status === "confirmed") return Promise.resolve("already");
      r.status = "confirmed";
      return Promise.resolve("confirmed");
    },
    unsubscribe(token) { const i = rows.findIndex((r) => r.unsubscribe_token === token); if (i >= 0) rows.splice(i, 1); return Promise.resolve(i >= 0); },
    countExpiredPending: (days) => Promise.resolve(rows.filter((r) => r.status === "pending" && r.consent_at.getTime() < Date.now() - days * 864e5).length),
    deleteExpiredPending(days) {
      const old = rows.filter((r) => r.status === "pending" && r.consent_at.getTime() < Date.now() - days * 864e5);
      for (const o of old) rows.splice(rows.indexOf(o), 1);
      return Promise.resolve(old.length);
    },
    countConfirmed: () => Promise.resolve(rows.filter((r) => r.status === "confirmed").length),
    confirmedRecipients: () => Promise.resolve(rows.filter((r) => r.status === "confirmed").map((r) => ({ email: r.email, unsubscribe_token: r.unsubscribe_token }))),
    lastSentAt: () => Promise.resolve([...sends.values()].filter((s) => s.status === "sent").map((s) => s.at).sort((a, b) => b.getTime() - a.getTime())[0] ?? null),
    claimIssue(key) { if (sends.has(key)) return Promise.resolve(false); sends.set(key, { status: "sending", recipients: 0, at: new Date() }); return Promise.resolve(true); },
    finishIssue(key, status, recipients) { Object.assign(sends.get(key)!, { status, recipients }); return Promise.resolve(); },
  };
  return { store, rows, sends };
}

function fakeMailer(fail = false) {
  const outbox: Outbound[] = [];
  const mailer: Mailer = { send(m) { if (fail) return Promise.reject(new Error("nere")); outbox.push(...m); return Promise.resolve({ sent: m.length, logged: false }); } };
  return { mailer, outbox };
}

const post = (url: string, body: unknown, headers: Record<string, string> = { origin: SITE, "content-type": "application/json", "x-forwarded-for": "203.0.113.7" }) =>
  new Request(url, { method: "POST", headers, body: typeof body === "string" ? body : JSON.stringify(body) });

const FEED = `<?xml version="1.0"?><rss><channel>
<item><title>Ny elbil &amp; laddning</title><link>${SITE}/artikel/ny-elbil/</link><pubDate>Sat, 31 Oct 2026 08:00:00 +0100</pubDate><category>Elbil</category><description>Kort om bilen.</description></item>
<item><title>Äldre nyhet</title><link>${SITE}/artikel/aldre/</link><pubDate>Thu, 29 Oct 2026 08:00:00 +0100</pubDate><category>Sportbil</category><description>Gammal.</description></item>
<item><title>Extern</title><link>https://example.com/x</link><pubDate>Sat, 31 Oct 2026 09:00:00 +0100</pubDate><category>X</category><description>Ska bort.</description></item>
</channel></rss>`;

// ---------- ren logik ----------
Deno.test("e-post normaliseras och valideras", () => {
  assertEquals(normalizeEmail("  Namn@Exempel.SE "), "namn@exempel.se");
  assertEquals(normalizeEmail("inte-en-adress"), null);
  assertEquals(normalizeEmail("a@b.c"), null); // kortare än 6 tecken, samma regel som tabellen
  assertEquals(normalizeEmail(42), null);
});

Deno.test("källa är bara en sökväg på sajten", () => {
  assertEquals(normalizeSource("/artikel/bmw/"), "/artikel/bmw/");
  assertEquals(normalizeSource("https://evil.example/"), null);
  assertEquals(normalizeSource("//evil.example/"), null);
  assertEquals(normalizeSource("/<script>"), null);
});

Deno.test("plan: ny rad, skicka samma länk igen, eller redan bekräftad", () => {
  assertEquals(planSubscription(null), "insert");
  assertEquals(planSubscription({ status: "pending" }), "resend");
  assertEquals(planSubscription({ status: "confirmed" }), "already");
});

Deno.test("safeEqual och tokenform", () => {
  assert(safeEqual("abc", "abc"));
  assert(!safeEqual("abc", "abd"));
  assert(!safeEqual("abc", "abcd"));
  assert(isToken("a".repeat(64)));
  assert(!isToken("A".repeat(64)));
  assert(!isToken("a".repeat(63)));
});

Deno.test("datum och utskicksnyckel i Stockholmstid", () => {
  const d = new Date("2026-10-31T23:30:00Z"); // 1 november 00:30 i Stockholm (UTC+1)
  assertEquals(issueKey(d), "2026-11-01");
  assertEquals(svDate(d), "1 november 2026");
});

Deno.test("feed: bara sajtens artiklar, nyast först, efter since", () => {
  const all = parseFeed(FEED);
  assertEquals(all.length, 2);
  assertEquals(all[0].title, "Ny elbil & laddning");
  const picked = pickArticles(all, new Date("2026-10-30T00:00:00Z"));
  assertEquals(picked.map((a) => a.url), [`${SITE}/artikel/ny-elbil/`]);
});

const DASHES = /[\u2013\u2014]/;
Deno.test("mejlen är på svenska, utan tankstreck, med avregistrering", () => {
  const c = renderConfirmEmail({ confirmUrl: `${SITE}/prenumeration/bekrafta/?token=${"a".repeat(64)}`, unsubscribePage: `${SITE}/prenumeration/avsluta/?token=${"b".repeat(64)}` });
  const i = renderIssue(parseFeed(FEED), new Date("2026-10-31T10:00:00Z"), `${SITE}/prenumeration/avsluta/?token=x`);
  for (const m of [c, i]) {
    for (const part of [m.subject, m.html, m.text]) assert(!DASHES.test(part), `tankstreck i: ${part.slice(0, 80)}`);
    assert(m.html.includes('lang="sv"'));
    assert(m.text.includes("/prenumeration/avsluta/"));
  }
  assertEquals(c.subject, "Bekräfta din prenumeration på Motorpuls");
  assert(c.html.includes("Bekräfta prenumerationen"));
  assertEquals(i.subject, "Ny elbil & laddning (och 1 till)");
  assert(i.html.includes("Ny elbil &amp; laddning"));
  assert(!DASHES.test(CONSENT_TEXT));
});

Deno.test("mejlen visar ingen kontaktadress", () => {
  const c = renderConfirmEmail({ confirmUrl: "https://motorpuls.se/x", unsubscribePage: "https://motorpuls.se/y" });
  const i = renderIssue(parseFeed(FEED), new Date(), "https://motorpuls.se/y");
  for (const m of [c, i]) assert(!/[\w.+-]+@[\w-]+\.[\w.]+/.test(m.html + m.text), "e-postadress i mallen");
});

// ---------- anmälan ----------
Deno.test("anmälan: väntande rad, ett bekräftelsemejl med List-Unsubscribe och one-click", async () => {
  const { store, rows } = fakeStore();
  const { mailer, outbox } = fakeMailer();
  const res = await subscribeHandler({ store, mailer, config })(post(`${FN}/newsletter-subscribe`, { email: "Test@Exempel.se", source: "/artikel/x/" }));
  assertEquals(res.status, 200);
  assertEquals(res.headers.get("access-control-allow-origin"), SITE);
  assertEquals(rows.length, 1);
  assertEquals(rows[0].status, "pending");
  assertEquals(rows[0].source, "/artikel/x/");
  assertEquals(rows[0].consent_text, CONSENT_TEXT);
  assertEquals(outbox.length, 1);
  const m = outbox[0];
  assertEquals(m.to, "test@exempel.se");
  assert(m.html.includes(`/prenumeration/bekrafta/?token=${rows[0].confirm_token}`));
  assertEquals(m.headers["List-Unsubscribe"], `<${FN}/newsletter-unsubscribe?token=${rows[0].unsubscribe_token}>`);
  assertEquals(m.headers["List-Unsubscribe-Post"], "List-Unsubscribe=One-Click");
  assertNotEquals(rows[0].confirm_token, rows[0].unsubscribe_token);
});

Deno.test("anmälan igen: samma länk skickas, raden skrivs inte om; bekräftad adress får inget mejl", async () => {
  const { store, rows } = fakeStore();
  const { mailer, outbox } = fakeMailer();
  const h = subscribeHandler({ store, mailer, config });
  await h(post(`${FN}/newsletter-subscribe`, { email: "a@exempel.se" }));
  const token = rows[0].confirm_token;
  await h(post(`${FN}/newsletter-subscribe`, { email: "a@exempel.se" }, { origin: SITE, "x-forwarded-for": "198.51.100.1" }));
  assertEquals(rows.length, 1);
  assertEquals(rows[0].confirm_token, token);
  assertEquals(outbox.length, 2);
  assert(outbox[1].html.includes(token));
  rows[0].status = "confirmed";
  const res = await h(post(`${FN}/newsletter-subscribe`, { email: "a@exempel.se" }, { origin: SITE, "x-forwarded-for": "198.51.100.2" }));
  assertEquals(res.status, 200); // samma svar: ingen kan se att adressen redan prenumererar
  assertEquals(outbox.length, 2);
});

Deno.test("honungsfälla: svarar ok men sparar och skickar inget", async () => {
  const { store, rows } = fakeStore();
  const { mailer, outbox } = fakeMailer();
  const res = await subscribeHandler({ store, mailer, config })(post(`${FN}/newsletter-subscribe`, { email: "bot@exempel.se", webbplats: "http://spam" }));
  assertEquals(res.status, 200);
  assertEquals(rows.length + outbox.length, 0);
});

Deno.test("fel Origin, ogiltig adress och fel metod stoppas", async () => {
  const { store, rows } = fakeStore();
  const { mailer } = fakeMailer();
  const h = subscribeHandler({ store, mailer, config });
  assertEquals((await h(post(`${FN}/x`, { email: "a@exempel.se" }, { origin: "https://evil.example" }))).status, 403);
  assertEquals((await h(post(`${FN}/x`, { email: "a@exempel.se" }, {}))).status, 403);
  assertEquals((await h(post(`${FN}/x`, { email: "nej" }))).status, 400);
  assertEquals((await h(new Request(`${FN}/x`, { method: "GET" }))).status, 405);
  const pre = await h(new Request(`${FN}/x`, { method: "OPTIONS", headers: { origin: SITE } }));
  assertEquals(pre.status, 204);
  assertMatch(pre.headers.get("access-control-allow-methods") ?? "", /POST/);
  assertEquals(rows.length, 0);
});

Deno.test("gränser: 5 per timme och IP, 3 per timme och adress", async () => {
  const { store } = fakeStore();
  const { mailer } = fakeMailer();
  const h = subscribeHandler({ store, mailer, config });
  const codes = [];
  for (let i = 0; i < 6; i++) codes.push((await h(post(`${FN}/x`, { email: `p${i}@exempel.se` }))).status);
  assertEquals(codes, [200, 200, 200, 200, 200, 429]);
  const same = [];
  for (let i = 0; i < 4; i++) same.push((await h(post(`${FN}/x`, { email: "s@exempel.se" }, { origin: SITE, "x-forwarded-for": `10.0.0.${i}` }))).status);
  assertEquals(same, [200, 200, 200, 429]);
});

Deno.test("Resend nere: 502 och raden står kvar som väntande (nytt försök skickar samma länk)", async () => {
  const { store, rows } = fakeStore();
  const res = await subscribeHandler({ store, mailer: fakeMailer(true).mailer, config })(post(`${FN}/x`, { email: "a@exempel.se" }));
  assertEquals(res.status, 502);
  assertEquals(rows[0].status, "pending");
  assertEquals(rows[0].confirm_sent, 0);
});

// ---------- bekräftelse ----------
Deno.test("bekräftelse: bara POST med giltig kod, sedan 'already'", async () => {
  const { store, rows } = fakeStore();
  const { mailer } = fakeMailer();
  await subscribeHandler({ store, mailer, config })(post(`${FN}/x`, { email: "a@exempel.se" }));
  const h = confirmHandler({ store, mailer, config });
  assertEquals((await h(new Request(`${FN}/newsletter-confirm?token=${rows[0].confirm_token}`))).status, 405);
  assertEquals(rows[0].status, "pending"); // GET (länkskanner) ändrar inget
  const r1 = await h(post(`${FN}/newsletter-confirm`, { token: rows[0].confirm_token }));
  assertEquals(await r1.json(), { status: "confirmed" });
  const r2 = await h(post(`${FN}/newsletter-confirm`, { token: rows[0].confirm_token }));
  assertEquals(await r2.json(), { status: "already" });
  assertEquals((await h(post(`${FN}/newsletter-confirm`, { token: rows[0].unsubscribe_token }))).status, 404); // fel sorts kod
  assertEquals((await h(post(`${FN}/newsletter-confirm`, { token: "x" }))).status, 404);
  assertEquals((await h(post(`${FN}/newsletter-confirm`, { token: rows[0].confirm_token }, { origin: "https://evil.example" }))).status, 403);
});

// ---------- avregistrering ----------
Deno.test("one-click (RFC 8058) utan Origin raderar raden", async () => {
  const { store, rows } = fakeStore();
  const { mailer } = fakeMailer();
  await subscribeHandler({ store, mailer, config })(post(`${FN}/x`, { email: "a@exempel.se" }));
  const t = rows[0].unsubscribe_token;
  const res = await unsubscribeHandler({ store, mailer, config })(new Request(`${FN}/newsletter-unsubscribe?token=${t}`, {
    method: "POST", headers: { "content-type": "application/x-www-form-urlencoded" }, body: "List-Unsubscribe=One-Click",
  }));
  assertEquals(res.status, 200);
  assertEquals(await res.json(), { status: "unsubscribed" });
  assertEquals(rows.length, 0);
});

Deno.test("avregistrering från sidan (JSON) och GET som bara skickar vidare", async () => {
  const { store, rows } = fakeStore();
  const { mailer } = fakeMailer();
  await subscribeHandler({ store, mailer, config })(post(`${FN}/x`, { email: "a@exempel.se" }));
  const t = rows[0].unsubscribe_token;
  const h = unsubscribeHandler({ store, mailer, config });
  const g = await h(new Request(`${FN}/newsletter-unsubscribe?token=${t}`));
  assertEquals(g.status, 303);
  assertEquals(g.headers.get("location"), `${SITE}/prenumeration/avsluta/?token=${t}`);
  assertEquals(rows.length, 1);
  assertEquals(await (await h(post(`${FN}/newsletter-unsubscribe`, { token: t }))).json(), { status: "unsubscribed" });
  assertEquals(await (await h(post(`${FN}/newsletter-unsubscribe`, { token: t }))).json(), { status: "missing" });
  assertEquals((await h(post(`${FN}/newsletter-unsubscribe`, { token: t }, { origin: "https://evil.example", "content-type": "application/json" }))).status, 403);
  assertEquals((await h(post(`${FN}/newsletter-unsubscribe`, { token: "nej" }))).status, 400);
});

// ---------- utskick ----------
async function seeded() {
  const s = fakeStore();
  const { mailer } = fakeMailer();
  const sub = subscribeHandler({ store: s.store, mailer, config });
  for (const [i, e] of ["a@exempel.se", "b@exempel.se", "c@exempel.se"].entries()) {
    await sub(post(`${FN}/x`, { email: e }, { origin: SITE, "x-forwarded-for": `10.1.0.${i}` }));
  }
  s.rows[0].status = "confirmed";
  s.rows[1].status = "confirmed";
  s.rows[2].consent_at = new Date(Date.now() - 31 * 864e5); // obekräftad i mer än 30 dagar
  return s;
}
const sendReq = (body: unknown, secret = "hemligt") => new Request(`${FN}/newsletter-send`, { method: "POST", headers: { "x-newsletter-secret": secret }, body: JSON.stringify(body) });
const NOW = () => new Date("2026-10-31T10:00:00Z");
const feed = () => Promise.resolve(FEED);

Deno.test("utskick: fel hemlighet 401, dry-run ändrar inget", async () => {
  const { store, rows } = await seeded();
  const { mailer, outbox } = fakeMailer();
  const h = sendHandler({ store, mailer, config, now: NOW, fetchFeed: feed });
  assertEquals((await h(sendReq({ mode: "send" }, "fel"))).status, 401);
  const r = await (await h(sendReq({}))).json();
  assertEquals(r.mode, "dry-run");
  assertEquals(r.recipients, 2);
  assertEquals(r.expired_pending, 1);
  assertEquals(r.articles, 1);
  assertEquals(outbox.length, 0);
  assertEquals(rows.length, 3);
});

Deno.test("utskick utan NEWSLETTER_SEND_ENABLED blir dry-run", async () => {
  const { store } = await seeded();
  const { mailer, outbox } = fakeMailer();
  const r = await (await sendHandler({ store, mailer, config: { ...config, sendEnabled: false }, now: NOW, fetchFeed: feed })(sendReq({ mode: "send" }))).json();
  assertEquals(r.mode, "dry-run");
  assert(r.forced);
  assertEquals(outbox.length, 0);
});

Deno.test("utskick: bara bekräftade, egen avregistrering per mottagare, aldrig två gånger samma dag", async () => {
  const { store, rows, sends } = await seeded();
  const { mailer, outbox } = fakeMailer();
  const h = sendHandler({ store, mailer, config, now: NOW, fetchFeed: feed });
  const r = await (await h(sendReq({ mode: "send" }))).json();
  assertEquals(r.sent, 2);
  assertEquals(r.expired_deleted, 1);
  assertEquals(rows.length, 2);
  assertEquals(outbox.map((m) => m.to).sort(), ["a@exempel.se", "b@exempel.se"]);
  for (const m of outbox) {
    const row = rows.find((x) => x.email === m.to)!;
    assertEquals(m.headers["List-Unsubscribe"], `<${FN}/newsletter-unsubscribe?token=${row.unsubscribe_token}>`);
    assert(m.html.includes(`/prenumeration/avsluta/?token=${row.unsubscribe_token}`));
  }
  assertEquals(sends.get("2026-10-31")?.status, "sent");
  const again = await h(sendReq({ mode: "send", since: "2026-10-30T00:00:00Z" }));
  assertEquals(again.status, 409);
  assertEquals(outbox.length, 2);
});

Deno.test("utskick: inga nya artiklar ger inget mejl", async () => {
  const { store } = await seeded();
  const { mailer, outbox } = fakeMailer();
  const r = await (await sendHandler({ store, mailer, config, now: () => new Date("2026-11-05T10:00:00Z"), fetchFeed: feed })(sendReq({ mode: "send" }))).json();
  assertEquals(r.skipped, "inga nya artiklar");
  assertEquals(outbox.length, 0);
});

Deno.test("utskick: Resend nere markerar failed och skickar inte om automatiskt", async () => {
  const { store, sends } = await seeded();
  const h = sendHandler({ store, mailer: fakeMailer(true).mailer, config, now: NOW, fetchFeed: feed });
  assertEquals((await h(sendReq({ mode: "send" }))).status, 502);
  assertEquals(sends.get("2026-10-31")?.status, "failed");
  assertEquals((await h(sendReq({ mode: "send" }))).status, 409);
});

Deno.test("provmejl går bara till test_to", async () => {
  const { store } = await seeded();
  const { mailer, outbox } = fakeMailer();
  const r = await (await sendHandler({ store, mailer, config, now: NOW, fetchFeed: feed })(sendReq({ mode: "test", test_to: "alx@exempel.se" }))).json();
  assertEquals(r.mode, "test");
  assertEquals(outbox.map((m) => m.to), ["alx@exempel.se"]);
});

// ---------- Resend-klienten ----------
Deno.test("Resend: batch om högst 100, Bearer, Idempotency-Key, from och reply_to", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const fetchImpl = ((url: string, init: RequestInit) => { calls.push({ url, init }); return Promise.resolve(new Response("{}", { status: 200 })); }) as unknown as typeof fetch;
  const m = resendMailer({ apiKey: "re_test", from: "Motorpuls <nyhetsbrev@motorpuls.se>", replyTo: "svar@motorpuls.se", fetchImpl });
  const msgs = Array.from({ length: 205 }, (_, i) => ({ to: `p${i}@exempel.se`, subject: "s", html: "h", text: "t", headers: { "List-Unsubscribe": "<x>" } }));
  const r = await m.send(msgs, "motorpuls-2026-10-31");
  assertEquals(r.sent, 205);
  assertEquals(calls.length, 3);
  assertEquals(calls[0].url, "https://api.resend.com/emails/batch");
  const h = calls[2].init.headers as Record<string, string>;
  assertEquals(h.Authorization, "Bearer re_test");
  assertEquals(h["Idempotency-Key"], "motorpuls-2026-10-31-2");
  const body = JSON.parse(calls[0].init.body as string);
  assertEquals(body.length, 100);
  assertEquals(body[0].from, "Motorpuls <nyhetsbrev@motorpuls.se>");
  assertEquals(body[0].reply_to, "svar@motorpuls.se");
  assertEquals(body[0].to, ["p0@exempel.se"]);
});

Deno.test("Resend utan nyckel: loggar bara, inget anrop", async () => {
  let called = false;
  const fetchImpl = (() => { called = true; return Promise.resolve(new Response()); }) as unknown as typeof fetch;
  const r = await resendMailer({ from: "x", fetchImpl }).send([{ to: "a@exempel.se", subject: "s", html: "h", text: "t", headers: {} }]);
  assert(r.logged);
  assert(!called);
});

Deno.test("Resend-fel ger undantag", async () => {
  const fetchImpl = (() => Promise.resolve(new Response("nej", { status: 422 }))) as unknown as typeof fetch;
  let threw = false;
  try { await resendMailer({ apiKey: "k", from: "x", fetchImpl }).send([{ to: "a@exempel.se", subject: "s", html: "h", text: "t", headers: {} }]); } catch { threw = true; }
  assert(threw);
});
