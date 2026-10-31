// Utskick av nyhetsbrevet med de senaste artiklarna från feed.xml till alla bekräftade adresser (Resend, 100 per anrop).
// POST /functions/v1/newsletter-send  Header: x-newsletter-secret: <NEWSLETTER_SEND_SECRET>
// Body: {"mode": "dry-run" | "test" | "send", "test_to": "...", "since": "...", "issue_key": "..."}. Standard är dry-run.
// Riktiga utskick bara när NEWSLETTER_SEND_ENABLED=true. Driftsätts med --no-verify-jwt (skyddas av hemligheten).
import { sendHandler } from "../_shared/handlers.ts";
import { liveDeps } from "../_shared/deps.ts";

Deno.serve(sendHandler(liveDeps()));
