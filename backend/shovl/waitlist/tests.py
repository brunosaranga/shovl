"""
The launch list (waitlist/): joining (the same answer for every address, the honeypot, names,
consent, limits), the double opt-in (the email, its button, single use, expiry), "remove me",
the box ticked at sign-up and the account's code, the launch command and the cleanup.

Run with:  DJANGO_DEBUG=1 python manage.py test waitlist
"""
import re
from datetime import timedelta
from io import StringIO
from unittest import mock
from urllib.parse import parse_qs, unquote, urlsplit

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.tokens import issue_tokens
from mailer.models import SentEmail
from waitlist import services
from waitlist.admin import WaitlistEntryAdmin
from waitlist.models import WaitlistEntry

User = get_user_model()

SITE = "https://xikomu.com"
JOIN = "/api/waitlist/"
CONFIRM = "/api/waitlist/confirm/"
LEAVE = "/api/waitlist/leave/"
PASSWORD = "a-long-test-password-77"
MAIL = dict(
    MAILER_ENABLED=True,
    EMAIL_DAILY_CAP=250,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_REPLY_TO="support@xikomu.com",
    CORS_ALLOWED_ORIGINS=[SITE],
)


def link(message, path):
    """The token of the link to SITE/path in an email's plain text."""
    url = re.search(rf"{re.escape(SITE)}{re.escape(path)}\?t=(\S+)", message.body).group(0)
    return unquote(parse_qs(urlsplit(url).query)["t"][0])


@override_settings(**MAIL)
class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def join(self, email="ana@example.com", first_name="Ana", **extra):
        body = {"email": email, "first_name": first_name, "consent_version": services.CONSENT_VERSION, **extra}
        return self.client.post(JOIN, body, format="json")

    def older(self, entry, **deltas):
        """Move an entry's times into the past."""
        fields = {}
        for name, delta in deltas.items():
            fields[name] = getattr(WaitlistEntry.objects.get(pk=entry.pk), name) - delta
        WaitlistEntry.objects.filter(pk=entry.pk).update(**fields)


