"""
Resetting a forgotten password with a 6-digit code (accounts/reset.py): asking for a code, the
same answer for addresses with no account, the code's rules, setting the password, signing
out every other session, confirming the address, moving a guest's scans, and the limits.

Run with:  DJANGO_DEBUG=1 python manage.py test accounts.test_reset
"""
import re
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts import confirmation, reset
from accounts.models import EmailCode
from accounts.tokens import issue_tokens
from mailer.models import SentEmail
from mailer.services import address_hash
from scans.models import Scan

User = get_user_model()

OLD = "the-old-long-passphrase-1"
NEW = "a-brand-new-passphrase-2"
ASK = "/api/accounts/password/reset/"
RESET = "/api/accounts/password/reset/confirm/"
ME = "/api/accounts/me/"
LOGIN = "/api/accounts/login/"
MAIL = dict(
    MAILER_ENABLED=True,
    EMAIL_DAILY_CAP=250,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_REPLY_TO="support@xikomu.com",
    CORS_ALLOWED_ORIGINS=["https://xikomu.com"],
)


def code_in(message):
    return re.search(r"^\s+(\d{6})\s*$", message.body, re.M).group(1)


def back_in_time(user, delta):
    for row in EmailCode.objects.filter(user=user):
        EmailCode.objects.filter(pk=row.pk).update(created_at=row.created_at - delta, expires_at=row.expires_at - delta)
    for row in SentEmail.objects.filter(user=user):
        SentEmail.objects.filter(pk=row.pk).update(created_at=row.created_at - delta)


@override_settings(**MAIL)
class Base(TestCase):
    def setUp(self):
        cache.clear()  # the network throttles count in the cache
        self.client = APIClient()
        self.user = User.objects.create_user("bruno@example.com", OLD, tos_agreed=True)

    def ask(self, email="bruno@example.com"):
        return self.client.post(ASK, {"email": email}, format="json")

    def reset(self, code, password=NEW, email="bruno@example.com", **extra):
        return self.client.post(RESET, {"email": email, "code": code, "password": password, **extra}, format="json")

    def sign_in(self, password):
        return APIClient().post(LOGIN, {"email": "bruno@example.com", "password": password}, format="json")


class AskTests(Base):
    def test_asking_emails_a_code_not_in_the_subject(self):
        response = self.ask("  Bruno@Example.COM ")
        self.assertEqual(response.status_code, 200)
        self.assertIn("If an account uses this address", response.data["detail"])
        self.assertEqual(response.data["resend_in"], 60)
        [message] = mail.outbox
        self.assertEqual(message.to, ["bruno@example.com"])
        self.assertEqual(message.subject, "xikomu: reset your password")
        code = code_in(message)
        self.assertNotIn(code, message.subject)
        self.assertIn(code, message.alternatives[0][0])
        self.assertNotIn(code, message.alternatives[0][0].split("<body")[1].split("</div>")[0])  # not in the preview line
        row = EmailCode.objects.get(user=self.user)
        self.assertEqual(row.purpose, EmailCode.PURPOSE_RESET)
        self.assertNotIn(code, row.code_hash)
        self.assertEqual(SentEmail.objects.get().kind, "password_reset")

    def test_an_address_without_an_account_gets_the_same_answer(self):
        known = self.ask()
        cache.clear()
        unknown = self.ask("nobody@example.com")
        self.assertEqual(unknown.status_code, known.status_code)
        self.assertEqual(unknown.data, known.data)
        self.assertEqual(len(mail.outbox), 1)

    def test_guests_and_inactive_accounts_get_no_code(self):
        guest = User.objects.create_guest()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.ask(guest.email).status_code, 200)
        self.assertEqual(self.ask().status_code, 200)
        self.assertEqual(mail.outbox, [])

    def test_a_minute_between_codes(self):
        self.ask()
        response = self.ask()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["code"], "code_cooldown")
        self.assertTrue(1 <= response.data["retry_after"] <= 60)
        back_in_time(self.user, timedelta(seconds=61))
        self.assertEqual(self.ask().status_code, 200)
        self.assertEqual(len(mail.outbox), 2)

    def test_ten_codes_a_day_per_account(self):
        for _ in range(reset.CODES_PER_DAY):
            SentEmail.objects.create(kind="password_reset", user=self.user, to_hash="x" * 64, status=SentEmail.STATUS_SENT)
        back_in_time(self.user, timedelta(minutes=2))
        response = self.ask()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["code"], "code_limit")

    def test_five_a_day_to_one_address(self):
        for _ in range(5):
            SentEmail.objects.create(kind="password_reset", to_hash=address_hash("bruno@example.com"), status=SentEmail.STATUS_SENT)
        response = self.ask()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["code"], "code_limit")
        self.assertFalse(EmailCode.objects.exists())

    def test_a_failed_send_leaves_no_code(self):
        with mock.patch("django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=OSError("down")):
            response = self.ask()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "email_failed")
        self.assertFalse(EmailCode.objects.exists())

    def test_ten_requests_an_hour_per_network(self):
        for n in range(10):
            self.ask(f"someone{n}@example.com")
        response = self.ask("someone10@example.com")
        self.assertEqual(response.status_code, 429)

    def test_a_stale_sign_in_header_does_not_get_in_the_way(self):
        response = self.client.post(ASK, {"email": "bruno@example.com"}, format="json", HTTP_AUTHORIZATION="Bearer junk")
        self.assertEqual(response.status_code, 200)

    def test_a_malformed_address_is_a_field_error(self):
        response = self.ask("not-an-address")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)


