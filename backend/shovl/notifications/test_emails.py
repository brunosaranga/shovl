"""
murindzi's alert emails (notifications/emails.py): one email per account per runner pass, who
gets it, what's in it, the limits, the "turn these emails off" link and its endpoint, and that
nothing here can stop a pass.

Real passes (watch/runner.py, run_pass) with the engine and the verification check replaced,
so nothing touches the network. Emails go to Django's in-memory outbox.

Run with:  DJANGO_DEBUG=1 python manage.py test notifications
"""
import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit

from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.tokens import issue_tokens
from mailer.models import SentEmail
from mailer.services import address_hash
from mailer.tests import brevo_response
from notifications import emails
from notifications.models import Notification
from notifications.tests import API, API2, HOST, domain_for, fake_scan, registered, report
from scanner.engine import ScanFailed
from scans.models import Scan
from watch import runner
from watch.models import Watch

User = get_user_model()

SITE = "https://xikomu.com"
OFF = "/api/notifications/email-off/"
MAIL = dict(
    MAILER_ENABLED=True,
    EMAIL_DAILY_CAP=250,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_REPLY_TO="support@xikomu.com",
    CORS_ALLOWED_ORIGINS=[SITE],
)


def token_in(message):
    """The turn-off token from an email's List-Unsubscribe header."""
    url = message.extra_headers["List-Unsubscribe"].strip("<>")
    return unquote(parse_qs(urlsplit(url).query)["t"][0])


