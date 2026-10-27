"""
Email (mailer/): sending through the one path, what is refused, the limits, failures that
must not escape, what is stored (never the address), the Brevo request itself, the templates,
the deploy check, the settings, the test command, the 90-day cleanup and the admin.

Nothing here reaches the network: Django's test runner swaps in its in-memory backend, and the
Brevo tests replace the HTTP request.

Run with:  DJANGO_DEBUG=1 python manage.py test mailer
"""
import json
import os
import subprocess
import sys
from datetime import timedelta
from io import StringIO
from pathlib import Path
from unittest import mock

import requests
from anymail.backends.test import EmailBackend as AnymailTestBackend
from anymail.exceptions import AnymailAPIError
from anymail.message import AnymailRecipientStatus
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from mailer import checks
from mailer.kinds import KINDS
from mailer.models import SentEmail
from mailer.services import address_hash, base_context, send_email

User = get_user_model()

ADDRESS = "bruno@example.com"
SITE = "https://xikomu.com"
BACKEND_DIR = Path(__file__).resolve().parent.parent


class RejectingBackend(AnymailTestBackend):
    """anymail's test backend, answering as Brevo does for an address it won't deliver to."""

    def post_to_esp(self, payload, message):
        message.anymail_test_response = {
            "recipient_status": {
                email: AnymailRecipientStatus(message_id="m-1", status="rejected")
                for email in payload.recipient_emails
            }
        }
        return super().post_to_esp(payload, message)


def age(row, delta):
    """Move a SentEmail back in time (created_at is set automatically on create)."""
    SentEmail.objects.filter(pk=row.pk).update(created_at=timezone.now() - delta)


@override_settings(
    MAILER_ENABLED=True,
    CORS_ALLOWED_ORIGINS=[SITE],
    DEFAULT_FROM_EMAIL="xikomu <hello@xikomu.com>",
    EMAIL_REPLY_TO="support@xikomu.com",
    EMAIL_DAILY_CAP=250,
)
class SendTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(ADDRESS, "correct horse battery staple", tos_agreed=True)

    def test_an_email_goes_out_with_both_parts(self):
        result = send_email("test", ADDRESS, user=self.user)

        self.assertTrue(result.sent)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [ADDRESS])
        self.assertEqual(message.from_email, "xikomu <hello@xikomu.com>")
        self.assertEqual(message.reply_to, ["support@xikomu.com"])
        self.assertEqual(message.subject, KINDS["test"].subject)
        self.assertEqual(message.tags, ["test"])
        # Plain text, not escaped as if it were HTML.
        self.assertIn("You're getting this", message.body)
        self.assertNotIn("&#x27;", message.body)
        self.assertIn(SITE, message.body)
        html, kind = message.alternatives[0]
        self.assertEqual(kind, "text/html")
        self.assertIn("sending works", html)
        self.assertIn(f'href="{SITE}"', html)

    def test_the_record_keeps_a_hash_never_the_address(self):
        result = send_email("test", ADDRESS, user=self.user)

        row = result.record
        self.assertEqual(row.status, SentEmail.STATUS_SENT)
        self.assertEqual(row.kind, "test")
        self.assertEqual(row.user, self.user)
        self.assertEqual(row.to_hash, address_hash(ADDRESS))
        self.assertEqual(len(row.to_hash), 64)
        for field in SentEmail._meta.fields:
            self.assertNotIn(ADDRESS, str(getattr(row, field.attname)), field.name)

    def test_the_address_is_trimmed_and_lowercased(self):
        send_email("test", "  Bruno@Example.COM ")

        self.assertEqual(mail.outbox[0].to, [ADDRESS])
        self.assertEqual(SentEmail.objects.get().to_hash, address_hash(ADDRESS))

    def test_without_a_user_the_record_has_none(self):
        self.assertIsNone(send_email("test", "someone@example.org").record.user)

    def test_an_unknown_kind_is_a_programming_error(self):
        with self.assertRaises(KeyError):
            send_email("newsletter", ADDRESS)
        self.assertEqual(mail.outbox, [])


