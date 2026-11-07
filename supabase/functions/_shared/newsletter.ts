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
// Mörkt tema som sajten (DESIGN.md): nästan svart botten, orange accent, ordmärket MOTORPULS följt av den lilla svenska
// flaggan (#0A2260 / #FECC00) som i sidhuvudet. Bara tabeller och inline-CSS, 600 px, så att Outlook (även Hotmail och
// live.com), Gmail och Apple Mail visar samma sak. Ordmärket och flaggan är text och tabellceller, inte bilder, så de syns
// även när mejlprogrammet blockerar bilder. Bakgrunderna har dessutom en linear-gradient i samma färg, så att Gmail i
// mörkt läge inte vänder färgerna.
export const CONTACT_EMAIL = "hello@motorpuls.se";
export const REPLY_TO_DEFAULT = CONTACT_EMAIL;
export const ISSUE_CARDS = 5; // artiklar under huvudartikeln (högst)

const C = {
  bg: "#0B0D10", bg2: "#101318", card: "#151A20", raised: "#1B2129", line: "#252C35", lineStrong: "#3A434E",
  text: "#EEF1F4", text2: "#C3CAD1", muted: "#929CA7", pulse: "#FF5B1F", pulseText: "#FF8A5C", flagBlue: "#0A2260", flagYellow: "#FECC00",
};
const FONT = "'Archivo','Helvetica Neue',Helvetica,Arial,sans-serif";
const WORDMARK_FONT = "'Arial Black','Archivo','Helvetica Neue',Helvetica,Arial,sans-serif";
const MONO = "'DM Mono',ui-monospace,Menlo,Consolas,monospace";
const bgc = (c: string) => `background-color:${c};background-image:linear-gradient(${c},${c});`;

/** Svenska flaggan 16:10 (5:2:9 och 4:2:4) som tabellceller. Fungerar i Outlook, kräver inga bilder. */
function flagTable(w = 24): string {
  const u = w / 16;
  const px = (n: number) => `${Math.round(n * u)}px`;
  const cell = (cw: number, ch: number, c: string) =>
    `<td width="${px(cw)}" height="${px(ch)}" style="width:${px(cw)};height:${px(ch)};${bgc(c)}font-size:0;line-height:0;mso-line-height-rule:exactly;">&nbsp;</td>`;
  const row = (h: number, c1: string, c2: string, c3: string) => `<tr>${cell(5, h, c1)}${cell(2, h, c2)}${cell(9, h, c3)}</tr>`;
  return `<table role="presentation" cellpadding="0" cellspacing="0" border="0" aria-hidden="true" style="border-collapse:collapse;display:inline-table;vertical-align:middle;">` +
    row(4, C.flagBlue, C.flagYellow, C.flagBlue) + row(2, C.flagYellow, C.flagYellow, C.flagYellow) + row(4, C.flagBlue, C.flagYellow, C.flagBlue) + `</table>`;
}

function wordmark(size = 22, flagW = 24): string {
  return `<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
<td style="font-family:${WORDMARK_FONT};font-size:${size}px;line-height:${size + 4}px;font-weight:900;letter-spacing:0.5px;mso-line-height-rule:exactly;">
<a href="${SITE_DEFAULT}/" style="color:${C.text};text-decoration:none;"><span style="color:${C.text};">MOTOR</span><span style="color:${C.text};">PULS</span></a></td>
<td width="${Math.round(size * 0.45)}" style="width:${Math.round(size * 0.45)}px;font-size:0;line-height:0;">&nbsp;</td>
<td valign="middle" style="vertical-align:middle;">${flagTable(flagW)}</td></tr></table>`;
}

const PREHEADER_PAD = "&#8199;&#65279;&#847; ".repeat(60);

