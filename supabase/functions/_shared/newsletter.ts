// Motorpuls nyhetsbrev: ren logik och mejlmallar (inga nätverksanrop). Används av edge-funktionerna newsletter-*
// och testas i supabase/functions/tests/. Modell: BuildShipper (dubbel bekräftelse, separat bekräftelse- och
// avregistreringskod, List-Unsubscribe med one-click). Svensk text utan tankstreck.

export const SITE_DEFAULT = "https://motorpuls.se";
export const FROM_DEFAULT = "Motorpuls <nyhetsbrev@motorpuls.se>";
export const PENDING_DAYS = 30; // obekräftade adresser raderas efter så här många dagar
export const BATCH = 100; // Resends batch-API tar högst 100 mejl per anrop
export const MAX_ARTICLES = 12;

/** Samtyckestexten som sparas med varje anmälan. Servern väljer den, klienten skickar den aldrig. */
export const CONSENT_TEXT =
  "Få Motorpuls i inkorgen. De viktigaste bilnyheterna, korta och med källor. Helt gratis, avsluta när du vill. " +
  "Vi skickar ett mejl där du bekräftar först.";

export function normalizeEmail(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const email = value.trim().toLowerCase();
  if (email.length < 6 || email.length > 254) return null;
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return null;
  return email;
}

/** Sidan på motorpuls.se där anmälan gjordes, bara en sökväg ("/artikel/..."), annars null. */
export function normalizeSource(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const s = value.trim();
  if (!s.startsWith("/") || s.startsWith("//") || s.length > 300) return null;
  return /^[\w\-./%~]*$/.test(s) ? s : null;
}

export function isToken(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}

export async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Jämför två hemligheter utan att svarstiden avslöjar hur många tecken som stämde. */
export function safeEqual(a: string, b: string): boolean {
  const x = new TextEncoder().encode(a);
  const y = new TextEncoder().encode(b);
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return diff === 0;
}

/** Klientens IP enligt Supabase-gatewayen (första adressen i x-forwarded-for). */
export function clientIp(headers: Headers): string {
  const fwd = headers.get("x-forwarded-for") ?? "";
  return (fwd.split(",")[0] || headers.get("cf-connecting-ip") || headers.get("x-real-ip") || "okand").trim();
}

export type SubscriberState = "pending" | "confirmed";

/** Vad en ny anmälan ska leda till, givet raden som redan finns (BuildShipper: en väntande rad skrivs aldrig om). */
export function planSubscription(current: { status: SubscriberState } | null): "insert" | "resend" | "already" {
  if (!current) return "insert";
  return current.status === "pending" ? "resend" : "already";
}

export function links(site: string, functionsUrl: string, confirmToken: string, unsubscribeToken: string) {
  return {
    confirmUrl: `${site}/prenumeration/bekrafta/?token=${confirmToken}`,
    unsubscribePage: `${site}/prenumeration/avsluta/?token=${unsubscribeToken}`,
    oneClickUrl: `${functionsUrl}/newsletter-unsubscribe?token=${unsubscribeToken}`,
  };
}

/** RFC 8058: one-click-avregistrering. Mejlprogrammet POSTar till adressen, utan sida och utan knapp. */
export function unsubscribeHeaders(oneClickUrl: string): Record<string, string> {
  return { "List-Unsubscribe": `<${oneClickUrl}>`, "List-Unsubscribe-Post": "List-Unsubscribe=One-Click" };
}

export function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// ---------- mejlmallar ----------
const C = { bg: "#0B0D10", card: "#151A20", line: "#252C35", text: "#EEF1F4", text2: "#C3CAD1", muted: "#929CA7", pulse: "#FF5B1F", pulseText: "#FF8A5C" };
const FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif";

