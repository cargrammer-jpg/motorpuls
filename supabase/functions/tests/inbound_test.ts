// Tester för inbound-forward utan nätverk. Kör: deno test supabase/functions/tests/
import { assert, assertEquals } from "jsr:@std/assert@1";
import { buildForward, type ForwardMail, type InboundDeps, inboundHandler, verifySvix } from "../_shared/inbound.ts";

const SECRET = "whsec_" + btoa("hemlig-nyckel-for-test-1234567890");
const NOW = 1_800_000_000;

async function sign(body: string, id = "msg_1", ts = NOW) {
  const raw = Uint8Array.from(atob(SECRET.slice(6)), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey("raw", raw, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${id}.${ts}.${body}`)));
  return { "svix-id": id, "svix-timestamp": String(ts), "svix-signature": `v1,${btoa(String.fromCharCode(...mac))}` };
}

function deps(over: Partial<InboundDeps> = {}) {
  const sent: ForwardMail[] = [];
  const claimed = new Map<string, string>();
  const d: InboundDeps = {
    webhookSecret: SECRET, forwardTo: "moedare@mail.grokbot.com", now: () => NOW * 1000,
    getEmail: (id) => Promise.resolve({ id, from: "Läsare <lasare@exempel.se>", to: ["hello@motorpuls.se"], subject: "Tips om Volvo", created_at: "2026-10-31T13:00:00Z", html: "<p>Hej!</p>", text: "Hej!" }),
    listAttachments: () => Promise.resolve([{ id: "a1", filename: "bild.png", content_type: "image/png", size: 3, download_url: "https://x/a1" }]),
    download: () => Promise.resolve(new Uint8Array([1, 2, 3])),
    send: (m) => { sent.push(m); return Promise.resolve("fwd_1"); },
    claim: (id) => { if (claimed.has(id)) return Promise.resolve(false); claimed.set(id, "forwarding"); return Promise.resolve(true); },
    finish: (id, s) => { claimed.set(id, s); return Promise.resolve(); },
    ...over,
  };
  return { d, sent, claimed };
}
const ev = (to = ["hello@motorpuls.se"], id = "e1", type = "email.received") => JSON.stringify({ type, data: { email_id: id, from: "lasare@exempel.se", to } });
const req = async (body: string, h?: Record<string, string>) => new Request("https://f/inbound-forward", { method: "POST", body, headers: h ?? await sign(body) });

Deno.test("svix: rätt signatur godkänns, fel, gammal eller saknad avvisas", async () => {
  const b = ev();
  const h = new Headers(await sign(b));
  assert(await verifySvix(SECRET, h, b, NOW));
  assert(!(await verifySvix(SECRET, h, b + " ", NOW)));
  assert(!(await verifySvix(SECRET, h, b, NOW + 600)));
  assert(!(await verifySvix(SECRET, new Headers(), b, NOW)));
});

Deno.test("vidarebefordrar till moedare med reply_to, Fwd-ämne, rubrikrader och bilaga", async () => {
  const { d, sent, claimed } = deps();
  const r = await inboundHandler(d)(await req(ev()));
  assertEquals(r.status, 200);
  assertEquals(sent.length, 1);
  const m = sent[0];
  assertEquals(m.to, ["moedare@mail.grokbot.com"]);
  assertEquals(m.from, "Motorpuls <hello@motorpuls.se>");
  assertEquals(m.reply_to, "lasare@exempel.se");
  assertEquals(m.subject, "Fwd: Tips om Volvo");
  assert(m.html.includes("Från: Läsare &lt;lasare@exempel.se&gt;") && m.html.endsWith("<p>Hej!</p>"));
  assert(m.text.includes("Till: hello@motorpuls.se") && m.text.includes("Datum: 2026-10-31 14:00:00"));
  assertEquals(m.attachments.map((a) => [a.filename, a.content]), [["bild.png", "AQID"]]);
  assertEquals(claimed.get("e1"), "forwarded");
});

Deno.test("fel signatur ger 401 och inget skickas", async () => {
  const { d, sent } = deps();
  const r = await inboundHandler(d)(await req(ev(), { "svix-id": "msg_1", "svix-timestamp": String(NOW), "svix-signature": "v1,fel" }));
  assertEquals(r.status, 401);
  assertEquals(sent.length, 0);
});

Deno.test("andra mottagare, andra händelser och dubbletter ignoreras", async () => {
  const { d, sent } = deps();
  const h = inboundHandler(d);
  assertEquals((await (await h(await req(ev(["info@motorpuls.se"])))).json()).ignored, "recipient");
  assertEquals((await (await h(await req(ev(undefined, "e2", "email.sent")))).json()).ignored, "type");
  await h(await req(ev(undefined, "e3")));
  assertEquals((await (await h(await req(ev(undefined, "e3"), await sign(ev(undefined, "e3"), "msg_2")))).json()).ignored, "duplicate");
  assertEquals(sent.length, 1);
});

Deno.test("slingskydd: mejl från motorpuls.se skickas inte vidare, provet från nyhetsbrev@ gör det", async () => {
  const own = deps({ getEmail: (id) => Promise.resolve({ id, from: "hello@motorpuls.se", to: ["hello@motorpuls.se"], subject: "x" }) });
  assertEquals((await (await inboundHandler(own.d)(await req(ev()))).json()).ignored, "loop");
  assertEquals(own.sent.length, 0);
  const test = deps({ getEmail: (id) => Promise.resolve({ id, from: "nyhetsbrev@motorpuls.se", to: ["hello@motorpuls.se"], subject: "Prov", text: "t" }) });
  assertEquals((await inboundHandler(test.d)(await req(ev()))).status, 200);
  assertEquals(test.sent.length, 1);
});

Deno.test("bilaga som inte går att hämta listas i stället", () => {
  const m = buildForward({ id: "e", from: "a@exempel.se", to: ["hello@motorpuls.se"], subject: "", text: "t" }, "x@y.se", [], ["stor.zip"]);
  assertEquals(m.subject, "Fwd: (inget ämne)");
  assert(m.text.includes("stor.zip"));
});