@override_settings(MAILER_ENABLED=True, EMAIL_DAILY_CAP=250)
class RefusalTests(TestCase):
    def assert_refused(self, address, user=None, reason=None):
        result = send_email("test", address, user=user)
        self.assertFalse(result.sent)
        self.assertEqual(result.status, SentEmail.STATUS_REFUSED)
        if reason:
            self.assertEqual(result.record.error, reason)
        self.assertEqual(mail.outbox, [])

    def test_guest_accounts_are_never_emailed(self):
        guest = User.objects.create_guest(tos_agreed=True)
        self.assert_refused(guest.email, user=guest, reason="guest account")

    def test_reserved_invalid_addresses_are_refused(self):
        self.assert_refused("guest-abc@guest.xikomu.invalid", reason="reserved .invalid address")
        self.assert_refused("someone@invalid", reason="not a valid address")

    def test_things_that_are_not_addresses_are_refused(self):
        for address in ["", "   ", "no-at-sign", "a@", "@example.com", "two@@example.com",
                        "bruno@example.com\nBcc: victim@example.org",
                        "bruno@example.com, victim@example.org"]:
            with self.subTest(address=address):
                self.assert_refused(address, reason="not a valid address")

    @override_settings(MAILER_ENABLED=False)
    def test_a_server_without_a_key_sends_nothing(self):
        result = send_email("test", ADDRESS)
        self.assertEqual(result.status, SentEmail.STATUS_DISABLED)
        self.assertEqual(mail.outbox, [])


@override_settings(MAILER_ENABLED=True, EMAIL_DAILY_CAP=250)
class LimitTests(TestCase):
    def test_one_address_gets_at_most_the_kinds_limit(self):
        limit = KINDS["test"].per_address
        for _ in range(limit):
            self.assertTrue(send_email("test", ADDRESS).sent)

        result = send_email("test", ADDRESS)
        self.assertEqual(result.status, SentEmail.STATUS_LIMITED)
        self.assertEqual(result.record.error, "too many of this kind to this address")
        self.assertEqual(len(mail.outbox), limit)
        # Another address is unaffected.
        self.assertTrue(send_email("test", "other@example.com").sent)

    def test_the_window_moves_on(self):
        limit = KINDS["test"].per_address
        rows = [send_email("test", ADDRESS).record for _ in range(limit)]
        age(rows[0], KINDS["test"].window + timedelta(seconds=1))

        self.assertTrue(send_email("test", ADDRESS).sent)

    def test_failed_attempts_count_too(self):
        with mock.patch("mailer.services.EmailMultiAlternatives.send", side_effect=ConnectionError("down")):
            for _ in range(KINDS["test"].per_address):
                self.assertEqual(send_email("test", ADDRESS).status, SentEmail.STATUS_FAILED)

        self.assertEqual(send_email("test", ADDRESS).status, SentEmail.STATUS_LIMITED)

    def test_refused_and_limited_attempts_do_not_count(self):
        limit = KINDS["test"].per_address
        for _ in range(limit):
            send_email("test", ADDRESS)
        for _ in range(3):
            send_email("test", ADDRESS)  # limited
        rows = SentEmail.objects.filter(status=SentEmail.STATUS_SENT)
        for row in rows:
            age(row, timedelta(hours=2))

        self.assertTrue(send_email("test", ADDRESS).sent)

    @override_settings(EMAIL_DAILY_CAP=2)
    def test_the_daily_cap_covers_every_address(self):
        self.assertTrue(send_email("test", "one@example.com").sent)
        self.assertTrue(send_email("test", "two@example.com").sent)

        result = send_email("test", "three@example.com")
        self.assertEqual(result.status, SentEmail.STATUS_LIMITED)
        self.assertEqual(result.record.error, "daily cap reached")

    @override_settings(EMAIL_DAILY_CAP=2)
    def test_the_cap_counts_the_last_24_hours(self):
        old = send_email("test", "one@example.com").record
        send_email("test", "two@example.com")
        age(old, timedelta(hours=24, seconds=1))

        self.assertTrue(send_email("test", "three@example.com").sent)

    @override_settings(EMAIL_DAILY_CAP=0)
    def test_a_cap_of_zero_stops_all_email(self):
        self.assertEqual(send_email("test", ADDRESS).status, SentEmail.STATUS_LIMITED)
        self.assertEqual(mail.outbox, [])


