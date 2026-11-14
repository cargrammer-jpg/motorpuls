"""Skriver data/popular.json: artiklar sorterade efter sidvisningar.

Källan är självhostad Umami, med Cloudflare Web Analytics som reserv. Fönstret är
idag och de N-1 föregående dygnen (standard 7), med dygnsgränser i Europe/Stockholm.

Kör:  python tools/update_popular.py [--days 7] [--source auto|umami|cloudflare] [--dry-run]

Miljö (värdena skrivs aldrig ut):
  UMAMI_URL, UMAMI_USERNAME, UMAMI_PASSWORD
  CLOUDFLARE_ANALYTICS_TOKEN   (API-token med Account Analytics: Read)

--source auto (standard): Umami när alla tre UMAMI_* är satta, fönstret börjar
2026-11-07 eller senare (då spårningen började) och minst två /artikel/-slugs
kommer tillbaka. Annars Cloudflare, om token finns. Umami anropas inte när
fönstret ändå ska förkastas på grund av startdatumet.
--source umami: bara Umami. Datumgränsen och kravet på minst två slugs gäller inte.
--source cloudflare: bara Cloudflare.

build.py läser data/popular.json; saknas filen eller är den kort fylls listan på med de senaste artiklarna.
"""
import datetime as dt, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from zoneinfo import ZoneInfo

ACCOUNT = "6ae5d33e5a0671b0c9c53fbdd7d6c2a0"
HOST = "motorpuls.se"
UMAMI_WEBSITE_ID = "ffb8602c-4d57-4164-824c-9823ad5c42bb"
UMAMI_TRACKING_START = dt.date(2026, 11, 7)
STOCKHOLM = ZoneInfo("Europe/Stockholm")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT = 30
# /artikel/<slug>/ (med eller utan snedstreck, utan query, valfritt index.html)
SLUG_RE = re.compile(r"^/artikel/([a-z0-9-]+)/?(?:index\.html)?$")
QUERY = """query($account: String!, $from: Date!, $to: Date!, $host: String!) {
  viewer { accounts(filter: {accountTag: $account}) {
    rumPageloadEventsAdaptiveGroups(limit: 1000, orderBy: [count_DESC],
      filter: {date_geq: $from, date_leq: $to, requestHost: $host, requestPath_like: "/artikel/%"}) {
      count dimensions { requestPath } } } } }"""
SOURCES = ("auto", "umami", "cloudflare")


def stockholm_now():
    return dt.datetime.now(STOCKHOLM)


def epoch_ms(moment):
    utc = moment.astimezone(dt.timezone.utc)
    delta = utc - dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    return delta.days * 86_400_000 + delta.seconds * 1000 + delta.microseconds // 1000


def stockholm_window(days, now=None):
    if days < 1:
        raise SystemExit("--days kräver ett positivt heltal")
    moment = stockholm_now() if now is None else now
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=STOCKHOLM)
    else:
        moment = moment.astimezone(STOCKHOLM)
    to = moment.date()
    frm = to - dt.timedelta(days=days - 1)
    start = dt.datetime.combine(frm, dt.time.min, tzinfo=STOCKHOLM)
    # Umami använder SQL BETWEEN (inklusive). Sista millisekunden av idag tar med hela
    # dygnen i Stockholm och lämnar nästa midnatt utanför. Sommartid gör dygnet 23 eller 25 timmar.
    end = dt.datetime.combine(to + dt.timedelta(days=1), dt.time.min, tzinfo=STOCKHOLM) - dt.timedelta(milliseconds=1)
    return start, end, frm, to


def parse_args(argv):
    days, source, dry_run = 7, "auto", "--dry-run" in argv
    if "--days" in argv:
        index = argv.index("--days")
        if index + 1 >= len(argv):
            raise SystemExit("--days kräver ett positivt heltal")
        try:
            days = int(argv[index + 1])
        except ValueError:
            raise SystemExit("--days kräver ett positivt heltal")
        if days < 1:
            raise SystemExit("--days kräver ett positivt heltal")
    if "--source" in argv:
        index = argv.index("--source")
        if index + 1 >= len(argv):
            raise SystemExit("--source kräver auto, umami eller cloudflare")
        source = argv[index + 1]
        if source not in SOURCES:
            raise SystemExit("--source kräver auto, umami eller cloudflare")
    return days, source, dry_run


