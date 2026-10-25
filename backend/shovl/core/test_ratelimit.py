"""
The API's general rate limit (core/ratelimit.py).

Run with:  DJANGO_DEBUG=1 python manage.py test core
"""
from unittest.mock import patch

from django.test import TestCase, override_settings

from core.ratelimit import WINDOW_SECONDS, client_address

ME = "/api/accounts/me/"
ORIGIN = "http://localhost:5173"  # allowed by CORS_ALLOWED_ORIGINS in development
NOON = 1_800_000_000.0  # a fixed time, at the start of a one-minute window


@override_settings(SHOVL_API_RATE_LIMIT_PER_MINUTE=3)
class RateLimitTests(TestCase):
    # Each test gets a new test client, and with it fresh middleware and fresh counts.

    def get(self, path=ME, **extra):
        return self.client.get(path, **extra)

    def test_every_answer_says_where_the_client_stands(self):
        with patch("core.ratelimit.time.time", return_value=NOON + 15):
            response = self.get()
        self.assertEqual(response.status_code, 401)  # the view's own answer, untouched
        self.assertEqual(response["RateLimit-Limit"], "3")
        self.assertEqual(response["RateLimit-Remaining"], "2")
        self.assertEqual(response["RateLimit-Reset"], "45")

    def test_past_the_limit_the_answer_is_429_with_retry_after(self):
        with patch("core.ratelimit.time.time", return_value=NOON + 50):
            remaining = [self.get()["RateLimit-Remaining"] for _ in range(3)]
            refused = self.get()
        self.assertEqual(remaining, ["2", "1", "0"])
        self.assertEqual(refused.status_code, 429)
        self.assertEqual(refused["Retry-After"], "10")
        self.assertEqual(refused["RateLimit-Remaining"], "0")
        body = refused.json()
        self.assertEqual(body["code"], "rate_limited")
        self.assertEqual(body["retry_after"], 10)
        self.assertIn("Wait a minute", body["error"])

    def test_the_count_starts_again_each_minute(self):
        with patch("core.ratelimit.time.time", return_value=NOON + 1):
            for _ in range(4):
                self.get()
        with patch("core.ratelimit.time.time", return_value=NOON + WINDOW_SECONDS + 1):
            again = self.get()
        self.assertEqual(again.status_code, 401)
        self.assertEqual(again["RateLimit-Remaining"], "2")

    def test_paths_that_dont_exist_count_too(self):
        with patch("core.ratelimit.time.time", return_value=NOON):
            for _ in range(3):
                self.assertEqual(self.get("/nothing-here").status_code, 404)
            self.assertEqual(self.get("/nothing-here").status_code, 429)
            self.assertEqual(self.get(ME).status_code, 429)  # one count per address, not per path

    def test_the_health_check_is_never_counted(self):
        with patch("core.ratelimit.time.time", return_value=NOON):
            for _ in range(5):
                response = self.get("/healthz")
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("RateLimit-Limit", response)
            self.assertEqual(self.get()["RateLimit-Remaining"], "2")

    def test_cors_preflights_are_not_counted(self):
        with patch("core.ratelimit.time.time", return_value=NOON):
            for _ in range(5):
                self.client.options(
                    ME,
                    HTTP_ORIGIN=ORIGIN,
                    HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
                    HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization",
                )
            self.assertEqual(self.get()["RateLimit-Remaining"], "2")

    def test_a_429_carries_cors_headers_so_the_frontend_can_read_it(self):
        with patch("core.ratelimit.time.time", return_value=NOON):
            for _ in range(3):
                self.get(HTTP_ORIGIN=ORIGIN)
            refused = self.get(HTTP_ORIGIN=ORIGIN)
        self.assertEqual(refused.status_code, 429)
        self.assertEqual(refused["Access-Control-Allow-Origin"], ORIGIN)

    @override_settings(GUEST_THROTTLE_PROXIES=1)
    def test_each_address_has_its_own_count_and_made_up_ones_dont_help(self):
        with patch("core.ratelimit.time.time", return_value=NOON):
            for fake in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
                # The proxy appends the real address; whatever the client wrote comes first.
                self.get(HTTP_X_FORWARDED_FOR=f"{fake}, 203.0.113.7")
            refused = self.get(HTTP_X_FORWARDED_FOR="4.4.4.4, 203.0.113.7")
            someone_else = self.get(HTTP_X_FORWARDED_FOR="198.51.100.9")
        self.assertEqual(refused.status_code, 429)
        self.assertEqual(someone_else.status_code, 401)
        self.assertEqual(someone_else["RateLimit-Remaining"], "2")

    @override_settings(SHOVL_API_RATE_LIMIT_PER_MINUTE=0)
    def test_zero_turns_it_off(self):
        with patch("core.ratelimit.time.time", return_value=NOON):
            for _ in range(10):
                response = self.get()
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("RateLimit-Limit", response)


class ClientAddressTests(TestCase):
    def test_the_connection_address_without_proxies(self):
        meta = {"REMOTE_ADDR": "10.0.0.1", "HTTP_X_FORWARDED_FOR": "6.6.6.6"}
        with override_settings(GUEST_THROTTLE_PROXIES=0):
            self.assertEqual(client_address(meta), "10.0.0.1")

    def test_counts_back_from_the_end_behind_proxies(self):
        meta = {"REMOTE_ADDR": "10.0.0.1", "HTTP_X_FORWARDED_FOR": "6.6.6.6, 203.0.113.7, 10.1.1.1, 10.2.2.2"}
        with override_settings(GUEST_THROTTLE_PROXIES=3):
            self.assertEqual(client_address(meta), "203.0.113.7")

    def test_fewer_entries_than_proxies_uses_the_first(self):
        meta = {"REMOTE_ADDR": "10.0.0.1", "HTTP_X_FORWARDED_FOR": "203.0.113.7"}
        with override_settings(GUEST_THROTTLE_PROXIES=3):
            self.assertEqual(client_address(meta), "203.0.113.7")
