// STUB, inte driftsatt. Skickar en Web Push-notis till alla i public.push_subscriptions när en artikel publiceras.
// Körs som Supabase Edge Function (Deno). Anropas av publiceringen (t.ex. ett steg i GitHub Actions efter deploy) med
//   POST /functions/v1/send-push   Header: x-push-secret: <PUSH_SEND_SECRET>
//   Body: {"title": "...", "body": "...", "url": "/artikel/<slug>/", "tag": "<slug>"}
// Hemligheter (sätts med `supabase secrets set`, aldrig i repot): VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY,
// VAPID_SUBJECT (mailto:...), PUSH_SEND_SECRET. SUPABASE_URL och SUPABASE_SERVICE_ROLE_KEY finns automatiskt i funktionen.
import webpush from "npm:web-push@3.6.7";
import { createClient } from "npm:@supabase/supabase-js@2";

const env = (k: string) => {
  const v = Deno.env.get(k);
  if (!v) throw new Error(`saknar ${k}`);
  return v;
};

Deno.serve(async (req) => {
  if (req.method !== "POST") return new Response("bara POST", { status: 405 });
  if (req.headers.get("x-push-secret") !== env("PUSH_SEND_SECRET")) return new Response("nej", { status: 401 });

  const { title, body, url, tag } = await req.json();
  if (typeof title !== "string" || typeof url !== "string" || !url.startsWith("/")) {
    return new Response("title och url (/artikel/...) krävs", { status: 400 });
  }
  webpush.setVapidDetails(env("VAPID_SUBJECT"), env("VAPID_PUBLIC_KEY"), env("VAPID_PRIVATE_KEY"));
  const db = createClient(env("SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"), { auth: { persistSession: false } });

  const { data: subs, error } = await db.from("push_subscriptions").select("id, endpoint, p256dh, auth");
  if (error) return new Response(error.message, { status: 500 });

  const payload = JSON.stringify({ title, body: body ?? "", url, tag: tag ?? url });
  let sent = 0, removed = 0;
  // TODO före drift: skicka i omgångar (t.ex. 50 åt gången) och logga utfallet.
  for (const s of subs ?? []) {
    try {
      await webpush.sendNotification({ endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } }, payload, { TTL: 6 * 3600, urgency: "normal" });
      sent++;
    } catch (e) {
      const code = (e as { statusCode?: number }).statusCode;
      if (code === 404 || code === 410) { await db.from("push_subscriptions").delete().eq("id", s.id); removed++; } // prenumerationen finns inte längre
    }
  }
  return Response.json({ sent, removed, total: subs?.length ?? 0 });
});
