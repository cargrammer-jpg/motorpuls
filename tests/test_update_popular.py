"""Tester för tools/update_popular.py. Stdlib only.

Kör: python -m unittest tests/test_update_popular.py
"""
import datetime as dt
import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from email.message import EmailMessage
from unittest import mock
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "update_popular", os.path.join(ROOT, "tools", "update_popular.py")
)
up = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(up)

STOCKHOLM = ZoneInfo("Europe/Stockholm")
ENV_KEYS = ("UMAMI_URL", "UMAMI_USERNAME", "UMAMI_PASSWORD", "CLOUDFLARE_ANALYTICS_TOKEN")
PASSWORD = "p@ss word/should-not-leak"
USERNAME = "umami-user-name"
TOKEN = "bearer-token-value"
CF_TOKEN = "cf-analytics-token"
SECRETS = (PASSWORD, USERNAME, TOKEN, CF_TOKEN)
ELIGIBLE = dt.datetime(2026, 11, 13, 15, 4, 30, tzinfo=STOCKHOLM)  # 7 dygn börjar 2026-11-07
EARLY = dt.datetime(2026, 11, 7, 15, 0, tzinfo=STOCKHOLM)  # 7 dygn börjar 2026-11-01
DAY_BEFORE = dt.datetime(2026, 11, 12, 12, 0, tzinfo=STOCKHOLM)  # 7 dygn börjar 2026-11-06

EXPECTED_QUERY = """query($account: String!, $from: Date!, $to: Date!, $host: String!) {
  viewer { accounts(filter: {accountTag: $account}) {
    rumPageloadEventsAdaptiveGroups(limit: 1000, orderBy: [count_DESC],
      filter: {date_geq: $from, date_leq: $to, requestHost: $host, requestPath_like: "/artikel/%"}) {
      count dimensions { requestPath } } } } }"""


def epoch_ms(moment):
    utc = moment.astimezone(dt.timezone.utc)
    delta = utc - dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
    return delta.days * 86_400_000 + delta.seconds * 1000 + delta.microseconds // 1000


def umami_env(**extra):
    env = {
        "UMAMI_URL": "https://stats.example",
        "UMAMI_USERNAME": USERNAME,
        "UMAMI_PASSWORD": PASSWORD,
    }
    env.update(extra)
    return env


def cf_body(groups):
    return {"data": {"viewer": {"accounts": [{"rumPageloadEventsAdaptiveGroups": groups}]}}}


def cf_group(path, count):
    return {"count": count, "dimensions": {"requestPath": path}}


class _Body:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeHTTP:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []
        self._patch = None

    def __enter__(self):
        def urlopen(req, timeout=30):
            self.calls.append((req, timeout))
            result = self.handler(req, timeout)
            if isinstance(result, BaseException):
                raise result
            body = result if isinstance(result, bytes) else json.dumps(result).encode("utf-8")
            return _Body(body)

        self._patch = mock.patch("urllib.request.urlopen", urlopen)
        self._patch.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._patch.stop()
        return False


def http_error(req, code):
    payload = json.dumps({"password": PASSWORD, "token": TOKEN, "username": USERNAME}).encode()
    return urllib.error.HTTPError(req.full_url, code, "nope", EmailMessage(), io.BytesIO(payload))