function shell(preheader: string, inner: string, footerHtml: string): string {
  return `<!doctype html>
<html lang="sv"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark light"><meta name="supported-color-schemes" content="dark light"><title>Motorpuls</title></head>
<body style="margin:0;padding:0;background:${C.bg};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">${esc(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:${C.bg};"><tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;">
<tr><td style="padding:0 4px 16px;font-family:${FONT};font-size:22px;font-weight:800;letter-spacing:-0.02em;color:${C.text};">
<a href="${SITE_DEFAULT}/" style="color:${C.text};text-decoration:none;">MOTOR<span style="color:${C.pulse};">PULS</span></a></td></tr>
<tr><td style="background:${C.card};border:1px solid ${C.line};border-top:3px solid ${C.pulse};border-radius:10px;padding:28px 24px;">
${inner}
</td></tr>
<tr><td style="padding:18px 4px 0;font-family:${FONT};font-size:13px;line-height:20px;color:${C.muted};">${footerHtml}</td></tr>
</table></td></tr></table></body></html>`;
}

function button(href: string, label: string): string {
  return `<table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0 6px;"><tr><td style="border-radius:8px;background:${C.pulse};">
<a href="${esc(href)}" style="display:inline-block;padding:13px 22px;font-family:${FONT};font-size:16px;font-weight:700;color:#0B0D10;text-decoration:none;border-radius:8px;">${esc(label)}</a></td></tr></table>`;
}

const P = (t: string) => `<p style="margin:0 0 14px;font-family:${FONT};font-size:16px;line-height:25px;color:${C.text2};">${t}</p>`;

export type Mail = { subject: string; html: string; text: string };

export function renderConfirmEmail(l: { confirmUrl: string; unsubscribePage: string }): Mail {
  const subject = "Bekräfta din prenumeration på Motorpuls";
  const inner = `<p style="margin:0 0 6px;font-family:${FONT};font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:${C.pulseText};">Nyhetsbrev</p>
<h1 style="margin:0 0 14px;font-family:${FONT};font-size:24px;line-height:30px;font-weight:800;color:${C.text};">Ett klick kvar</h1>
${P("Den här adressen anmäldes till Motorpuls nyhetsbrev på motorpuls.se. Tryck på knappen för att bekräfta att det var du.")}
${P("Vi skickar inga nyhetsbrev förrän du har bekräftat.")}
${button(l.confirmUrl, "Bekräfta prenumerationen")}
<p style="margin:14px 0 0;font-family:${FONT};font-size:13px;line-height:20px;color:${C.muted};">Fungerar inte knappen? Öppna den här länken:<br><a href="${esc(l.confirmUrl)}" style="color:${C.pulseText};word-break:break-all;">${esc(l.confirmUrl)}</a></p>`;
  const footer = `Var det inte du som anmälde dig? Då händer inget mer. Adressen raderas automatiskt efter ${PENDING_DAYS} dagar om den inte bekräftas. Du kan också <a href="${esc(l.unsubscribePage)}" style="color:${C.muted};">ta bort adressen direkt</a>.`;
  const text = [
    "Ett klick kvar",
    "",
    "Den här adressen anmäldes till Motorpuls nyhetsbrev på motorpuls.se. Öppna länken för att bekräfta att det var du:",
    l.confirmUrl,
    "",
    "Vi skickar inga nyhetsbrev förrän du har bekräftat.",
    "",
    `Var det inte du? Då händer inget mer. Adressen raderas automatiskt efter ${PENDING_DAYS} dagar om den inte bekräftas.`,
    `Ta bort adressen direkt: ${l.unsubscribePage}`,
  ].join("\n");
  return { subject, html: shell("Bekräfta med ett klick så börjar nyhetsbrevet komma.", inner, footer), text };
}

export type Article = { title: string; url: string; description: string; category: string; published: Date };

const MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"];

/** Datum i Stockholmstid, t.ex. "31 oktober 2026". */
export function svDate(d: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Stockholm", year: "numeric", month: "numeric", day: "numeric" }).formatToParts(d);
  const get = (t: string) => Number(parts.find((p) => p.type === t)?.value);
  return `${get("day")} ${MONTHS[get("month") - 1]} ${get("year")}`;
}