function shell(o: { title: string; preheader: string; label: string; body: string; footer: string }): string {
  return `<!doctype html>
<html lang="sv" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="x-apple-disable-message-reformatting">
<meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no">
<meta name="color-scheme" content="dark light">
<meta name="supported-color-schemes" content="dark light">
<title>${esc(o.title)}</title>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
<style>
:root{color-scheme:dark light;supported-color-schemes:dark light;}
body,table,td,a{-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;}
table,td{mso-table-lspace:0pt;mso-table-rspace:0pt;}
img{border:0;outline:none;text-decoration:none;-ms-interpolation-mode:bicubic;display:block;}
a{color:${C.pulseText};}
a[x-apple-data-detectors]{color:inherit!important;text-decoration:none!important;}
u + #body a{color:inherit;text-decoration:none;}
@media (max-width:599px){
  .wrap{width:100%!important;}
  .px{padding-left:20px!important;padding-right:20px!important;}
  .hero-title{font-size:24px!important;line-height:30px!important;}
  .stack{display:block!important;width:100%!important;max-width:100%!important;}
  .thumb{padding:0 0 14px 0!important;}
  .thumb img{width:100%!important;max-width:100%!important;height:auto!important;}
  .card-pad{padding:18px!important;}
  .hide-m{display:none!important;}
}
[data-ogsc] .t-text{color:${C.text}!important;}
[data-ogsc] .t-muted{color:${C.muted}!important;}
</style>
</head>
<body id="body" style="margin:0;padding:0;width:100%;${bgc(C.bg)}">
<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all;">${esc(o.preheader)}${PREHEADER_PAD}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="${C.bg}" style="${bgc(C.bg)}">
<tr><td align="center" style="padding:0;">
<!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" align="center"><tr><td><![endif]-->
<table role="presentation" class="wrap" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;">
<tr><td height="4" style="height:4px;${bgc(C.pulse)}font-size:0;line-height:0;">&nbsp;</td></tr>
<tr><td class="px" style="padding:26px 32px 22px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td valign="middle">${wordmark()}</td>
<td valign="middle" align="right" class="t-muted" style="font-family:${MONO};font-size:12px;line-height:16px;letter-spacing:0.06em;text-transform:uppercase;color:${C.muted};">${esc(o.label)}</td>
</tr></table>
</td></tr>
${o.body}
<tr><td class="px" style="padding:8px 32px 40px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td style="border-top:1px solid ${C.line};font-size:0;line-height:0;height:1px;">&nbsp;</td></tr>
<tr><td style="padding:24px 0 14px;">${wordmark(15, 16)}</td></tr>
<tr><td class="t-muted" style="font-family:${FONT};font-size:13px;line-height:21px;color:${C.muted};">${o.footer}</td></tr>
</table>
</td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
</td></tr></table>
</body></html>`;
}

/** Knapp som fungerar i Outlook (färgad cell med padding) och överallt annars. */
function button(href: string, label: string, ghost = false): string {
  const bg = ghost ? C.bg : C.pulse;
  const color = ghost ? C.text : "#0B0D10";
  const border = ghost ? `border:1px solid ${C.lineStrong};` : `border:1px solid ${C.pulse};`;
  return `<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
<td bgcolor="${bg}" style="${bgc(bg)}${border}border-radius:4px;mso-padding-alt:13px 22px;">
<a href="${esc(href)}" style="display:inline-block;padding:13px 22px;font-family:${FONT};font-size:15px;line-height:18px;font-weight:700;color:${color};text-decoration:none;border-radius:4px;">${esc(label)}&nbsp;&rarr;</a>
</td></tr></table>`;
}

const kicker = (t: string, color: string = C.pulseText) =>
  `<p style="margin:0 0 10px;font-family:${MONO};font-size:12px;line-height:16px;font-weight:500;letter-spacing:0.08em;text-transform:uppercase;color:${color};">${t}</p>`;
const P = (t: string) => `<p class="t-text" style="margin:0 0 14px;font-family:${FONT};font-size:16px;line-height:25px;color:${C.text2};">${t}</p>`;
const mailto = `<a href="mailto:${CONTACT_EMAIL}" style="color:${C.text2};text-decoration:underline;">${CONTACT_EMAIL}</a>`;

