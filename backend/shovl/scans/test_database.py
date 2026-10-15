"""
Tests for what Postgres does differently from SQLite.

SQLite stores anything it is given; Postgres refuses text longer than the column, the NUL
character, broken Unicode and NaN inside JSON. The allowance lock only takes effect on Postgres,
so its test is skipped on SQLite.

Run with:  python manage.py test scans
Against Postgres:  DATABASE_URL=postgresql://... python manage.py test scans
"""
import math
import threading
import time
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from scans import limits
from scans.models import Scan
from scans.validators import MAX_URL_LENGTH, target_url_error

User = get_user_model()

CREATE = "/api/scans/create/"
STREAM = "/api/scans/stream/"
PRACTICE = "https://postman-echo.com/get"


def registered_user(email="real@example.com"):
    return User.objects.create_user(email, "correct horse battery staple", tos_agreed=True)


def signed_in(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class TargetUrlValidationTests(TestCase):
    """Bad URLs are refused with a 400 before anything touches the database."""

    def test_usable_urls_pass(self):
        for url in [PRACTICE, "http://example.com", f"{PRACTICE}?q={'a' * 1500}"]:
            self.assertIsNone(target_url_error(url), url)

    def test_unusable_urls_are_refused(self):
        for value in [
            None,
            "",
            123,
            ["https://example.com"],
            "example.com",
            "ftp://example.com/",
            "https://",
            "http://[::1",                          # urlparse raises on this one
            f"{PRACTICE}?q={'a' * MAX_URL_LENGTH}",
            f"{PRACTICE}\x00",
            f"{PRACTICE}?q=\x01",
            "https://exa\ud800mple.com/",          # a lone surrogate cannot be stored as UTF-8
        ]:
            self.assertIsNotNone(target_url_error(value), repr(value)[:60])

    def test_both_scan_endpoints_refuse_a_url_that_is_too_long(self):
        client = signed_in(registered_user())
        long_url = f"{PRACTICE}?q={'a' * MAX_URL_LENGTH}"

        self.assertEqual(client.post(CREATE, {"target_url": long_url}, format="json").status_code, 400)
        self.assertEqual(client.get(STREAM, {"target_url": long_url}).status_code, 400)
        self.assertFalse(Scan.objects.exists())

    def test_both_scan_endpoints_refuse_control_characters(self):
        client = signed_in(registered_user())

        self.assertEqual(client.post(CREATE, {"target_url": f"{PRACTICE}\x00"}, format="json").status_code, 400)
        self.assertEqual(client.get(STREAM, {"target_url": f"{PRACTICE}\x00"}).status_code, 400)
        self.assertFalse(Scan.objects.exists())

    def test_a_target_url_that_is_not_text_is_a_400_not_a_crash(self):
        client = signed_in(registered_user())
        response = client.post(CREATE, {"target_url": 123}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_the_old_messages_are_kept(self):
        client = signed_in(registered_user())
        missing = client.post(CREATE, {}, format="json")
        invalid = client.post(CREATE, {"target_url": "example.com"}, format="json")
        self.assertEqual(missing.data, {"error": "target_url is required."})
        self.assertEqual(invalid.data, {"error": "Invalid URL format. Include http:// or https://"})


class LongTargetUrlStorageTests(TestCase):
    def test_a_long_url_is_stored_in_full(self):
        url = f"{PRACTICE}?q={'a' * 1900}"
        scan = Scan.objects.create(user=registered_user(), target_url=url, status="running")
        scan.refresh_from_db()
        self.assertEqual(scan.target_url, url)


class ResultsStorageTests(TestCase):
    """Scan results hold text copied from the scanned API, which can be anything."""

    def test_text_postgres_refuses_is_cleaned_before_saving(self):
        results = {
            "summary": {"HIGH": 0, "MEDIUM": 1},
            "findings": [
                {
                    "check": "data\x00exposure",
                    "detail": "broken \ud800 text",
                    "raw": {
                        "fi\x00eld": "va\x00lue",
                        "nan": math.nan,
                        "inf": math.inf,
                        "nested": [math.nan, "ok", 1.5],
                        7: "number key",
                    },
                }
            ],
        }
        scan = Scan.objects.create(user=registered_user(), target_url=PRACTICE, results=results)
        scan.refresh_from_db()

        finding = scan.results["findings"][0]
        self.assertEqual(finding["check"], "dataexposure")
        self.assertEqual(finding["detail"], "broken ? text")
        self.assertEqual(finding["raw"]["field"], "value")
        self.assertIsNone(finding["raw"]["nan"])
        self.assertIsNone(finding["raw"]["inf"])
        self.assertEqual(finding["raw"]["nested"], [None, "ok", 1.5])
        self.assertEqual(finding["raw"]["7"], "number key")
        self.assertEqual(scan.results["summary"], {"HIGH": 0, "MEDIUM": 1})

    def test_ordinary_results_are_stored_unchanged(self):
        results = {"meta": {"risk_score": "LOW", "partial": False}, "findings": [{"severity": "PASS"}]}
        scan = Scan.objects.create(user=registered_user(), target_url=PRACTICE, results=results)
        scan.refresh_from_db()
        self.assertEqual(scan.results, results)


class SlowCount:
    """A queryset whose count() pauses, so simultaneous requests overlap on purpose."""

    def __init__(self, queryset, pause):
        self.queryset = queryset
        self.pause = pause

    def count(self):
        number = self.queryset.count()
        time.sleep(self.pause)
        return number

    def __getattr__(self, name):
        return getattr(self.queryset, name)


@skipUnless(connection.vendor == "postgresql", "the row lock only takes effect on Postgres")
class AllowanceLockTests(TransactionTestCase):
    """Several scans started at the same moment cannot all slip under the limit."""

    ATTEMPTS = 6

    def test_simultaneous_starts_stop_at_the_limit(self):
        user = registered_user("racer@example.com")
        for _ in range(limits.USER_SCANS_PER_DAY - 1):
            Scan.objects.create(user=user, target_url=PRACTICE, status="complete")

        original = limits._counted
        barrier = threading.Barrier(self.ATTEMPTS)
        outcomes = []

        def attempt():
            try:
                barrier.wait()
                limits.start_scan(User.objects.get(pk=user.pk), target_url=PRACTICE)
                outcomes.append("started")
            except limits.AllowanceExceeded:
                outcomes.append("refused")
            finally:
                connection.close()

        with patch.object(limits, "_counted", lambda scans, now: SlowCount(original(scans, now), 0.3)):
            threads = [threading.Thread(target=attempt) for _ in range(self.ATTEMPTS)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(outcomes.count("started"), 1, outcomes)
        self.assertEqual(outcomes.count("refused"), self.ATTEMPTS - 1, outcomes)
        self.assertEqual(Scan.objects.filter(user=user).count(), limits.USER_SCANS_PER_DAY)