def aggregate(rows):
    views = {}
    for path, count in rows:
        if not isinstance(path, str):
            continue
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise SystemExit("Ogiltigt sidvisningsvärde")
        match = SLUG_RE.match(path)
        if not match:
            continue
        slug = match.group(1)
        views[slug] = views.get(slug, 0) + count
    return views


def as_count(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer():
        whole = int(value)
        return whole if whole >= 0 else None
    return None


def public_target(url):
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return f"{parts.scheme}://{host}{parts.path}"


def redact(text):
    for key in ("UMAMI_PASSWORD", "UMAMI_USERNAME", "CLOUDFLARE_ANALYTICS_TOKEN"):
        secret = os.environ.get(key, "")
        if len(secret) >= 4:
            text = text.replace(secret, "***")
    return text


def http_json(method, url, payload=None, headers=None, timeout=TIMEOUT):
    data = None
    hdrs = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read()
    except urllib.error.HTTPError as err:
        raise SystemExit(redact(f"{method} {public_target(url)}: HTTP {err.code}")) from None
    except urllib.error.URLError as err:
        raise SystemExit(redact(f"{method} {public_target(url)}: {err.reason}")) from None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SystemExit(redact(f"{method} {public_target(url)}: svaret är inte JSON")) from None


def api_url(base, suffix):
    parts = urllib.parse.urlsplit(base)
    path, _, query = suffix.partition("?")
    if not path.startswith("/"):
        path = "/" + path
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/") + path, query, ""))


def umami_settings():
    fields = {
        "UMAMI_URL": os.environ.get("UMAMI_URL", "").strip(),
        "UMAMI_USERNAME": os.environ.get("UMAMI_USERNAME", "").strip(),
        "UMAMI_PASSWORD": os.environ.get("UMAMI_PASSWORD", ""),
    }
    missing = [name for name, value in fields.items() if value == ""]
    if len(missing) == 3:
        return None
    if missing:
        raise SystemExit("Ofullständig Umami-konfiguration, saknas: " + ", ".join(missing))
    parts = urllib.parse.urlsplit(fields["UMAMI_URL"])
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise SystemExit("UMAMI_URL måste vara en http(s)-adress")
    if parts.username is not None or parts.password is not None:
        raise SystemExit("UMAMI_URL får inte innehålla användarnamn eller lösenord")
    return fields


def fetch_umami(cfg, start, end):
    login = http_json("POST", api_url(cfg["UMAMI_URL"], "/api/auth/login"),
                      {"username": cfg["UMAMI_USERNAME"], "password": cfg["UMAMI_PASSWORD"]})
    token = login.get("token") if isinstance(login, dict) else None
    if not isinstance(token, str) or not token.strip():
        raise SystemExit("Umami: inloggning gav inget token")
    query = urllib.parse.urlencode([
        ("type", "path"),
        ("startAt", str(epoch_ms(start))),
        ("endAt", str(epoch_ms(end))),
        ("limit", "1000"),
    ])
    rows = http_json(
        "GET",
        api_url(cfg["UMAMI_URL"], f"/api/websites/{UMAMI_WEBSITE_ID}/metrics?{query}"),
        headers={"Authorization": "Bearer " + token.strip()},
    )
    if not isinstance(rows, list):
        raise SystemExit("Umami: oväntat svarsformat")
    pairs = []
    for row in rows:
        if not isinstance(row, dict) or "x" not in row or "y" not in row:
            raise SystemExit("Umami: oväntat svarsformat")
        path, count = row["x"], as_count(row["y"])
        if path is None:
            continue
        if not isinstance(path, str) or count is None:
            raise SystemExit("Umami: oväntat svarsformat")
        pairs.append((path, count))
    return aggregate(pairs)


def fetch_cloudflare(frm, to, reason=None):
    token = os.environ.get("CLOUDFLARE_ANALYTICS_TOKEN", "").strip()
    if not token:
        if reason:
            raise SystemExit(f"{reason} CLOUDFLARE_ANALYTICS_TOKEN saknas i miljön.")
        raise SystemExit("CLOUDFLARE_ANALYTICS_TOKEN saknas i miljön")
    res = http_json(
        "POST",
        "https://api.cloudflare.com/client/v4/graphql",
        {"query": QUERY, "variables": {"account": ACCOUNT, "from": frm.isoformat(), "to": to.isoformat(), "host": HOST}},
        {"Authorization": "Bearer " + token},
    )
    if not isinstance(res, dict):
        raise SystemExit("Cloudflare: oväntat svarsformat")
    errors = res.get("errors")
    if errors:
        messages = [err.get("message", "?") if isinstance(err, dict) else "?" for err in errors]
        raise SystemExit(redact("Cloudflare: " + "; ".join(messages)))
    try:
        groups = res["data"]["viewer"]["accounts"][0]["rumPageloadEventsAdaptiveGroups"]
    except (KeyError, IndexError, TypeError):
        raise SystemExit("Cloudflare: oväntat svarsformat")
    if not isinstance(groups, list):
        raise SystemExit("Cloudflare: oväntat svarsformat")
    pairs = []
    for group in groups:
        try:
            path, count = group["dimensions"]["requestPath"], as_count(group["count"])
        except (KeyError, TypeError):
            raise SystemExit("Cloudflare: oväntat svarsformat")
        if not isinstance(path, str) or count is None:
            raise SystemExit("Cloudflare: oväntat svarsformat")
        pairs.append((path, count))
    views = aggregate(pairs)
    if reason:
        print(f"{reason} Cloudflare används.", file=sys.stderr)
    return views


def article_noun(count):
    return "artikelsida" if count == 1 else "artikelsidor"


def load_ranking(source, start, end, frm, to):
    if source == "cloudflare":
        return "cloudflare", fetch_cloudflare(frm, to)
    umami = umami_settings()
    if source == "umami":
        if umami is None:
            raise SystemExit("UMAMI_URL, UMAMI_USERNAME och UMAMI_PASSWORD saknas i miljön")
        return "umami", fetch_umami(umami, start, end)
    if umami is not None and frm >= UMAMI_TRACKING_START:
        views = fetch_umami(umami, start, end)
        if len(views) >= 2:
            return "umami", views
        reason = f"Umami: {len(views)} {article_noun(len(views))}."
        return "cloudflare", fetch_cloudflare(frm, to, reason)
    if umami is not None:
        reason = f"Umami: fönstret börjar {frm.isoformat()}, före {UMAMI_TRACKING_START.isoformat()}."
        return "cloudflare", fetch_cloudflare(frm, to, reason)
    return "cloudflare", fetch_cloudflare(frm, to)


def render(source, views, updated):
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=STOCKHOLM)
    else:
        updated = updated.astimezone(STOCKHOLM)
    ranked = sorted(views.items(), key=lambda item: -item[1])
    document = {
        "updated": updated.isoformat(timespec="minutes"),
        "source": source,
        "articles": [{"slug": slug, "views": count} for slug, count in ranked],
    }
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def main(argv=None):
    days, source, dry_run = parse_args(sys.argv[1:] if argv is None else argv)
    start, end, frm, to = stockholm_window(days)
    chosen, views = load_ranking(source, start, end, frm, to)
    text = render(chosen, views, stockholm_now())
    if dry_run:
        sys.stdout.write(text)
        return
    path = os.path.join(ROOT, "data", "popular.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"data/popular.json: {len(views)} artiklar ({frm.isoformat()} till {to.isoformat()}, {chosen})")


if __name__ == "__main__":
    main()
