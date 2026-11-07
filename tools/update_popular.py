"""Skriver data/popular.json: artiklar sorterade efter sidvisningar de senaste 7 dygnen (Cloudflare Web Analytics).

Kör:  CLOUDFLARE_ANALYTICS_TOKEN=... python tools/update_popular.py [--days 7] [--dry-run]
Token (API-token med Account Analytics: Read) läses bara från miljön och skrivs aldrig ut eller till fil.
build.py läser data/popular.json; saknas filen eller är den kort fylls listan på med de senaste artiklarna.
"""
import datetime as dt, json, os, re, sys, urllib.request

ACCOUNT = "6ae5d33e5a0671b0c9c53fbdd7d6c2a0"
HOST = "motorpuls.se"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUERY = """query($account: String!, $from: Date!, $to: Date!, $host: String!) {
  viewer { accounts(filter: {accountTag: $account}) {
    rumPageloadEventsAdaptiveGroups(limit: 1000, orderBy: [count_DESC],
      filter: {date_geq: $from, date_leq: $to, requestHost: $host, requestPath_like: "/artikel/%"}) {
      count dimensions { requestPath } } } } }"""

def main():
    days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 7
    token = os.environ.get("CLOUDFLARE_ANALYTICS_TOKEN")
    if not token: raise SystemExit("CLOUDFLARE_ANALYTICS_TOKEN saknas i miljön")
    to = dt.date.today(); frm = to - dt.timedelta(days=days - 1)
    body = json.dumps({"query": QUERY, "variables": {"account": ACCOUNT, "from": frm.isoformat(), "to": to.isoformat(), "host": HOST}}).encode()
    req = urllib.request.Request("https://api.cloudflare.com/client/v4/graphql", body,
                                 {"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r: res = json.load(r)
    if res.get("errors"): raise SystemExit("Cloudflare: " + "; ".join(e.get("message", "?") for e in res["errors"]))
    groups = res["data"]["viewer"]["accounts"][0]["rumPageloadEventsAdaptiveGroups"]
    views = {}
    for g in groups:  # /artikel/<slug>/ (med eller utan snedstreck, utan query)
        m = re.match(r"^/artikel/([a-z0-9-]+)/?(?:index\.html)?$", g["dimensions"]["requestPath"])
        if m: views[m.group(1)] = views.get(m.group(1), 0) + g["count"]
    ranked = sorted(views.items(), key=lambda kv: -kv[1])
    out = {"updated": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="minutes"),
           "source": f"Cloudflare Web Analytics, sidvisningar {frm.isoformat()} till {to.isoformat()}",
           "articles": [{"slug": s, "views": v} for s, v in ranked]}
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if "--dry-run" in sys.argv: print(text); return
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    open(os.path.join(ROOT, "data/popular.json"), "w", encoding="utf-8").write(text)
    print(f"data/popular.json: {len(ranked)} artiklar ({frm} till {to})")

if __name__ == "__main__":
    main()