@override_settings(MAILER_ENABLED=True, EMAIL_DAILY_CAP=250)
class FailureTests(TestCase):
    def test_a_provider_error_is_recorded_not_raised_and_the_address_is_kept_out(self):
        error = AnymailAPIError(f"Brevo API response 400: invalid recipient {ADDRESS}")
        with mock.patch("mailer.services.EmailMultiAlternatives.send", side_effect=error):
            with self.assertLogs("mailer", "WARNING") as logs:
                result = send_email("test", ADDRESS)

        self.assertEqual(result.status, SentEmail.STATUS_FAILED)
        self.assertIn("AnymailAPIError", result.record.error)
        self.assertIn("<recipient>", result.record.error)
        self.assertNotIn(ADDRESS, result.record.error)
        self.assertNotIn(ADDRESS, "\n".join(logs.output))

    def test_a_very_long_error_is_cut_to_fit(self):
        with mock.patch("mailer.services.EmailMultiAlternatives.send", side_effect=RuntimeError("x" * 2000)):
            result = send_email("test", ADDRESS)
        self.assertEqual(len(result.record.error), 300)

    @override_settings(EMAIL_BACKEND="mailer.tests.RejectingBackend")
    def test_an_address_brevo_refuses_counts_as_failed(self):
        result = send_email("test", ADDRESS)

        self.assertEqual(result.status, SentEmail.STATUS_FAILED)
        self.assertEqual(result.record.message_id, "m-1")
        self.assertIn("rejected", result.record.error)

    @override_settings(EMAIL_BACKEND="anymail.backends.test.EmailBackend")
    def test_the_providers_message_id_is_kept(self):
        result = send_email("test", ADDRESS)

        self.assertTrue(result.sent)
        self.assertEqual(result.record.message_id, "0")  # the test backend numbers its outbox


def brevo_response(status=201, body=None):
    response = requests.models.Response()
    response.status_code = status
    response._content = json.dumps(body or {"messageId": "<20261027.1@smtp-relay.mailin.fr>"}).encode()
    response.headers["Content-Type"] = "application/json"
    response.encoding = "utf-8"
    return response


@override_settings(
    MAILER_ENABLED=True,
    EMAIL_DAILY_CAP=250,
    CORS_ALLOWED_ORIGINS=[SITE],
    EMAIL_BACKEND="anymail.backends.brevo.EmailBackend",
    ANYMAIL={"BREVO_API_KEY": "test-key"},
    DEFAULT_FROM_EMAIL="xikomu <hello@xikomu.com>",
    EMAIL_REPLY_TO="support@xikomu.com",
)
class BrevoRequestTests(TestCase):
    """What actually goes to Brevo's API, with the HTTP request replaced."""

    def test_the_request_brevo_receives(self):
        with mock.patch("requests.Session.request", return_value=brevo_response()) as request:
            result = send_email("test", ADDRESS)

        self.assertTrue(result.sent)
        self.assertEqual(result.record.message_id, "<20261027.1@smtp-relay.mailin.fr>")
        call = request.call_args
        method = call.kwargs.get("method", call.args[0] if call.args else None)
        url = call.kwargs.get("url", call.args[1] if len(call.args) > 1 else None)
        self.assertEqual(method.upper(), "POST")
        self.assertEqual(url, "https://api.brevo.com/v3/smtp/email")
        self.assertEqual(request.call_args.kwargs["headers"]["api-key"], "test-key")
        payload = json.loads(request.call_args.kwargs["data"])
        self.assertEqual(payload["sender"], {"email": "hello@xikomu.com", "name": "xikomu"})
        self.assertEqual(payload["to"], [{"email": ADDRESS}])
        self.assertEqual(payload["replyTo"], {"email": "support@xikomu.com"})
        self.assertEqual(payload["subject"], KINDS["test"].subject)
        self.assertEqual(payload["tags"], ["test"])
        self.assertIn("sending works", payload["htmlContent"])
        self.assertIn("sending works", payload["textContent"])

    def test_brevo_saying_no_is_recorded(self):
        refusal = brevo_response(401, {"code": "unauthorized", "message": "Key not found"})
        with mock.patch("requests.Session.request", return_value=refusal):
            result = send_email("test", ADDRESS)

        self.assertEqual(result.status, SentEmail.STATUS_FAILED)
        self.assertIn("Key not found", result.record.error)
        self.assertNotIn(ADDRESS, result.record.error)

    def test_a_network_failure_is_recorded(self):
        with mock.patch("requests.Session.request", side_effect=requests.ConnectionError("no route")):
            result = send_email("test", ADDRESS)

        self.assertEqual(result.status, SentEmail.STATUS_FAILED)


