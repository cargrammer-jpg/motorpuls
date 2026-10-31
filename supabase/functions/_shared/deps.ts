// Riktiga beroenden för edge-funktionerna (Supabase med service role och Resend). Hemligheter läses bara från miljön
// (`supabase secrets set`), aldrig från repot. SUPABASE_URL och SUPABASE_SERVICE_ROLE_KEY finns automatiskt i funktionen.
import { configFromEnv, type Deps } from "./handlers.ts";
import { resendMailer } from "./mail.ts";
import { FROM_DEFAULT } from "./newsletter.ts";
import { supabaseStore } from "./store.ts";

export function liveDeps(): Deps {
  const get = (k: string) => Deno.env.get(k);
  const url = get("SUPABASE_URL");
  const key = get("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !key) throw new Error("saknar SUPABASE_URL eller SUPABASE_SERVICE_ROLE_KEY");
  return {
    store: supabaseStore(url, key),
    mailer: resendMailer({ apiKey: get("RESEND_API_KEY"), from: get("NEWSLETTER_FROM") || FROM_DEFAULT, replyTo: get("NEWSLETTER_REPLY_TO") || undefined }),
    config: configFromEnv(get),
  };
}
