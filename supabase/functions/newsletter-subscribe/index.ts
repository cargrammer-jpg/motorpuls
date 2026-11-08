// Anmälan från nyhetsbrevsrutan på motorpuls.se: sparar en väntande rad och skickar bekräftelsemejlet (dubbel bekräftelse).
// POST /functions/v1/newsletter-subscribe  {"email": "...", "source": "/artikel/...", "webbplats": ""}
// Driftsätts med --no-verify-jwt (anropas från webbläsaren utan inloggning; skyddas av Origin, honungsfälla och gränser).
import { subscribeHandler } from "../_shared/handlers.ts";
import { serveLive } from "../_shared/deps.ts";

Deno.serve(serveLive(subscribeHandler));