@override_settings(CORS_ALLOWED_ORIGINS=[SITE], EMAIL_REPLY_TO="support@xikomu.com")
class TemplateTests(SimpleTestCase):
    def test_every_kind_renders_both_parts(self):
        for kind in KINDS.values():
            with self.subTest(kind=kind.name):
                values = {**base_context(), "subject": kind.subject}
                html = render_to_string(f"mailer/{kind.template}.html", values)
                text = render_to_string(f"mailer/{kind.template}.txt", values)
                self.assertIn("<html", html)
                self.assertIn("xikomu.com", html)
                self.assertNotIn("<", text.replace("<recipient>", ""))
                self.assertIn("support@xikomu.com", text)

    def test_html_escapes_what_it_is_given(self):
        values = {**base_context(), "subject": "x", "brand": '<script>alert("x")</script>'}
        html = render_to_string("mailer/test.html", values)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_the_context_points_at_the_frontend(self):
        self.assertEqual(base_context()["site_url"], SITE)
        self.assertEqual(base_context()["site_host"], "xikomu.com")

    @override_settings(CORS_ALLOWED_ORIGINS=[])
    def test_no_frontend_address_leaves_the_links_out(self):
        values = {**base_context(), "subject": "x"}
        html = render_to_string("mailer/test.html", values)
        self.assertNotIn("href=\"\"", html)


class DeployCheckTests(SimpleTestCase):
    @override_settings(DEBUG=False, BREVO_API_KEY="")
    def test_production_without_a_key_warns(self):
        problems = checks.brevo_key(None)
        self.assertEqual([p.id for p in problems], ["mailer.W001"])

    @override_settings(DEBUG=False, BREVO_API_KEY="xkeysib-123")
    def test_production_with_a_key_is_fine(self):
        self.assertEqual(checks.brevo_key(None), [])

    @override_settings(DEBUG=True, BREVO_API_KEY="")
    def test_development_needs_no_key(self):
        self.assertEqual(checks.brevo_key(None), [])


class SettingsTests(SimpleTestCase):
    """The backend chosen from the environment, read in a fresh Python each time."""

    def backend(self, **env):
        base = {k: v for k, v in os.environ.items() if k not in ("DJANGO_DEBUG", "BREVO_API_KEY", "DATABASE_URL")}
        base.update(env)
        code = (
            "import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings'); "
            "from django.conf import settings; "
            "print(settings.EMAIL_BACKEND, settings.MAILER_ENABLED, settings.EMAIL_DAILY_CAP)"
        )
        out = subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, env=base,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout.split()

    PRODUCTION = {
        "DJANGO_SECRET_KEY": "x" * 50,
        "DJANGO_ALLOWED_HOSTS": "api.xikomu.com",
        "CORS_ALLOWED_ORIGINS": SITE,
        "DATABASE_URL": "postgresql://u:p@db.example.com/xikomu",
    }

    def test_a_key_means_brevo(self):
        self.assertEqual(self.backend(**self.PRODUCTION, BREVO_API_KEY="xkeysib-1"),
                         ["anymail.backends.brevo.EmailBackend", "True", "250"])

    def test_development_without_a_key_prints(self):
        self.assertEqual(self.backend(DJANGO_DEBUG="1"),
                         ["django.core.mail.backends.console.EmailBackend", "True", "250"])

    def test_production_without_a_key_sends_nothing(self):
        self.assertEqual(self.backend(**self.PRODUCTION),
                         ["django.core.mail.backends.dummy.EmailBackend", "False", "250"])

    def test_the_cap_can_be_changed(self):
        self.assertEqual(self.backend(DJANGO_DEBUG="1", EMAIL_DAILY_CAP="100")[2], "100")