class ResetTests(Base):
    def setUp(self):
        super().setUp()
        self.old_token = issue_tokens(self.user)[0]
        self.ask()
        self.code = code_in(mail.outbox[0])

    def test_the_right_code_sets_the_password_and_signs_in(self):
        response = self.reset(self.code)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.data["is_guest"])
        self.assertTrue(response.data["email_confirmed"])
        self.assertEqual(self.sign_in(NEW).status_code, 200)
        self.assertEqual(self.sign_in(OLD).status_code, 401)
        new_session = APIClient()
        new_session.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(new_session.get(ME).status_code, 200)
        self.assertFalse(EmailCode.objects.filter(user=self.user).exists())

    def test_every_other_session_is_signed_out(self):
        self.reset(self.code)
        old_session = APIClient()
        old_session.credentials(HTTP_AUTHORIZATION=f"Bearer {self.old_token}")
        self.assertEqual(old_session.get(ME).status_code, 401)

    def test_a_reset_confirms_an_unconfirmed_address(self):
        User.objects.filter(pk=self.user.pk).update(email_confirmed_at=None, confirm_by=self.user.date_joined)
        EmailCode.objects.create(user=self.user, purpose="confirm", sent_to="x", code_hash="y", expires_at=self.user.date_joined)
        self.reset(self.code)
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.email_confirmed_at)
        self.assertIsNone(self.user.confirm_by)
        self.assertFalse(EmailCode.objects.filter(user=self.user).exists())

    def test_a_weak_password_is_refused_without_using_a_try(self):
        response = self.reset(self.code, password="12345678")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)
        self.assertEqual(EmailCode.objects.get(user=self.user).attempts, 0)
        self.assertEqual(self.reset(self.code).status_code, 200)

    def test_five_wrong_tries_use_the_code_up(self):
        wrong = "000000" if self.code != "000000" else "111111"
        for left in [4, 3, 2, 1]:
            response = self.reset(wrong)
            self.assertEqual(response.data["code"], "code_wrong")
            self.assertEqual(response.data["attempts_left"], left)
        self.assertEqual(self.reset(wrong).data["code"], "code_used_up")
        self.assertEqual(self.reset(self.code).data["code"], "code_expired")
        self.assertEqual(self.sign_in(OLD).status_code, 200)

    def test_not_six_digits_is_not_a_try(self):
        for bad in ["", "12345", "abcdef", "1234567"]:
            self.assertEqual(self.reset(bad).data["code"], "code_invalid")
        self.assertEqual(EmailCode.objects.get(user=self.user).attempts, 0)

    def test_an_expired_code_does_not_work(self):
        back_in_time(self.user, timedelta(minutes=15, seconds=1))
        self.assertEqual(self.reset(self.code).data["code"], "code_expired")

    def test_only_the_newest_code_works(self):
        back_in_time(self.user, timedelta(seconds=61))
        self.ask()
        newest = code_in(mail.outbox[1])
        if newest != self.code:
            self.assertEqual(self.reset(self.code).data["code"], "code_wrong")
        self.assertEqual(self.reset(newest).status_code, 200)

    def test_an_address_without_an_account_answers_like_an_expired_code(self):
        response = self.reset(self.code, email="nobody@example.com")
        self.assertEqual(response.data["code"], "code_expired")

    def test_a_code_only_works_for_the_address_it_went_to(self):
        User.objects.filter(pk=self.user.pk).update(email="moved@example.com")
        self.assertEqual(self.reset(self.code, email="moved@example.com").data["code"], "code_expired")

    def test_a_confirmation_code_is_not_a_reset_code(self):
        EmailCode.objects.filter(user=self.user).delete()
        User.objects.filter(pk=self.user.pk).update(email_confirmed_at=None)
        self.user.refresh_from_db()
        with mock.patch.object(confirmation, "new_code", return_value="424242"):
            confirmation.send_code(self.user)
        self.assertEqual(self.reset("424242").data["code"], "code_expired")
        self.assertEqual(self.sign_in(OLD).status_code, 200)

    def test_a_reset_code_is_not_a_confirmation_code(self):
        User.objects.filter(pk=self.user.pk).update(email_confirmed_at=None)
        self.user.refresh_from_db()
        outcome = confirmation.check_code(self.user, self.code)
        self.assertEqual(outcome.status, confirmation.EXPIRED)

    def test_the_hashes_differ_by_purpose(self):
        self.assertNotEqual(
            confirmation.code_hash(self.user, "123456", EmailCode.PURPOSE_CONFIRM),
            confirmation.code_hash(self.user, "123456", EmailCode.PURPOSE_RESET),
        )

    def test_a_guests_scans_move_to_the_account(self):
        guest = User.objects.create_guest()
        Scan.objects.create(user=guest, target_url="https://postman-echo.com/get", status="complete")
        response = self.reset(self.code, guest_token=issue_tokens(guest)[0])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Scan.objects.filter(user=self.user).count(), 1)
        self.assertFalse(User.objects.filter(pk=guest.pk).exists())

    def test_thirty_attempts_an_hour_per_network(self):
        cache.clear()
        for _ in range(30):
            self.reset("abc")
        self.assertEqual(self.reset(self.code).status_code, 429)


class TemplateTests(Base):
    def test_the_email_says_what_happens_and_how_to_ignore_it(self):
        self.ask()
        body = mail.outbox[0].body
        self.assertIn("It works for 15 minutes", body)
        self.assertIn("signs you out everywhere else", body)
        self.assertIn("ignore this email: your password stays as it is", body)
