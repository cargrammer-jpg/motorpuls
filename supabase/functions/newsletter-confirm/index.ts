// Bekräftelse från sidan /prenumeration/bekrafta/ på motorpuls.se (knappen POSTar koden hit). GET ändrar inget.
// POST /functions/v1/newsletter-confirm  {"token": "<64 hex>"}  ->  {"status": "confirmed" | "already" | "missing"}
// Driftsätts med --no-verify-jwt.
import { confirmHandler } from "../_shared/handlers.ts";
import { serveLive } from "../_shared/deps.ts";

Deno.serve(serveLive(confirmHandler));