/** Nyckel för ett utskick: datumet i Stockholm (YYYY-MM-DD). Ett utskick per dag och nyckel. */
export function issueKey(d: Date): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Stockholm", year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
}

export function issueSubject(articles: Article[]): string {
  if (articles.length === 0) return "Motorpuls nyhetsbrev";
  const more = articles.length - 1;
  return more > 0 ? `${articles[0].title} (och ${more} till)` : articles[0].title;
}

export function renderIssue(articles: Article[], when: Date, unsubscribePage: string): Mail {
  const subject = issueSubject(articles);
  const items = articles.map((a, i) => `
<tr><td style="padding:${i === 0 ? "4px" : "18px"} 0 18px;${i < articles.length - 1 ? `border-bottom:1px solid ${C.line};` : ""}">
<p style="margin:0 0 6px;font-family:${FONT};font-size:12px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:${C.pulseText};">${esc(a.category)}</p>
<a href="${esc(a.url)}" style="font-family:${FONT};font-size:19px;line-height:25px;font-weight:750;color:${C.text};text-decoration:none;">${esc(a.title)}</a>
<p style="margin:8px 0 0;font-family:${FONT};font-size:15px;line-height:23px;color:${C.text2};">${esc(a.description)}</p>
<p style="margin:8px 0 0;font-family:${FONT};font-size:14px;"><a href="${esc(a.url)}" style="color:${C.pulseText};font-weight:600;">Läs artikeln</a></p>
</td></tr>`).join("");
  const inner = `<p style="margin:0 0 6px;font-family:${FONT};font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:${C.pulseText};">Nyhetsbrev, ${esc(svDate(when))}</p>
<h1 style="margin:0 0 10px;font-family:${FONT};font-size:24px;line-height:30px;font-weight:800;color:${C.text};">Senaste från Motorpuls</h1>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">${items}</table>`;
  const footer = `Du får det här mejlet för att du prenumererar på Motorpuls nyhetsbrev. <a href="${esc(unsubscribePage)}" style="color:${C.muted};">Avsluta prenumerationen</a>. Det går också att avsluta direkt i ditt mejlprogram.<br><a href="${SITE_DEFAULT}/integritet/" style="color:${C.muted};">Så hanterar vi din adress</a>`;
  const text = [
    `Senaste från Motorpuls, ${svDate(when)}`,
    "",
    ...articles.flatMap((a) => [`${a.title}`, a.description, a.url, ""]),
    "Du får det här mejlet för att du prenumererar på Motorpuls nyhetsbrev.",
    `Avsluta prenumerationen: ${unsubscribePage}`,
  ].join("\n");
  return { subject, html: shell(articles[0]?.description ?? "Senaste från Motorpuls", inner, footer), text };
}

// ---------- RSS ----------
function decodeXml(s: string): string {
  return s
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'")
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&amp;/g, "&")
    .trim();
}

/** Läser Motorpuls egen feed.xml (RSS 2.0). Bara artiklar på sajtens egen domän tas med. */
export function parseFeed(xml: string, site = SITE_DEFAULT): Article[] {
  const out: Article[] = [];
  for (const m of xml.matchAll(/<item>([\s\S]*?)<\/item>/g)) {
    const tag = (name: string) => decodeXml(m[1].match(new RegExp(`<${name}>([\\s\\S]*?)</${name}>`))?.[1] ?? "");
    const url = tag("link");
    const published = new Date(tag("pubDate"));
    if (!url.startsWith(site + "/") || Number.isNaN(published.getTime())) continue;
    out.push({ title: tag("title"), url, description: tag("description"), category: tag("category"), published });
  }
  return out;
}

/** Artiklar publicerade efter since, nyast först, högst max. */
export function pickArticles(all: Article[], since: Date, max = MAX_ARTICLES): Article[] {
  return all.filter((a) => a.published > since).sort((a, b) => b.published.getTime() - a.published.getTime()).slice(0, max);
}