export type Mail = { subject: string; html: string; text: string };

export function renderConfirmEmail(l: { confirmUrl: string; unsubscribePage: string }): Mail {
  const subject = "Bekräfta din prenumeration på Motorpuls";
  const body = `<tr><td class="px" style="padding:0 32px 28px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="${C.card}" style="${bgc(C.card)}border:1px solid ${C.line};border-radius:6px;">
<tr><td class="card-pad" style="padding:32px 30px 30px;">
${kicker("Ett steg kvar")}
<h1 class="hero-title t-text" style="margin:0 0 14px;font-family:${FONT};font-size:28px;line-height:34px;font-weight:800;letter-spacing:-0.01em;color:${C.text};">Bekräfta att det var du</h1>
${P("Någon, förhoppningsvis du, anmälde den här adressen till Motorpuls nyhetsbrev på motorpuls.se. Tryck på knappen så är du med.")}
${P("Vi skickar inga nyhetsbrev förrän du har bekräftat.")}
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:8px 0 0;"><tr><td>${button(l.confirmUrl, "Bekräfta prenumerationen")}</td></tr></table>
<p class="t-muted" style="margin:22px 0 0;font-family:${FONT};font-size:13px;line-height:20px;color:${C.muted};">Fungerar inte knappen? Kopiera länken till webbläsaren:<br><a href="${esc(l.confirmUrl)}" style="color:${C.pulseText};word-break:break-all;">${esc(l.confirmUrl)}</a></p>
</td></tr></table>
</td></tr>
<tr><td class="px" style="padding:0 32px 24px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
<td valign="top" width="24" style="width:24px;font-family:${FONT};font-size:16px;line-height:22px;color:${C.pulse};">&#9679;</td>
<td class="t-text" style="font-family:${FONT};font-size:14px;line-height:22px;color:${C.text2};">De viktigaste bilnyheterna, korta och med källor. Elbilar, sportbilar, laddning och förnybara bränslen.</td>
</tr></table>
</td></tr>`;
  const footer = `Var det inte du som anmälde dig? Då behöver du inte göra något. Adressen raderas automatiskt efter ${PENDING_DAYS} dagar om den inte bekräftas. Du kan också <a href="${esc(l.unsubscribePage)}" style="color:${C.text2};text-decoration:underline;">ta bort adressen direkt</a>.<br><br>Frågor om dina uppgifter? Mejla ${mailto}. <a href="${SITE_DEFAULT}/integritet/" style="color:${C.text2};text-decoration:underline;">Så hanterar vi din adress</a>.`;
  const text = [
    "MOTORPULS",
    "",
    "Bekräfta att det var du",
    "",
    "Någon, förhoppningsvis du, anmälde den här adressen till Motorpuls nyhetsbrev på motorpuls.se. Öppna länken för att bekräfta:",
    l.confirmUrl,
    "",
    "Vi skickar inga nyhetsbrev förrän du har bekräftat.",
    "",
    `Var det inte du? Då behöver du inte göra något. Adressen raderas automatiskt efter ${PENDING_DAYS} dagar om den inte bekräftas.`,
    `Ta bort adressen direkt: ${l.unsubscribePage}`,
    "",
    `Frågor om dina uppgifter? Mejla ${CONTACT_EMAIL}.`,
    `Så hanterar vi din adress: ${SITE_DEFAULT}/integritet/`,
  ].join("\n");
  return { subject, html: shell({ title: subject, preheader: "Ett klick kvar, sedan kommer de viktigaste bilnyheterna till din inkorg.", label: "Nyhetsbrev", body, footer }), text };
}

export type Article = { title: string; url: string; description: string; category: string; published: Date; image?: string };

const MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"];
const WEEKDAYS = ["söndag", "måndag", "tisdag", "onsdag", "torsdag", "fredag", "lördag"];