@override_settings(**MAIL)
class PassTests(TestCase):
    """What a pass sends, and to whom."""

    def setUp(self):
        self.user = registered(plan=User.PLAN_PRO, watch_intro_at=timezone.now())
        self.domain = domain_for(self.user)
        patcher = patch.object(runner, "verify_dns", return_value=True)
        self.verify = patcher.start()
        self.addCleanup(patch.stopall)
        self.watch = self.watched(API)

    def watched(self, url):
        earlier = report()
        Scan.objects.create(
            user=self.user, target_url=url, status="complete",
            completed_at=timezone.now() - timedelta(days=30),
            risk_score=earlier["meta"]["risk_score"], results=earlier,
        )
        return Watch.objects.create(user=self.user, domain=self.domain, target_url=url, next_run_at=timezone.now())

    def run_with(self, overrides=None):
        with patch.object(runner, "run_scan", side_effect=fake_scan(overrides)):
            return runner.run_pass()

    # ---- got worse ----

    def test_worse_sends_one_email_with_the_report_link(self):
        summary = self.run_with({"API4": "MEDIUM", "API2": "HIGH"})
        self.assertEqual(summary.emails.sent, 1)
        [message] = mail.outbox
        self.assertEqual(message.to, ["real@example.com"])
        self.assertEqual(message.subject, f"xikomu: {HOST}/v1 got worse")
        scan = summary.outcomes[0].scan
        self.assertIn(f"{HOST}/v1", message.body)
        self.assertIn("Risk LOW → HIGH.", message.body)
        self.assertIn(f"{SITE}/scan/{scan.pk}/report", message.body)
        html = message.alternatives[0][0]
        self.assertIn(f'href="{SITE}/scan/{scan.pk}/report"', html)
        self.assertIn("open the report", html)
        self.assertEqual(SentEmail.objects.get().kind, "watch_alert")
        self.assertEqual(SentEmail.objects.get().user, self.user)

    def test_nothing_worse_sends_nothing(self):
        summary = self.run_with()
        self.assertEqual(mail.outbox, [])
        self.assertEqual(str(summary.emails), "0 sent, 0 not wanted, 0 not sent")

    def test_several_findings_in_one_pass_make_one_email(self):
        self.watched(API2)
        summary = self.run_with({"API4": "MEDIUM"})
        self.assertEqual(summary.emails.sent, 1)
        [message] = mail.outbox
        self.assertEqual(message.subject, "xikomu: 2 updates from murindzi")
        self.assertIn(f"{HOST}/v1", message.body)
        self.assertIn(f"{HOST}/v2", message.body)

    def test_the_query_string_never_reaches_the_email(self):
        self.watch.delete()
        self.watched(API + "?api_key=s3cr3t-value")
        self.run_with({"API4": "MEDIUM"})
        [message] = mail.outbox
        self.assertNotIn("s3cr3t", message.subject + message.body + message.alternatives[0][0])

    def test_a_long_address_is_cut_in_the_subject(self):
        self.watch.delete()
        self.watched(f"https://{HOST}/" + "segment/" * 20)
        self.run_with({"API4": "MEDIUM"})
        subject = mail.outbox[0].subject
        self.assertTrue(subject.endswith("… got worse"), subject)
        self.assertLessEqual(len(subject), len("xikomu: ") + emails.SUBJECT_TARGET_MAX + len(" got worse"))

    # ---- paused ----

    def test_three_failed_runs_send_a_paused_email(self):
        Watch.objects.filter(pk=self.watch.pk).update(consecutive_failures=Watch.MAX_FAILURES - 1)
        with patch.object(runner, "run_scan", side_effect=ScanFailed("timeout", "slow")):
            summary = runner.run_pass()
        self.assertEqual(summary.outcomes[0].result, "paused")
        [message] = mail.outbox
        self.assertEqual(message.subject, f"xikomu: murindzi paused {HOST}/v1")
        self.assertIn("The last 3 scheduled scans failed.", message.body)
        self.assertIn(f"{SITE}/settings", message.body)

    def test_lost_verification_sends_one_item_for_the_domain(self):
        self.watched(API2)
        Watch.objects.filter(domain=self.domain).update(verification_failures=Watch.MAX_FAILURES - 1)
        self.verify.return_value = False
        summary = runner.run_pass()
        self.assertIn("paused", [o.result for o in summary.outcomes])
        [message] = mail.outbox
        self.assertEqual(message.subject, f"xikomu: murindzi paused {HOST}")
        self.assertEqual(message.body.count("paused: verification no longer passes"), 1)
        self.assertIn("its 2 watches are paused", message.body)

    def test_a_plain_failed_run_sends_nothing(self):
        with patch.object(runner, "run_scan", side_effect=ScanFailed("timeout", "slow")):
            summary = runner.run_pass()
        self.assertEqual(summary.outcomes[0].result, "failed")
        self.assertEqual(mail.outbox, [])

    # ---- who gets it ----

    def assert_bell_only(self, summary):
        self.assertEqual(mail.outbox, [])
        self.assertEqual(summary.emails.not_wanted, 1)
        self.assertTrue(Notification.objects.filter(kind=Notification.KIND_ALERT).exists())

    def test_muted_accounts_get_no_email(self):
        User.objects.filter(pk=self.user.pk).update(notifications_muted=True)
        self.assert_bell_only(self.run_with({"API4": "MEDIUM"}))

    def test_the_email_switch_turns_them_off(self):
        User.objects.filter(pk=self.user.pk).update(email_alerts=False)
        self.assert_bell_only(self.run_with({"API4": "MEDIUM"}))

    def test_unconfirmed_addresses_get_no_email(self):
        User.objects.filter(pk=self.user.pk).update(email_confirmed_at=None)
        self.assert_bell_only(self.run_with({"API4": "MEDIUM"}))

    def test_inactive_accounts_get_no_email(self):
        # The runner already skips their watches; the email rule says no on its own too.
        summary = self.run_with({"API4": "MEDIUM"})
        mail.outbox.clear()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        tally = emails.send_watch_emails(summary.outcomes)
        self.assertEqual((tally.sent, tally.not_wanted), (0, 1))
        self.assertEqual(mail.outbox, [])

    # ---- limits and failures ----

    def test_ten_a_day_to_one_address(self):
        for _ in range(10):
            SentEmail.objects.create(kind="watch_alert", to_hash=address_hash("real@example.com"), status=SentEmail.STATUS_SENT)
        summary = self.run_with({"API4": "MEDIUM"})
        self.assertEqual(mail.outbox, [])
        self.assertEqual(summary.emails.not_sent, 1)

    def test_a_failing_email_never_stops_the_pass(self):
        with patch("django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=OSError("down")):
            summary = self.run_with({"API4": "MEDIUM"})
        self.assertEqual(summary.count("complete"), 1)
        self.assertEqual(summary.emails.not_sent, 1)
        self.watch.refresh_from_db()
        self.assertEqual(self.watch.consecutive_failures, 0)

    def test_a_bug_in_the_emails_never_stops_the_pass(self):
        with patch.object(emails, "send_email", side_effect=RuntimeError("bug")), \
                self.assertLogs("notifications", level="ERROR"):
            summary = self.run_with({"API4": "MEDIUM"})
        self.assertEqual(summary.count("complete"), 1)
        self.assertEqual(summary.emails.not_sent, 1)

    def test_a_bug_working_out_who_to_email_never_stops_the_pass(self):
        with patch.object(emails, "items_by_account", side_effect=RuntimeError("bug")), \
                self.assertLogs("notifications", level="ERROR"):
            summary = self.run_with({"API4": "MEDIUM"})
        self.assertEqual(summary.count("complete"), 1)
        self.assertEqual(mail.outbox, [])

    def test_the_command_reports_the_emails(self):
        out = StringIO()
        with patch.object(runner, "run_scan", side_effect=fake_scan({"API4": "MEDIUM"})):
            call_command("run_watches", stdout=out)
        self.assertIn("murindzi emails: 1 sent, 0 not wanted, 0 not sent", out.getvalue())

    # ---- the way out ----

    def test_every_email_carries_a_turn_off_link(self):
        self.run_with({"API4": "MEDIUM"})
        [message] = mail.outbox
        header = message.extra_headers["List-Unsubscribe"]
        self.assertTrue(header.startswith(f"<{SITE}/email-off?t="), header)
        self.assertIn(f"{SITE}/email-off?t=", message.body)
        self.assertIn("Turn these emails off", message.alternatives[0][0])
        self.assertEqual(emails.user_for_token(token_in(message)), self.user)


@override_settings(**MAIL)
class TurnOffTests(TestCase):
    def setUp(self):
        self.user = registered()
        self.client = APIClient()

    def post(self, token, **extra):
        return self.client.post(OFF, {"token": token}, format="json", **extra)

    def test_a_genuine_link_turns_the_emails_off(self):
        response = self.post(emails.off_token(self.user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"done": True})
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_alerts)
        self.assertFalse(self.user.notifications_muted)  # the bell is untouched

    def test_twice_is_fine(self):
        token = emails.off_token(self.user)
        self.post(token)
        self.assertEqual(self.post(token).status_code, 200)

    def test_anything_else_is_refused(self):
        genuine = emails.off_token(self.user)
        other_salt = signing.dumps({"u": self.user.pk}, salt="something.else", compress=True)
        for bad in ["", None, "nonsense", genuine[:-2] + "xx", other_salt, signing.dumps({"x": 1}, salt=emails.SALT)]:
            response = self.post(bad)
            self.assertEqual(response.status_code, 400, bad)
            self.assertEqual(response.data["code"], "link_invalid")
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_alerts)

    def test_a_link_only_switches_off_its_own_account(self):
        other = registered("other@example.com")
        self.post(emails.off_token(self.user))
        other.refresh_from_db()
        self.assertTrue(other.email_alerts)

    def test_a_stale_sign_in_header_does_not_get_in_the_way(self):
        response = self.post(emails.off_token(self.user), HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(response.status_code, 200)

    def test_opening_the_address_does_nothing(self):
        response = self.client.get(OFF, {"token": emails.off_token(self.user)})
        self.assertEqual(response.status_code, 405)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_alerts)