class JoinTests(Base):
    def test_joining_makes_a_pending_entry_and_emails_a_link_with_nothing_typed(self):
        response = self.join("  Ana@Example.com ", "Ana")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "pending")
        entry = WaitlistEntry.objects.get()
        self.assertEqual(entry.email, "ana@example.com")
        self.assertEqual(entry.first_name, "Ana")
        self.assertEqual(entry.source, "after_scan")
        self.assertIsNone(entry.confirmed_at)
        self.assertEqual(entry.consent_version, services.CONSENT_VERSION)
        self.assertEqual(entry.consent_text, services.CONSENT_TEXT)
        self.assertEqual(len(entry.token_hash), 64)

        [message] = mail.outbox
        self.assertEqual(message.to, ["ana@example.com"])
        self.assertEqual(message.subject, "xikomu: confirm you want the launch email")
        everything = message.subject + message.body + message.alternatives[0][0]
        self.assertNotIn("Ana", everything)
        token = link(message, "/waitlist/confirm")
        self.assertNotIn(token, entry.token_hash)
        self.assertIn("/waitlist/leave?t=", message.extra_headers["List-Unsubscribe"])

    def test_the_same_answer_for_new_pending_and_listed_addresses(self):
        new = self.join("a@example.com").data
        pending = self.join("a@example.com").data
        WaitlistEntry.objects.filter(email="a@example.com").update(confirmed_at=timezone.now())
        listed = self.join("a@example.com").data
        self.assertEqual(new, pending)
        self.assertEqual(new, listed)
        self.assertEqual(len(mail.outbox), 1)

    def test_a_filled_honeypot_does_nothing_and_says_the_same(self):
        response = self.join(website="http://spam.example")
        self.assertEqual(response.data, self.join("b@example.com").data | {})
        self.assertEqual(WaitlistEntry.objects.filter(email="ana@example.com").count(), 0)

    def test_names(self):
        for good in ["Ana", "José", "Anne-Marie", "O'Neil", "Mary Ann", "Zoë", "李雷", "  Ana   Maria "]:
            cache.clear()
            self.assertEqual(self.join(f"{abs(hash(good))}@example.com", good).status_code, 200, good)
        for bad in ["", "   ", "Ana2", "ana@x", "http://x.io", "x" * 51, "Ana--Maria", "<b>Ana</b>", None]:
            cache.clear()
            response = self.join("bad@example.com", bad)
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn("first_name", response.data)
        self.assertEqual(WaitlistEntry.objects.get(email=f"{abs(hash('  Ana   Maria '))}@example.com").first_name, "Ana Maria")

    def test_an_address_is_needed(self):
        for bad in ["", "nope", None]:
            response = self.join(bad)
            self.assertEqual(response.status_code, 400)
            self.assertIn("email", response.data)

    def test_the_wording_must_be_the_current_one(self):
        response = self.join(consent_version="2020-01-01")
        self.assertEqual(response.status_code, 400)
        self.assertIn("consent", response.data)
        self.assertFalse(WaitlistEntry.objects.exists())

    def test_one_email_a_day_and_three_in_all(self):
        self.join()
        entry = WaitlistEntry.objects.get()
        for _ in range(4):
            self.older(entry, last_confirm_email_at=timedelta(hours=25))
            SentEmail.objects.update(created_at=timezone.now() - timedelta(hours=25))
            cache.clear()
            self.join()
        self.assertEqual(len(mail.outbox), services.CONFIRM_EMAILS_MAX)

    def test_asking_again_the_same_day_keeps_the_first_link_working(self):
        self.join()
        first = link(mail.outbox[0], "/waitlist/confirm")
        self.join()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.client.post(CONFIRM, {"token": first}, format="json").status_code, 200)

    def test_joining_again_while_pending_updates_the_name(self):
        self.join(first_name="Ana")
        self.join(first_name="Anabela")
        self.assertEqual(WaitlistEntry.objects.get().first_name, "Anabela")

    def test_ten_requests_an_hour_per_network_even_signed_in_as_a_guest(self):
        guest = User.objects.create_guest()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(guest)[0]}")
        for n in range(10):
            self.join(f"n{n}@example.com")
        refused = self.join("n10@example.com")
        self.assertEqual(refused.status_code, 429)
        self.assertEqual(refused.data["code"], "too_many_requests")
        self.assertIn("Try again in an hour", refused.data["detail"])

    def test_a_confirmed_account_with_its_own_address_is_on_at_once(self):
        user = User.objects.create_user("me@example.com", PASSWORD)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)[0]}")
        response = self.join("Me@Example.com", "Bruno")
        self.assertEqual(response.data["status"], "confirmed")
        self.assertIsNotNone(WaitlistEntry.objects.get().confirmed_at)
        self.assertEqual(mail.outbox, [])

    def test_a_confirmed_account_with_another_address_gets_the_email(self):
        user = User.objects.create_user("me@example.com", PASSWORD)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)[0]}")
        self.assertEqual(self.join("other@example.com").data["status"], "pending")
        self.assertEqual(len(mail.outbox), 1)

    def test_an_unconfirmed_account_gets_the_email(self):
        user = User.objects.create_user("me@example.com", PASSWORD, email_confirmed_at=None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)[0]}")
        self.assertEqual(self.join("me@example.com").data["status"], "pending")
        self.assertEqual(len(mail.outbox), 1)

    def test_a_failed_email_still_says_the_same(self):
        with mock.patch("django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=OSError("down")):
            response = self.join()
        self.assertEqual(response.data["status"], "pending")


class ConfirmTests(Base):
    def setUp(self):
        super().setUp()
        self.join()
        self.token = link(mail.outbox[0], "/waitlist/confirm")

    def test_the_button_confirms_once(self):
        response = self.client.post(CONFIRM, {"token": self.token}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"done": True})
        entry = WaitlistEntry.objects.get()
        self.assertIsNotNone(entry.confirmed_at)
        self.assertEqual(entry.token_hash, "")
        again = self.client.post(CONFIRM, {"token": self.token}, format="json")
        self.assertEqual(again.status_code, 400)
        self.assertEqual(again.data["code"], "link_invalid")

    def test_after_48_hours_the_link_is_dead(self):
        self.older(WaitlistEntry.objects.get(), token_expires_at=timedelta(hours=48, seconds=1))
        self.assertEqual(self.client.post(CONFIRM, {"token": self.token}, format="json").status_code, 400)

    def test_anything_else_is_refused(self):
        for bad in ["", None, "nonsense", self.token[:-1]]:
            self.assertEqual(self.client.post(CONFIRM, {"token": bad}, format="json").status_code, 400)
        self.assertIsNone(WaitlistEntry.objects.get().confirmed_at)

    def test_opening_the_address_does_nothing(self):
        self.assertEqual(self.client.get(CONFIRM, {"token": self.token}).status_code, 405)
        self.assertIsNone(WaitlistEntry.objects.get().confirmed_at)

    def test_a_newer_link_replaces_the_older(self):
        self.older(WaitlistEntry.objects.get(), last_confirm_email_at=timedelta(hours=25))
        SentEmail.objects.update(created_at=timezone.now() - timedelta(hours=25))
        self.join()
        newer = link(mail.outbox[1], "/waitlist/confirm")
        self.assertEqual(self.client.post(CONFIRM, {"token": self.token}, format="json").status_code, 400)
        self.assertEqual(self.client.post(CONFIRM, {"token": newer}, format="json").status_code, 200)

    def test_a_stale_sign_in_header_does_not_matter(self):
        response = self.client.post(CONFIRM, {"token": self.token}, format="json", HTTP_AUTHORIZATION="Bearer junk")
        self.assertEqual(response.status_code, 200)


