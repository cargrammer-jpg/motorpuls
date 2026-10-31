// Supabase-lagring för nyhetsbrevet. Funktionerna kör med service role (bara på servern), så RLS stoppar inte dem.
// Rollerna anon och authenticated har ingen åtkomst till tabellerna alls (se migrationen).
import { createClient, type SupabaseClient } from "npm:@supabase/supabase-js@2";
import type { SubscriberState } from "./newsletter.ts";

export type Subscriber = { id: string; email: string; status: SubscriberState; confirm_token: string; unsubscribe_token: string };

export interface Store {
  findByEmail(email: string): Promise<Subscriber | null>;
  /** Ny väntande rad. Finns adressen redan (samtidig anmälan) returneras den befintliga raden. */
  insertPending(row: { email: string; source: string | null; consent_text: string }): Promise<Subscriber>;
  markConfirmSent(id: string): Promise<void>;
  /** true om försöket ryms inom gränsen (max per fönster). Räknar försöket. */
  rateHit(bucket: string, max: number, windowSeconds: number): Promise<boolean>;
  confirm(token: string): Promise<"confirmed" | "already" | "missing">;
  /** Raderar raden helt. true om en rad togs bort. */
  unsubscribe(token: string): Promise<boolean>;
  countExpiredPending(days: number): Promise<number>;
  deleteExpiredPending(days: number): Promise<number>;
  countConfirmed(): Promise<number>;
  confirmedRecipients(): Promise<{ email: string; unsubscribe_token: string }[]>;
  lastSentAt(): Promise<Date | null>;
  /** Tar utskicksnyckeln. false om ett utskick med samma nyckel redan finns (skickas aldrig två gånger). */
  claimIssue(key: string, articleUrls: string[]): Promise<boolean>;
  finishIssue(key: string, status: "sent" | "failed", recipients: number): Promise<void>;
}

const COLS = "id,email,status,confirm_token,unsubscribe_token";

export function supabaseStore(url: string, serviceKey: string): Store {
  const db: SupabaseClient = createClient(url, serviceKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const T = "newsletter_subscribers";
  const fail = (what: string, error: { message: string } | null) => {
    if (error) throw new Error(`${what}: ${error.message}`);
  };
  const cutoff = (days: number) => new Date(Date.now() - days * 86400_000).toISOString();
  return {
    async findByEmail(email) {
      const { data, error } = await db.from(T).select(COLS).eq("email", email).maybeSingle();
      fail("findByEmail", error);
      return data as Subscriber | null;
    },
    async insertPending(row) {
      const { data, error } = await db.from(T).insert({ ...row, consent: true, status: "pending" }).select(COLS).single();
      if (error?.code === "23505") {
        const existing = await this.findByEmail(row.email);
        if (existing) return existing;
      }
      fail("insertPending", error);
      return data as Subscriber;
    },
    async markConfirmSent(id) {
      const { error } = await db.from(T).update({ confirm_sent_at: new Date().toISOString() }).eq("id", id);
      fail("markConfirmSent", error);
    },
    async rateHit(bucket, max, windowSeconds) {
      const { data, error } = await db.rpc("newsletter_rate_hit", { p_bucket: bucket, p_max: max, p_window_seconds: windowSeconds });
      fail("rateHit", error);
      return data === true;
    },
    async confirm(token) {
      const { data, error } = await db.from(T).update({ status: "confirmed", confirmed_at: new Date().toISOString() })
        .eq("confirm_token", token).eq("status", "pending").select("id");
      fail("confirm", error);
      if (data && data.length > 0) return "confirmed";
      const { data: row, error: e2 } = await db.from(T).select("status").eq("confirm_token", token).maybeSingle();
      fail("confirm lookup", e2);
      return row ? "already" : "missing";
    },
    async unsubscribe(token) {
      const { data, error } = await db.from(T).delete().eq("unsubscribe_token", token).select("id");
      fail("unsubscribe", error);
      return (data?.length ?? 0) > 0;
    },
    async countExpiredPending(days) {
      const { count, error } = await db.from(T).select("id", { count: "exact", head: true }).eq("status", "pending").lt("consent_at", cutoff(days));
      fail("countExpiredPending", error);
      return count ?? 0;
    },
    async deleteExpiredPending(days) {
      const { data, error } = await db.from(T).delete().eq("status", "pending").lt("consent_at", cutoff(days)).select("id");
      fail("deleteExpiredPending", error);
      return data?.length ?? 0;
    },
    async countConfirmed() {
      const { count, error } = await db.from(T).select("id", { count: "exact", head: true }).eq("status", "confirmed");
      fail("countConfirmed", error);
      return count ?? 0;
    },
    async confirmedRecipients() {
      const out: { email: string; unsubscribe_token: string }[] = [];
      const page = 1000;
      for (let from = 0; ; from += page) {
        const { data, error } = await db.from(T).select("email,unsubscribe_token").eq("status", "confirmed")
          .order("id").range(from, from + page - 1);
        fail("confirmedRecipients", error);
        out.push(...(data ?? []));
        if (!data || data.length < page) return out;
      }
    },
    async lastSentAt() {
      const { data, error } = await db.from("newsletter_sends").select("started_at").eq("status", "sent")
        .order("started_at", { ascending: false }).limit(1).maybeSingle();
      fail("lastSentAt", error);
      return data ? new Date(data.started_at) : null;
    },
    async claimIssue(key, articleUrls) {
      const { error } = await db.from("newsletter_sends").insert({ issue_key: key, status: "sending", article_urls: articleUrls });
      if (error?.code === "23505") return false;
      fail("claimIssue", error);
      return true;
    },
    async finishIssue(key, status, recipients) {
      const { error } = await db.from("newsletter_sends").update({ status, recipient_count: recipients, finished_at: new Date().toISOString() })
        .eq("issue_key", key);
      fail("finishIssue", error);
    },
  };
}