class UpdatePopularTest(unittest.TestCase):
    def setUp(self):
        self._saved = {key: os.environ.get(key) for key in ENV_KEYS}
        for key in ENV_KEYS:
            os.environ.pop(key, None)
        self.addCleanup(self._restore_env)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = mock.patch.object(up, "ROOT", self.tmp.name)
        self.root.start()
        self.addCleanup(self.root.stop)
        self.blocked = mock.patch("urllib.request.urlopen", self._blocked_http)
        self.blocked.start()
        self.addCleanup(self.blocked.stop)

    def _restore_env(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    @staticmethod
    def _blocked_http(req, timeout=30):
        raise AssertionError("oväntat HTTP-anrop")

    def assert_no_secrets(self, *chunks):
        blob = "\n".join(chunk for chunk in chunks if chunk is not None)
        for secret in SECRETS:
            self.assertNotIn(secret, blob)

    def written(self):
        path = os.path.join(self.tmp.name, "data", "popular.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def run_main(self, argv, handler=None, env=None, now=None):
        if env:
            os.environ.update(env)
        out, err = io.StringIO(), io.StringIO()
        clock = mock.patch.object(up, "stockholm_now", return_value=now or ELIGIBLE)
        clock.start()
        http = FakeHTTP(handler) if handler else None
        if http:
            http.__enter__()
        try:
            with redirect_stdout(out), redirect_stderr(err):
                up.main(argv)
        finally:
            if http:
                http.__exit__(None, None, None)
            clock.stop()
        return out.getvalue(), err.getvalue(), http.calls if http else []

    def exits(self, argv, handler=None, env=None, now=None):
        with self.assertRaises(SystemExit) as caught:
            self.run_main(argv, handler=handler, env=env, now=now)
        return str(caught.exception)

    def test_window_uses_stockholm_date_across_utc_midnight(self):
        now = dt.datetime(2026, 11, 13, 23, 30, tzinfo=dt.timezone.utc)  # 00:30 den 14:e i Stockholm
        start, end, frm, to = up.stockholm_window(1, now)
        self.assertEqual((frm, to), (dt.date(2026, 11, 14), dt.date(2026, 11, 14)))
        self.assertEqual(start, dt.datetime(2026, 11, 14, 0, 0, tzinfo=STOCKHOLM))
        nxt = dt.datetime(2026, 11, 15, 0, 0, tzinfo=STOCKHOLM)
        self.assertEqual(end, nxt - dt.timedelta(milliseconds=1))

    def test_naive_now_is_stockholm(self):
        start, end, frm, to = up.stockholm_window(1, dt.datetime(2026, 11, 13, 23, 30))
        self.assertEqual(to, dt.date(2026, 11, 13))
        self.assertEqual(start.utcoffset(), dt.timedelta(hours=1))
        self.assertEqual(end, dt.datetime(2026, 11, 14, 0, 0, tzinfo=STOCKHOLM) - dt.timedelta(milliseconds=1))

    def test_seven_day_window_ends_at_last_millisecond_of_today(self):
        start, end, frm, to = up.stockholm_window(7, ELIGIBLE)
        self.assertEqual(frm, dt.date(2026, 11, 7))
        self.assertEqual(to, dt.date(2026, 11, 13))
        self.assertEqual(start, dt.datetime(2026, 11, 7, 0, 0, tzinfo=STOCKHOLM))
        nxt = dt.datetime(2026, 11, 14, 0, 0, tzinfo=STOCKHOLM)
        self.assertEqual(end, nxt - dt.timedelta(milliseconds=1))
        self.assertEqual(epoch_ms(end) - epoch_ms(start), 7 * 24 * 60 * 60 * 1000 - 1)
        self.assertNotEqual(end, ELIGIBLE)
        self.assertNotEqual(end, nxt)

    def test_dst_spring_forward_day_is_23_hours(self):
        now = dt.datetime(2026, 3, 29, 12, 0, tzinfo=STOCKHOLM)
        start, end, frm, to = up.stockholm_window(1, now)
        self.assertEqual((frm, to), (dt.date(2026, 3, 29), dt.date(2026, 3, 29)))
        nxt = dt.datetime(2026, 3, 30, 0, 0, tzinfo=STOCKHOLM)
        self.assertEqual(end, nxt - dt.timedelta(milliseconds=1))
        self.assertEqual(epoch_ms(end) - epoch_ms(start), 23 * 60 * 60 * 1000 - 1)

    def test_dst_fall_back_day_is_25_hours(self):
        now = dt.datetime(2026, 10, 25, 12, 0, tzinfo=STOCKHOLM)
        start, end, frm, to = up.stockholm_window(1, now)
        self.assertEqual((frm, to), (dt.date(2026, 10, 25), dt.date(2026, 10, 25)))
        nxt = dt.datetime(2026, 10, 26, 0, 0, tzinfo=STOCKHOLM)
        self.assertEqual(end, nxt - dt.timedelta(milliseconds=1))
        self.assertEqual(epoch_ms(end) - epoch_ms(start), 25 * 60 * 60 * 1000 - 1)

    def test_slug_regex_and_aggregation(self):
        self.assertEqual(up.SLUG_RE.pattern, r"^/artikel/([a-z0-9-]+)/?(?:index\.html)?$")
        views = up.aggregate([
            ("/artikel/alfa/", 3),
            ("/artikel/alfa/index.html", 4),
            ("/artikel/alfa", 1),
            ("/artikel/beta/?q=1", 9),
            ("/Artikel/beta/", 5),
            ("/om/", 8),
            ("/artikel/", 2),
            ("/artikel/gamma", 2),
        ])
        self.assertEqual(views, {"alfa": 8, "gamma": 2})
        with self.assertRaises(SystemExit):
            up.aggregate([("/artikel/alfa/", -1)])

    def test_cloudflare_query_is_unchanged(self):
        self.assertEqual(up.QUERY, EXPECTED_QUERY)
        self.assertEqual(up.ACCOUNT, "6ae5d33e5a0671b0c9c53fbdd7d6c2a0")
        self.assertEqual(up.HOST, "motorpuls.se")
        self.assertEqual(up.UMAMI_WEBSITE_ID, "ffb8602c-4d57-4164-824c-9823ad5c42bb")
        self.assertEqual(up.UMAMI_TRACKING_START, dt.date(2026, 11, 7))

    def _router(self, umami_rows, groups):
        def handler(req, timeout):
            self.assertEqual(timeout, 30)
            url = req.full_url
            if url.split("?", 1)[0].endswith("/api/auth/login"):
                self.assertEqual(req.get_method(), "POST")
                self.assertEqual(json.loads(req.data.decode()), {"username": USERNAME, "password": PASSWORD})
                return {"token": TOKEN}
            if "/api/websites/" in url and "/metrics?" in url:
                self.assertEqual(req.get_method(), "GET")
                self.assertIsNone(req.data)
                self.assertEqual(req.get_header("Authorization"), "Bearer " + TOKEN)
                return umami_rows
            if url.startswith("https://api.cloudflare.com/client/v4/graphql"):
                self.assertEqual(req.get_method(), "POST")
                self.assertEqual(req.get_header("Authorization"), "Bearer " + CF_TOKEN)
                return cf_body(groups)
            raise AssertionError(url)

        return handler

    def test_default_auto_uses_umami_when_window_starts_on_tracking_day(self):
        rows = [
            {"x": "/artikel/beta/", "y": 3},
            {"x": "/artikel/alfa/", "y": 3},
            {"x": "/artikel/alfa/index.html", "y": 4},
            {"x": None, "y": 100},
            {"x": "/om/", "y": 50},
            {"x": "/artikel/gamma/", "y": 4.0},
        ]
        out, err, calls = self.run_main(
            ["--dry-run"],
            handler=self._router(rows, [cf_group("/artikel/fran-cf/", 99)]),
            env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN),
        )
        self.assertEqual(err, "")
        self.assertEqual(len(calls), 2)
        metrics = calls[1][0].full_url
        self.assertIn("/api/websites/ffb8602c-4d57-4164-824c-9823ad5c42bb/metrics?", metrics)
        query = urllib.parse.urlsplit(metrics).query
        params = urllib.parse.parse_qs(query)
        start, end, frm, to = up.stockholm_window(7, ELIGIBLE)
        self.assertEqual(params, {
            "type": ["path"],
            "startAt": [str(epoch_ms(start))],
            "endAt": [str(epoch_ms(end))],
            "limit": ["1000"],
        })
        self.assertNotEqual(params["endAt"], [str(epoch_ms(end + dt.timedelta(milliseconds=1)))])
        payload = json.loads(out)
        self.assertEqual(payload["source"], "umami")
        self.assertEqual(payload["updated"], "2026-11-13T15:04+01:00")
        self.assertEqual(payload["articles"], [
            {"slug": "alfa", "views": 7},
            {"slug": "gamma", "views": 4},
            {"slug": "beta", "views": 3},
        ])
        self.assertTrue(out.endswith("\n"))
        self.assertEqual(out, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        self.assertIsNone(self.written())
        self.assert_no_secrets(out, err, metrics, calls[0][0].full_url)

    def test_explicit_auto_matches_default_source_choice(self):
        out, err, calls = self.run_main(
            ["--source", "auto", "--dry-run"],
            handler=self._router(
                [{"x": "/artikel/a/", "y": 2}, {"x": "/artikel/b/", "y": 1}],
                [cf_group("/artikel/fran-cf/", 9)],
            ),
            env=umami_env(),
        )
        self.assertEqual(json.loads(out)["source"], "umami")
        self.assertEqual(err, "")
        self.assertEqual(len(calls), 2)

    def test_umami_request_uses_dst_fall_back_boundaries(self):
        now = dt.datetime(2026, 10, 25, 18, 0, tzinfo=STOCKHOLM)
        out, err, calls = self.run_main(
            ["--source", "umami", "--days", "1", "--dry-run"],
            handler=self._router([{"x": "/artikel/a/", "y": 1}], []),
            env=umami_env(),
            now=now,
        )
        params = urllib.parse.parse_qs(urllib.parse.urlsplit(calls[1][0].full_url).query)
        start, end, frm, to = up.stockholm_window(1, now)
        self.assertEqual(params["startAt"], [str(epoch_ms(start))])
        self.assertEqual(params["endAt"], [str(epoch_ms(end))])
        self.assertEqual(epoch_ms(end) - epoch_ms(start), 25 * 60 * 60 * 1000 - 1)
        self.assertEqual(json.loads(out)["source"], "umami")
        self.assertEqual(json.loads(out)["articles"], [{"slug": "a", "views": 1}])
        self.assertEqual(err, "")

    def test_trailing_slash_on_umami_url(self):
        out, _, calls = self.run_main(
            ["--source", "umami", "--days", "1", "--dry-run"],
            handler=self._router(
                [{"x": "/artikel/a/", "y": 1}, {"x": "/artikel/b/", "y": 1}],
                [],
            ),
            env=umami_env(UMAMI_URL="https://stats.example/"),
        )
        self.assertEqual(calls[0][0].full_url, "https://stats.example/api/auth/login")
        self.assertTrue(calls[1][0].full_url.startswith(
            "https://stats.example/api/websites/ffb8602c-4d57-4164-824c-9823ad5c42bb/metrics?"
        ))
        self.assertEqual(json.loads(out)["source"], "umami")

    def test_auto_falls_back_when_window_starts_before_tracking(self):
        def handler(req, timeout):
            self.assertTrue(req.full_url.startswith("https://api.cloudflare.com/"))
            body = json.loads(req.data.decode())
            self.assertEqual(body["query"], EXPECTED_QUERY)
            self.assertEqual(body["variables"], {
                "account": "6ae5d33e5a0671b0c9c53fbdd7d6c2a0",
                "from": "2026-11-01",
                "to": "2026-11-07",
                "host": "motorpuls.se",
            })
            return cf_body([cf_group("/artikel/fran-cf/", 4), cf_group("/artikel/annan/", 1)])

        out, err, calls = self.run_main(
            ["--days", "7", "--dry-run"],
            handler=handler,
            env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN),
            now=EARLY,
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(err, "Umami: fönstret börjar 2026-11-01, före 2026-11-07. Cloudflare används.\n")
        payload = json.loads(out)
        self.assertEqual(payload["source"], "cloudflare")
        self.assertEqual(payload["articles"], [
            {"slug": "fran-cf", "views": 4},
            {"slug": "annan", "views": 1},
        ])
        self.assert_no_secrets(out, err)

    def test_auto_falls_back_day_before_full_umami_window(self):
        seen = []

        def handler(req, timeout):
            seen.append(req.full_url)
            if "cloudflare.com" in req.full_url:
                body = json.loads(req.data.decode())
                self.assertEqual(body["variables"]["from"], "2026-11-06")
                self.assertEqual(body["variables"]["to"], "2026-11-12")
                return cf_body([cf_group("/artikel/fran-cf/", 2)])
            raise AssertionError("Umami ska inte anropas när fönstret börjar före 2026-11-07")

        out, err, _ = self.run_main(
            ["--dry-run"],
            handler=handler,
            env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN),
            now=DAY_BEFORE,
        )
        self.assertEqual(json.loads(out)["source"], "cloudflare")
        self.assertIn("2026-11-06", err)
        self.assertEqual(seen, ["https://api.cloudflare.com/client/v4/graphql"])

    def test_auto_one_day_on_first_tracking_day_uses_umami(self):
        out, err, calls = self.run_main(
            ["--days", "1", "--dry-run"],
            handler=self._router(
                [{"x": "/artikel/a/", "y": 2}, {"x": "/artikel/b/", "y": 1}],
                [cf_group("/artikel/fran-cf/", 9)],
            ),
            env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN),
            now=EARLY,
        )
        self.assertEqual(err, "")
        self.assertEqual(len(calls), 2)
        self.assertEqual(json.loads(out)["source"], "umami")
        params = urllib.parse.parse_qs(urllib.parse.urlsplit(calls[1][0].full_url).query)
        start, end, _, _ = up.stockholm_window(1, EARLY)
        self.assertEqual(params["startAt"], [str(epoch_ms(start))])
        self.assertEqual(params["endAt"], [str(epoch_ms(end))])

    def test_auto_falls_back_when_fewer_than_two_slugs(self):
        out, err, calls = self.run_main(
            ["--dry-run"],
            handler=self._router(
                [{"x": "/artikel/ensam/", "y": 5}, {"x": "/artikel/ensam/index.html", "y": 1}, {"x": "/om/", "y": 9}],
                [cf_group("/artikel/fran-cf/", 3), cf_group("/artikel/annan/", 1)],
            ),
            env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN),
        )
        self.assertEqual(len(calls), 3)
        self.assertEqual(err, "Umami: 1 artikelsida. Cloudflare används.\n")
        payload = json.loads(out)
        self.assertEqual(payload["source"], "cloudflare")
        self.assertEqual([item["slug"] for item in payload["articles"]], ["fran-cf", "annan"])
        self.assert_no_secrets(out, err)

    def test_auto_falls_back_when_umami_returns_no_articles(self):
        _, err, calls = self.run_main(
            ["--dry-run"],
            handler=self._router([], [cf_group("/artikel/a/", 1), cf_group("/artikel/b/", 1)]),
            env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN),
        )
        self.assertEqual(len(calls), 3)
        self.assertEqual(err, "Umami: 0 artikelsidor. Cloudflare används.\n")

    def test_exactly_two_slugs_stay_on_umami(self):
        out, err, calls = self.run_main(
            ["--dry-run"],
            handler=self._router(
                [{"x": "/artikel/a/", "y": 1}, {"x": "/artikel/b", "y": 1}],
                [cf_group("/artikel/fran-cf/", 100)],
            ),
            env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN),
        )
        self.assertEqual(err, "")
        self.assertEqual(len(calls), 2)
        self.assertEqual(json.loads(out)["source"], "umami")
        self.assertEqual(json.loads(out)["articles"], [
            {"slug": "a", "views": 1},
            {"slug": "b", "views": 1},
        ])

    def test_auto_without_umami_uses_cloudflare(self):
        out, err, calls = self.run_main(
            ["--days", "1", "--dry-run"],
            handler=self._router([], [cf_group("/artikel/bara-cf/", 6)]),
            env={"CLOUDFLARE_ANALYTICS_TOKEN": CF_TOKEN},
        )
        self.assertEqual(err, "")
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][0].full_url.startswith("https://api.cloudflare.com/"))
        body = json.loads(calls[0][0].data.decode())
        self.assertEqual(body["variables"]["from"], "2026-11-13")
        self.assertEqual(body["variables"]["to"], "2026-11-13")
        self.assertEqual(json.loads(out)["source"], "cloudflare")
        self.assertEqual(json.loads(out)["articles"], [{"slug": "bara-cf", "views": 6}])

    def test_cloudflare_dates_follow_injected_stockholm_clock(self):
        now = dt.datetime(2026, 11, 13, 23, 30, tzinfo=dt.timezone.utc)

        def handler(req, timeout):
            body = json.loads(req.data.decode())
            self.assertEqual(body["variables"]["from"], "2026-11-14")
            self.assertEqual(body["variables"]["to"], "2026-11-14")
            return cf_body([cf_group("/artikel/a/", 1)])

        out, _, _ = self.run_main(
            ["--source", "cloudflare", "--days", "1", "--dry-run"],
            handler=handler,
            env={"CLOUDFLARE_ANALYTICS_TOKEN": CF_TOKEN},
            now=now,
        )
        self.assertEqual(json.loads(out)["updated"], "2026-11-14T00:30+01:00")

    def test_fallback_without_cloudflare_token_exits_and_writes_nothing(self):
        message = self.exits(
            [],
            handler=self._router([{"x": "/artikel/ensam/", "y": 1}], []),
            env=umami_env(),
        )
        self.assertEqual(message, "Umami: 1 artikelsida. CLOUDFLARE_ANALYTICS_TOKEN saknas i miljön.")
        self.assert_no_secrets(message)
        self.assertIsNone(self.written())

    def test_date_fallback_without_cloudflare_token_exits(self):
        message = self.exits([], env=umami_env(), now=EARLY)
        self.assertEqual(
            message,
            "Umami: fönstret börjar 2026-11-01, före 2026-11-07. CLOUDFLARE_ANALYTICS_TOKEN saknas i miljön.",
        )
        self.assert_no_secrets(message)

    def test_auto_without_any_credentials_exits(self):
        message = self.exits([])
        self.assertEqual(message, "CLOUDFLARE_ANALYTICS_TOKEN saknas i miljön")
        self.assert_no_secrets(message)

    def test_partial_umami_env_exits_before_http(self):
        message = self.exits([], env={"UMAMI_URL": "https://stats.example", "UMAMI_USERNAME": USERNAME})
        self.assertEqual(message, "Ofullständig Umami-konfiguration, saknas: UMAMI_PASSWORD")
        self.assert_no_secrets(message)
        self.assertIsNone(self.written())

    def test_partial_umami_lists_missing_names_in_order(self):
        message = self.exits([], env={"UMAMI_PASSWORD": PASSWORD})
        self.assertEqual(message, "Ofullständig Umami-konfiguration, saknas: UMAMI_URL, UMAMI_USERNAME")
        self.assertNotIn(PASSWORD, message)

    def test_source_cloudflare_ignores_partial_umami_env(self):
        out, err, calls = self.run_main(
            ["--source", "cloudflare", "--dry-run"],
            handler=self._router([], [cf_group("/artikel/a/", 2), cf_group("/artikel/b/", 1)]),
            env={"UMAMI_URL": "https://user:secret@stats.example", "CLOUDFLARE_ANALYTICS_TOKEN": CF_TOKEN},
        )
        self.assertEqual(err, "")
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(out)["source"], "cloudflare")
        self.assert_no_secrets(out, err)

    def test_source_umami_before_tracking_does_not_fall_back(self):
        out, err, calls = self.run_main(
            ["--source", "umami", "--dry-run"],
            handler=self._router([{"x": "/artikel/tidig/", "y": 2}], [cf_group("/artikel/fran-cf/", 9)]),
            env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN),
            now=EARLY,
        )
        self.assertEqual(err, "")
        self.assertEqual(len(calls), 2)
        payload = json.loads(out)
        self.assertEqual(payload["source"], "umami")
        self.assertEqual(payload["articles"], [{"slug": "tidig", "views": 2}])

    def test_source_umami_with_one_slug_does_not_fall_back(self):
        out, err, calls = self.run_main(
            ["--source", "umami", "--dry-run"],
            handler=self._router([{"x": "/artikel/ensam/", "y": 2}], [cf_group("/artikel/fran-cf/", 9)]),
            env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN),
        )
        self.assertEqual(err, "")
        self.assertEqual(len(calls), 2)
        self.assertEqual(json.loads(out)["articles"], [{"slug": "ensam", "views": 2}])

    def test_source_umami_missing_env_exits(self):
        message = self.exits(["--source", "umami"], env={"CLOUDFLARE_ANALYTICS_TOKEN": CF_TOKEN})
        self.assertEqual(message, "UMAMI_URL, UMAMI_USERNAME och UMAMI_PASSWORD saknas i miljön")
        self.assert_no_secrets(message)

    def test_source_cloudflare_missing_token_exits(self):
        message = self.exits(["--source", "cloudflare"], env=umami_env())
        self.assertEqual(message, "CLOUDFLARE_ANALYTICS_TOKEN saknas i miljön")

    def test_invalid_source_and_days(self):
        self.assertEqual(self.exits(["--source", "nope"]), "--source kräver auto, umami eller cloudflare")
        self.assertEqual(self.exits(["--source"]), "--source kräver auto, umami eller cloudflare")
        self.assertEqual(self.exits(["--source", "Umami"]), "--source kräver auto, umami eller cloudflare")
        self.assertEqual(self.exits(["--days", "0"]), "--days kräver ett positivt heltal")
        self.assertEqual(self.exits(["--days", "-3"]), "--days kräver ett positivt heltal")
        self.assertEqual(self.exits(["--days", "två"]), "--days kräver ett positivt heltal")
        self.assertEqual(self.exits(["--days"]), "--days kräver ett positivt heltal")

    def test_flag_order_and_cloudflare_slug_sum(self):
        out, _, calls = self.run_main(
            ["--dry-run", "--days", "3", "--source", "cloudflare"],
            handler=self._router([], [
                cf_group("/artikel/alfa/", 2),
                cf_group("/artikel/alfa/index.html", 5),
                cf_group("/artikel/beta", 4),
                cf_group("/feed.xml", 100),
            ]),
            env={"CLOUDFLARE_ANALYTICS_TOKEN": CF_TOKEN},
        )
        body = json.loads(calls[0][0].data.decode())
        self.assertEqual(body["variables"]["from"], "2026-11-11")
        self.assertEqual(body["variables"]["to"], "2026-11-13")
        self.assertEqual(json.loads(out)["articles"], [
            {"slug": "alfa", "views": 7},
            {"slug": "beta", "views": 4},
        ])

    def test_umami_url_must_be_http_and_without_userinfo(self):
        self.assertEqual(
            self.exits(["--source", "umami"], env=umami_env(UMAMI_URL="stats.example")),
            "UMAMI_URL måste vara en http(s)-adress",
        )
        message = self.exits(
            ["--source", "umami"],
            env=umami_env(UMAMI_URL="https://user:should-not-leak@stats.example"),
        )
        self.assertEqual(message, "UMAMI_URL får inte innehålla användarnamn eller lösenord")
        self.assertNotIn("should-not-leak", message)
        self.assertNotIn("user:", message)

    def test_login_without_token_exits_before_metrics(self):
        def handler(req, timeout):
            self.assertTrue(req.full_url.endswith("/api/auth/login"))
            return {"user": USERNAME}

        message = self.exits(["--source", "umami"], handler=handler, env=umami_env())
        self.assertEqual(message, "Umami: inloggning gav inget token")
        self.assert_no_secrets(message)

    def test_umami_http_error_does_not_fall_back_or_leak(self):
        def handler(req, timeout):
            if req.full_url.endswith("/api/auth/login"):
                raise http_error(req, 401)
            raise AssertionError("metrics")

        message = self.exits(
            ["--source", "auto"],
            handler=handler,
            env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN),
        )
        self.assertEqual(message, "POST https://stats.example/api/auth/login: HTTP 401")
        self.assert_no_secrets(message)
        self.assertIsNone(self.written())

    def test_metrics_http_error_does_not_fall_back(self):
        def handler(req, timeout):
            if req.full_url.endswith("/api/auth/login"):
                return {"token": TOKEN}
            raise http_error(req, 500)

        message = self.exits([], handler=handler, env=umami_env(CLOUDFLARE_ANALYTICS_TOKEN=CF_TOKEN))
        self.assertEqual(
            message,
            "GET https://stats.example/api/websites/ffb8602c-4d57-4164-824c-9823ad5c42bb/metrics: HTTP 500",
        )
        self.assert_no_secrets(message)

    def test_umami_bad_shape_exits(self):
        message = self.exits(
            ["--source", "umami"],
            handler=self._router({"pageviews": []}, []),
            env=umami_env(),
        )
        self.assertEqual(message, "Umami: oväntat svarsformat")
        message = self.exits(
            ["--source", "umami"],
            handler=self._router([{"x": "/artikel/a/", "y": 1.5}], []),
            env=umami_env(),
        )
        self.assertEqual(message, "Umami: oväntat svarsformat")

    def test_cloudflare_error_has_no_token(self):
        def handler(req, timeout):
            return {"errors": [{"message": "boom"}, "något annat"]}

        message = self.exits(["--source", "cloudflare"], handler=handler, env={"CLOUDFLARE_ANALYTICS_TOKEN": CF_TOKEN})
        self.assertEqual(message, "Cloudflare: boom; ?")
        self.assertNotIn(CF_TOKEN, message)

    def test_cloudflare_error_redacts_token(self):
        def handler(req, timeout):
            return {"errors": [{"message": "ogiltig token " + CF_TOKEN}]}

        message = self.exits(["--source", "cloudflare"], handler=handler, env={"CLOUDFLARE_ANALYTICS_TOKEN": CF_TOKEN})
        self.assertEqual(message, "Cloudflare: ogiltig token ***")
        self.assertNotIn(CF_TOKEN, message)

    def test_cloudflare_bad_shape_exits(self):
        def handler(req, timeout):
            return {"data": {"viewer": {"accounts": []}}}

        message = self.exits(["--source", "cloudflare"], handler=handler, env={"CLOUDFLARE_ANALYTICS_TOKEN": CF_TOKEN})
        self.assertEqual(message, "Cloudflare: oväntat svarsformat")

    def test_network_error_hides_url_userinfo(self):
        # userinfo avvisas innan anrop; nätverksfel ska ändå inte ta med query eller lösenord
        def handler(req, timeout):
            raise urllib.error.URLError("timed out")

        message = self.exits(["--source", "umami"], handler=handler, env=umami_env())
        self.assertEqual(message, "POST https://stats.example/api/auth/login: timed out")
        self.assert_no_secrets(message)

    def test_write_popular_json_and_summary(self):
        out, err, _ = self.run_main(
            ["--source", "umami"],
            handler=self._router(
                [{"x": "/artikel/alfa/", "y": 2}, {"x": "/artikel/beta/", "y": 9}],
                [],
            ),
            env=umami_env(),
            now=ELIGIBLE,
        )
        self.assertEqual(out, "data/popular.json: 2 artiklar (2026-11-07 till 2026-11-13, umami)\n")
        self.assertEqual(err, "")
        text = self.written()
        payload = json.loads(text)
        self.assertEqual(payload["source"], "umami")
        self.assertEqual(payload["articles"][0], {"slug": "beta", "views": 9})
        self.assertEqual(text, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        self.assert_no_secrets(out, err, text)

    def test_dry_run_does_not_write(self):
        out, _, _ = self.run_main(
            ["--dry-run", "--source", "cloudflare"],
            handler=self._router([], [cf_group("/artikel/a/", 1)]),
            env={"CLOUDFLARE_ANALYTICS_TOKEN": CF_TOKEN},
        )
        self.assertEqual(json.loads(out)["source"], "cloudflare")
        self.assertIsNone(self.written())


if __name__ == "__main__":
    unittest.main()