class LeaveTests(Base):
    def test_remove_me_deletes_the_entry(self):
        self.join()
        token = link(mail.outbox[0], "/waitlist/leave")
        response = self.client.post(LEAVE, {"token": token}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(WaitlistEntry.objects.exists())
        self.assertEqual(self.client.post(LEAVE, {"token": token}, format="json").status_code, 200)

    def test_a_link_only_removes_its_own_entry(self):
        self.join("a@example.com")
        self.join("b@example.com")
        token = link(mail.outbox[0], "/waitlist/leave")
        self.client.post(LEAVE, {"token": token}, format="json")
        self.assertEqual(list(WaitlistEntry.objects.values_list("email", flat=True)), ["b@example.com"])

    def test_forged_links_are_refused(self):
        self.join()
        entry = WaitlistEntry.objects.get()
        forged = signing.dumps({"e": entry.pk, "h": "0" * 16}, salt=services.LEAVE_SALT, compress=True)
        other_salt = signing.dumps({"e": entry.pk, "h": "x"}, salt="something.else", compress=True)
        for bad in ["", "nonsense", other_salt]:
            response = self.client.post(LEAVE, {"token": bad}, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["code"], "link_invalid")
            self.assertNotIn("48 hours", response.data["detail"])  # leave links never expire
        self.client.post(LEAVE, {"token": forged}, format="json")
        self.assertTrue(WaitlistEntry.objects.exists())


class SignUpTickTests(Base):
    def register(self, email="new@example.com", tick=True):
        return self.client.post(
            "/api/accounts/register/",
            {"email": email, "password": PASSWORD, "tos_agreed": True, "waitlist": tick},
            format="json",
        )

    def test_the_tick_waits_for_the_accounts_code(self):
        self.assertEqual(self.register().status_code, 201)
        user = User.objects.get(email="new@example.com")
        entry = WaitlistEntry.objects.get()
        self.assertEqual(entry.source, "registration")
        self.assertEqual(entry.account, user)
        self.assertIsNone(entry.confirmed_at)
        self.assertEqual([m.subject.split(":")[1].strip()[:9] for m in mail.outbox], ["your code"])  # no list email
        code = re.search(r"\b(\d{6})\b", mail.outbox[0].subject).group(1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)[0]}")
        self.client.post("/api/accounts/email/confirm/", {"code": code}, format="json")
        self.assertIsNotNone(WaitlistEntry.objects.get().confirmed_at)

    def test_no_tick_no_entry(self):
        self.register(tick=False)
        self.assertFalse(WaitlistEntry.objects.exists())

    def test_the_tick_on_upgrade(self):
        guest = User.objects.create_guest()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(guest)[0]}")
        response = self.client.post(
            "/api/accounts/upgrade/",
            {"email": "up@example.com", "password": PASSWORD, "tos_agreed": True, "waitlist": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(WaitlistEntry.objects.get().email, "up@example.com")

    def test_a_password_reset_confirms_it_too(self):
        self.register()
        self.client.credentials()
        self.client.post("/api/accounts/password/reset/", {"email": "new@example.com"}, format="json")
        code = re.search(r"^\s+(\d{6})\s*$", mail.outbox[-1].body, re.M).group(1)
        self.client.post(
            "/api/accounts/password/reset/confirm/",
            {"email": "new@example.com", "code": code, "password": "another-long-passphrase-9"},
            format="json",
        )
        self.assertIsNotNone(WaitlistEntry.objects.get().confirmed_at)

    def test_the_admin_action_confirms_it_too(self):
        from accounts.admin import UserAdmin
        from django.contrib.messages.storage.fallback import FallbackStorage

        self.register()
        request = RequestFactory().post("/admin/")
        request.user = User.objects.create_superuser("boss@example.com", PASSWORD)
        request.session = {}
        request._messages = FallbackStorage(request)
        UserAdmin(User, AdminSite()).mark_confirmed(request, User.objects.filter(email="new@example.com"))
        self.assertIsNotNone(WaitlistEntry.objects.get().confirmed_at)

    def test_another_accounts_code_confirms_nothing(self):
        self.register()
        other = User.objects.create_user("other@example.com", PASSWORD, email_confirmed_at=None)
        services.account_confirmed(other)
        self.assertIsNone(WaitlistEntry.objects.get().confirmed_at)

    def change_and_confirm(self, new_email):
        user = User.objects.get(email="new@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)[0]}")
        changed = self.client.post("/api/accounts/email/change/", {"email": new_email, "password": PASSWORD}, format="json")
        self.assertEqual(changed.status_code, 200, changed.data)
        code = re.search(r"\b(\d{6})\b", mail.outbox[-1].subject).group(1)
        self.client.post("/api/accounts/email/confirm/", {"code": code}, format="json")

    def test_a_corrected_address_takes_the_tick_along(self):
        self.register()  # a typo, fixed on the code screen
        self.change_and_confirm("right@example.com")
        entry = WaitlistEntry.objects.get()
        self.assertEqual(entry.email, "right@example.com")
        self.assertIsNotNone(entry.confirmed_at)

    def test_a_corrected_address_already_on_the_list(self):
        self.register()
        WaitlistEntry.objects.create(
            email="right@example.com", source="after_scan", consent_version=services.CONSENT_VERSION,
            consent_text=services.CONSENT_TEXT, agreed_at=timezone.now(), confirmed_at=timezone.now(),
        )
        self.change_and_confirm("right@example.com")
        self.assertEqual(list(WaitlistEntry.objects.values_list("email", flat=True)), ["right@example.com"])

    def test_a_deleted_accounts_tick_doesnt_carry_over(self):
        self.register()
        User.objects.get(email="new@example.com").delete()  # the entry stays, without its account
        self.register(tick=False)  # the same address, a new account, no tick
        user = User.objects.get(email="new@example.com")
        services.account_confirmed(user)
        self.assertIsNone(WaitlistEntry.objects.get().confirmed_at)

    def test_a_problem_with_the_list_never_stops_the_sign_up(self):
        with mock.patch("waitlist.services.join", side_effect=RuntimeError("bug")), \
                self.assertLogs("accounts", level="ERROR"):
            self.assertEqual(self.register().status_code, 201)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())


@override_settings(**MAIL)
class LaunchCommandTests(TestCase):
    def setUp(self):
        now = timezone.now()
        for n, name in enumerate(["Ana", "", "Bruno"]):
            WaitlistEntry.objects.create(
                email=f"c{n}@example.com", first_name=name, source="after_scan",
                consent_version=services.CONSENT_VERSION, consent_text=services.CONSENT_TEXT,
                agreed_at=now, confirmed_at=now,
            )
        WaitlistEntry.objects.create(
            email="pending@example.com", first_name="Pat", source="after_scan",
            consent_version=services.CONSENT_VERSION, consent_text=services.CONSENT_TEXT, agreed_at=now,
        )

    def run_command(self, *args):
        out = StringIO()
        call_command("send_launch_email", *args, stdout=out)
        return out.getvalue()

    def test_without_send_nothing_goes_out(self):
        out = self.run_command()
        self.assertIn("3 confirmed waiting, 0 already sent, 1 unconfirmed", out)
        self.assertIn("Nothing sent", out)
        self.assertEqual(mail.outbox, [])

    def test_it_refuses_to_send_the_draft(self):
        self.assertIn("DRAFT", self.run_command())
        with self.assertRaises(CommandError):
            self.run_command("--send")
        self.assertEqual(mail.outbox, [])

    def test_it_sends_once_to_the_confirmed_only(self):
        with mock.patch("waitlist.management.commands.send_launch_email.draft_templates", return_value=[]):
            out = self.run_command("--send")
            again = self.run_command("--send")
        self.assertIn("3 sent, 0 skipped, 0 failed, 0 still waiting", out)
        self.assertIn("0 sent", again)
        self.assertEqual(sorted(m.to[0] for m in mail.outbox), ["c0@example.com", "c1@example.com", "c2@example.com"])
        ana = next(m for m in mail.outbox if m.to == ["c0@example.com"])
        self.assertEqual(ana.subject, "xikomu has launched")
        self.assertIn("Ana, xikomu has launched", ana.body)
        self.assertIn("/waitlist/leave?t=", ana.extra_headers["List-Unsubscribe"])
        nameless = next(m for m in mail.outbox if m.to == ["c1@example.com"])
        self.assertTrue(nameless.body.startswith("xikomu has launched"))
        self.assertEqual(WaitlistEntry.objects.filter(launch_sent_at__isnull=False).count(), 3)

    def test_a_limit_and_the_daily_cap_leave_the_rest_for_later(self):
        with mock.patch("waitlist.management.commands.send_launch_email.draft_templates", return_value=[]):
            self.assertIn("1 sent", self.run_command("--send", "--limit", "1"))
            with override_settings(EMAIL_DAILY_CAP=2):
                out = self.run_command("--send")
            self.assertIn("cap is reached", out)
            self.assertIn("1 still waiting", out)

    def test_the_real_templates_carry_the_draft_line(self):
        from waitlist.management.commands.send_launch_email import draft_templates

        self.assertEqual(draft_templates(), ["mailer/launch.html", "mailer/launch.txt"])


class CleanupTests(TestCase):
    def test_pending_after_7_days_and_everyone_a_month_after_launch(self):
        now = timezone.now()
        common = dict(source="after_scan", consent_version="v", consent_text="t", agreed_at=now)
        old_pending = WaitlistEntry.objects.create(email="a@example.com", **common)
        new_pending = WaitlistEntry.objects.create(email="b@example.com", **common)
        confirmed = WaitlistEntry.objects.create(email="c@example.com", confirmed_at=now, **common)
        launched_long_ago = WaitlistEntry.objects.create(
            email="d@example.com", confirmed_at=now, launch_sent_at=now - timedelta(days=31), **common
        )
        launched_lately = WaitlistEntry.objects.create(
            email="e@example.com", confirmed_at=now, launch_sent_at=now - timedelta(days=2), **common
        )
        WaitlistEntry.objects.filter(pk=old_pending.pk).update(created_at=now - timedelta(days=8))

        out = StringIO()
        call_command("purge_guests", "--dry-run", stdout=out)
        self.assertIn("Would delete 1 unconfirmed launch list requests older than 7 days, 1 entries", out.getvalue())
        call_command("purge_guests", stdout=StringIO())
        left = set(WaitlistEntry.objects.values_list("email", flat=True))
        self.assertEqual(left, {new_pending.email, confirmed.email, launched_lately.email})
        self.assertNotIn(launched_long_ago.email, left)


class AdminTests(TestCase):
    def test_the_title_counts_the_list(self):
        now = timezone.now()
        common = dict(source="after_scan", consent_version="v", consent_text="t", agreed_at=now)
        WaitlistEntry.objects.create(email="a@example.com", confirmed_at=now, **common)
        WaitlistEntry.objects.create(email="b@example.com", **common)
        request = RequestFactory().get("/admin/waitlist/waitlistentry/")
        request.user = User.objects.create_superuser("boss@example.com", PASSWORD)
        response = WaitlistEntryAdmin(WaitlistEntry, AdminSite()).changelist_view(request)
        self.assertEqual(response.context_data["title"], "Launch list: 1 confirmed, 1 pending")
        self.assertNotIn("token_hash", WaitlistEntryAdmin.readonly_fields)

    def test_entries_are_read_only_but_can_be_deleted(self):
        # What people agreed to, and when, is a record: nobody edits it. Deleting (a request to be
        # removed by email) stays possible.
        request = RequestFactory().get("/admin/waitlist/waitlistentry/")
        request.user = User.objects.create_superuser("boss@example.com", PASSWORD)
        admin = WaitlistEntryAdmin(WaitlistEntry, AdminSite())
        self.assertFalse(admin.has_add_permission(request))
        self.assertFalse(admin.has_change_permission(request))
        self.assertTrue(admin.has_delete_permission(request))