/** Datum i Stockholmstid, t.ex. "31 oktober 2026". */
export function svDate(d: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Stockholm", year: "numeric", month: "numeric", day: "numeric" }).formatToParts(d);
  const get = (t: string) => Number(parts.find((p) => p.type === t)?.value);
  return `${get("day")} ${MONTHS[get("month") - 1]} ${get("year")}`;
}

function svWeekday(d: Date): string {
  const [y, m, day] = issueKey(d).split("-").map(Number);
  return WEEKDAYS[new Date(Date.UTC(y, m - 1, day)).getUTCDay()];
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

/** Delningsbilden som build.py gör för varje artikel: <sajt>/img/og/<slug>.jpg (1200x630 JPEG). */
export function articleImage(url: string, site = SITE_DEFAULT): string | undefined {
  const m = url.match(/^https:\/\/[^/]+\/artikel\/([a-z0-9-]+)\/$/);
  return m ? `${site}/img/og/${m[1]}.jpg` : undefined;
}

function heroBlock(a: Article): string {
  const img = a.image
    ? `<tr><td style="padding:0;font-size:0;line-height:0;"><a href="${esc(a.url)}"><img src="${esc(a.image)}" width="536" alt="${esc(a.title)}" style="width:100%;max-width:536px;height:auto;display:block;border:0;border-radius:6px 6px 0 0;"></a></td></tr>`
    : `<tr><td height="4" style="height:4px;${bgc(C.pulse)}font-size:0;line-height:0;border-radius:6px 6px 0 0;">&nbsp;</td></tr>`;
  return `<tr><td class="px" style="padding:0 32px 28px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="${C.card}" style="${bgc(C.card)}border:1px solid ${C.line};border-radius:6px;">
${img}
<tr><td class="card-pad" style="padding:26px 28px 28px;">
${kicker(`<span style="color:${C.pulse};">&#9679;</span>&nbsp; Senaste nytt &nbsp;<span style="color:${C.pulseText};">${esc(a.category)}</span>`, C.muted)}
<h1 class="hero-title" style="margin:0 0 12px;font-family:${FONT};font-size:28px;line-height:34px;font-weight:800;letter-spacing:-0.01em;"><a href="${esc(a.url)}" class="t-text" style="color:${C.text};text-decoration:none;">${esc(a.title)}</a></h1>
${P(esc(a.description))}
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:6px 0 0;"><tr><td>${button(a.url, "Läs hela artikeln")}</td></tr></table>
</td></tr></table>
</td></tr>`;
}

function cardBlock(a: Article): string {
  const thumb = a.image
    ? `<td class="stack thumb" width="150" valign="top" style="width:150px;padding:0 20px 0 0;"><a href="${esc(a.url)}"><img src="${esc(a.image)}" width="150" alt="" style="width:150px;height:auto;display:block;border:0;border-radius:4px;"></a></td>`
    : "";
  return `<tr><td class="px" style="padding:0 32px 14px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="${C.card}" style="${bgc(C.card)}border:1px solid ${C.line};border-radius:6px;">
<tr><td class="card-pad" style="padding:20px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
${thumb}
<td class="stack" valign="top">
${kicker(esc(a.category))}
<h2 style="margin:0 0 8px;font-family:${FONT};font-size:18px;line-height:24px;font-weight:750;"><a href="${esc(a.url)}" class="t-text" style="color:${C.text};text-decoration:none;">${esc(a.title)}</a></h2>
<p class="t-text" style="margin:0 0 10px;font-family:${FONT};font-size:14px;line-height:22px;color:${C.text2};">${esc(a.description)}</p>
<p style="margin:0;font-family:${FONT};font-size:14px;line-height:20px;font-weight:700;"><a href="${esc(a.url)}" style="color:${C.pulseText};text-decoration:none;">Läs mer&nbsp;&rarr;</a></p>
</td></tr></table>
</td></tr></table>
</td></tr>`;
}

export function renderIssue(articles: Article[], when: Date, unsubscribePage: string, opts: { subjectPrefix?: string } = {}): Mail {
  const subject = `${opts.subjectPrefix ?? ""}${issueSubject(articles)}`;
  const [hero, ...rest] = articles;
  const cards = rest.slice(0, ISSUE_CARDS);
  const extra = rest.length - cards.length;
  const dateLabel = `${svWeekday(when)} ${svDate(when)}`;
  const intro = `<tr><td class="px" style="padding:0 32px 20px;">
<p class="t-text" style="margin:0;font-family:${FONT};font-size:15px;line-height:23px;color:${C.text2};">Hej! Här är det viktigaste från Motorpuls sedan förra brevet. ${articles.length === 1 ? "En nyhet" : `${articles.length} nyheter`}, korta och med källor.</p>
</td></tr>`;
  const moreHead = cards.length
    ? `<tr><td class="px" style="padding:4px 32px 14px;">${kicker(`<span style="color:${C.pulse};">&#9679;</span>&nbsp; Mer från Motorpuls`, C.muted)}</td></tr>`
    : "";
  const all = `<tr><td class="px" align="left" style="padding:12px 32px 32px;">
${extra > 0 ? `<p class="t-text" style="margin:0 0 14px;font-family:${FONT};font-size:14px;line-height:22px;color:${C.text2};">Och ${extra} till på sajten.</p>` : ""}
${button(`${SITE_DEFAULT}/`, "Alla nyheter på motorpuls.se", true)}
</td></tr>`;
  const body = hero ? intro + heroBlock(hero) + moreHead + cards.map(cardBlock).join("") + all : intro + all;
  const footer = `Du får det här mejlet för att du har anmält dig till Motorpuls nyhetsbrev på motorpuls.se och bekräftat adressen.<br><br>
<a href="${esc(unsubscribePage)}" style="color:${C.text};font-weight:700;text-decoration:underline;">Avsluta prenumerationen</a> med ett klick. Då raderas din adress direkt. Det går också att avsluta i ditt mejlprogram.<br><br>
Frågor om dina uppgifter? Mejla ${mailto}. <a href="${SITE_DEFAULT}/integritet/" style="color:${C.text2};text-decoration:underline;">Så hanterar vi din adress</a>.`;
  const shown = hero ? [hero, ...cards] : [];
  const text = [
    `MOTORPULS NYHETSBREV, ${dateLabel}`,
    "",
    "Hej! Här är det viktigaste från Motorpuls sedan förra brevet.",
    "",
    ...shown.flatMap((a, i) => [`${i === 0 ? "SENASTE NYTT" : a.category.toUpperCase()}${i === 0 ? `: ${a.category}` : ""}`, a.title, a.description, `Läs mer: ${a.url}`, ""]),
    ...(extra > 0 ? [`Och ${extra} till på sajten.`, ""] : []),
    `Alla nyheter: ${SITE_DEFAULT}/`,
    "",
    "Du får det här mejlet för att du har anmält dig till Motorpuls nyhetsbrev på motorpuls.se och bekräftat adressen.",
    `Avsluta prenumerationen: ${unsubscribePage}`,
    `Frågor om dina uppgifter? Mejla ${CONTACT_EMAIL}.`,
    `Så hanterar vi din adress: ${SITE_DEFAULT}/integritet/`,
  ].join("\n");
  const preheader = hero ? `${hero.description}` : "Senaste från Motorpuls";
  return { subject, html: shell({ title: subject, preheader, label: dateLabel, body, footer }), text };
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
    out.push({ title: tag("title"), url, description: tag("description"), category: tag("category"), published, image: articleImage(url, site) });
  }
  return out;
}

/** Artiklar publicerade efter since, nyast först, högst max. */
export function pickArticles(all: Article[], since: Date, max = MAX_ARTICLES): Article[] {
  return all.filter((a) => a.published > since).sort((a, b) => b.published.getTime() - a.published.getTime()).slice(0, max);
}