@override_settings(MAILER_ENABLED=True, EMAIL_DAILY_CAP=250, CORS_ALLOWED_ORIGINS=[SITE])
class CommandTests(TestCase):
    def test_the_test_command_sends(self):
        out = StringIO()
        call_command("send_test_email", ADDRESS, stdout=out)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [ADDRESS])
        self.assertIn("Sent.", out.getvalue())
        self.assertEqual(SentEmail.objects.get().kind, "test")

    def test_the_test_command_says_why_not(self):
        with self.assertRaisesMessage(CommandError, "address refused (not a valid address)"):
            call_command("send_test_email", "not-an-address", stdout=StringIO())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_development_says_it_printed(self):
        out = StringIO()
        with mock.patch("sys.stdout", new=StringIO()):  # where the console backend prints
            call_command("send_test_email", ADDRESS, stdout=out)
        self.assertIn("Printed above instead of sent", out.getvalue())


class CleanupTests(TestCase):
    def make(self, days_old):
        row = SentEmail.objects.create(kind="test", to_hash="h" * 64, status=SentEmail.STATUS_SENT)
        age(row, timedelta(days=days_old))
        return row

    def test_entries_older_than_90_days_are_deleted(self):
        old = self.make(91)
        recent = self.make(89)
        out = StringIO()
        call_command("purge_guests", stdout=out)

        self.assertFalse(SentEmail.objects.filter(pk=old.pk).exists())
        self.assertTrue(SentEmail.objects.filter(pk=recent.pk).exists())
        self.assertIn("Deleted 1 email log entries older than 90 days", out.getvalue())

    def test_a_dry_run_deletes_nothing(self):
        self.make(91)
        out = StringIO()
        call_command("purge_guests", "--dry-run", stdout=out)

        self.assertEqual(SentEmail.objects.count(), 1)
        self.assertIn("Would delete 1 email log entries older than 90 days", out.getvalue())

    def test_a_deleted_account_leaves_its_record_without_the_link(self):
        user = User.objects.create_user("gone@example.com", "correct horse battery staple", tos_agreed=True)
        row = SentEmail.objects.create(kind="test", user=user, to_hash="h" * 64, status=SentEmail.STATUS_SENT)
        user.delete()
        row.refresh_from_db()
        self.assertIsNone(row.user)


@override_settings(EMAIL_DAILY_CAP=250)
class AdminTests(TestCase):
    def test_the_list_shows_the_last_24_hours(self):
        admin_user = User.objects.create_superuser("admin@example.com", "correct horse battery staple")
        SentEmail.objects.create(kind="test", to_hash="a" * 64, status=SentEmail.STATUS_SENT)
        old = SentEmail.objects.create(kind="test", to_hash="b" * 64, status=SentEmail.STATUS_SENT)
        age(old, timedelta(days=2))
        SentEmail.objects.create(kind="test", to_hash="c" * 64, status=SentEmail.STATUS_LIMITED)
        self.client.force_login(admin_user)

        response = self.client.get("/admin/mailer/sentemail/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emails: 1 sent in the last 24 hours (cap 250)")
        self.assertContains(response, "aaaaaaaaaaaa…")
        self.assertEqual(self.client.get("/admin/mailer/sentemail/add/").status_code, 403)