class SwitchTests(TestCase):
    def test_me_shows_and_changes_the_email_switch(self):
        user = registered()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)[0]}")
        self.assertTrue(client.get("/api/accounts/me/").data["email_alerts"])
        response = client.patch("/api/accounts/me/", {"email_alerts": False}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["email_alerts"])
        user.refresh_from_db()
        self.assertFalse(user.email_alerts)

    def test_it_must_be_true_or_false(self):
        user = registered()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)[0]}")
        response = client.patch("/api/accounts/me/", {"email_alerts": "no"}, format="json")
        self.assertEqual(response.status_code, 400)


@override_settings(
    MAILER_ENABLED=True,
    EMAIL_DAILY_CAP=250,
    CORS_ALLOWED_ORIGINS=[SITE],
    EMAIL_BACKEND="anymail.backends.brevo.EmailBackend",
    ANYMAIL={"BREVO_API_KEY": "test-key"},
    EMAIL_REPLY_TO="support@xikomu.com",
)
class BrevoRequestTests(TestCase):
    """The turn-off link reaches Brevo as a plain header, with the HTTP request replaced."""

    def test_brevo_receives_the_list_unsubscribe_header(self):
        user = registered()
        with patch("requests.Session.request", return_value=brevo_response()) as request:
            result = emails.send_email(
                emails.KIND,
                user.email,
                {"headline": "x got worse", "items": [], "off_url": f"{SITE}/email-off?t=abc", "settings_url": ""},
                user=user,
                headers={"List-Unsubscribe": f"<{SITE}/email-off?t=abc>"},
            )
        self.assertTrue(result.sent)
        payload = json.loads(request.call_args.kwargs["data"])
        self.assertEqual(payload["headers"]["List-Unsubscribe"], f"<{SITE}/email-off?t=abc>")
        self.assertEqual(payload["subject"], "xikomu: x got worse")
        self.assertEqual(payload["tags"], ["watch_alert"])
