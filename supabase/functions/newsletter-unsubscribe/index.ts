// Avregistrering: one-click från mejlprogrammet (List-Unsubscribe-Post) eller knappen på /prenumeration/avsluta/.
// POST /functions/v1/newsletter-unsubscribe?token=<64 hex>  ->  {"status": "unsubscribed" | "missing"}. Raden raderas.
// GET skickas vidare (303) till sidan på motorpuls.se och ändrar inget. Driftsätts med --no-verify-jwt.
import { unsubscribeHandler } from "../_shared/handlers.ts";
import { serveLive } from "../_shared/deps.ts";

Deno.serve(serveLive(unsubscribeHandler));
