"""
Confirming the email address with a 6-digit code (accounts/confirmation.py): sign-up and
upgrade send a code, the code screen's endpoints, every limit, the gate on the account's own
domains, the cleanup of accounts that never confirm, and the admin action.
"""
import re
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts import confirmation
from accounts.admin import UserAdmin
from accounts.models import EmailCode
from accounts.tokens import issue_tokens
from mailer.models import SentEmail
from mailer.services import address_hash
from scans.models import Scan

User = get_user_model()

PASSWORD = "a-long-enough-passphrase-42"
REGISTER = "/api/accounts/register/"
LOGIN = "/api/accounts/login/"
GUEST = "/api/accounts/guest/"
UPGRADE = "/api/accounts/upgrade/"
ME = "/api/accounts/me/"
SEND = "/api/accounts/email/code/"
CONFIRM = "/api/accounts/email/confirm/"
CHANGE = "/api/accounts/email/change/"

MAIL = dict(
    MAILER_ENABLED=True,
    EMAIL_DAILY_CAP=250,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_REPLY_TO="support@xikomu.com",
    CORS_ALLOWED_ORIGINS=["https://xikomu.com"],
)


def code_in(message):
    """The 6 digits in an email's subject."""
    return re.search(r"\b(\d{6})\b", message.subject).group(1)


def back_in_time(user, delta):
    """Move this account's codes and code emails `delta` into the past."""
    for row in EmailCode.objects.filter(user=user):
        EmailCode.objects.filter(pk=row.pk).update(
            created_at=row.created_at - delta, expires_at=row.expires_at - delta
        )
    for row in SentEmail.objects.filter(user=user):
        SentEmail.objects.filter(pk=row.pk).update(created_at=row.created_at - delta)


class Base(TestCase):
    def setUp(self):
        cache.clear()  # the sign-up throttle counts in the cache
        self.client = APIClient()

    def register(self, email="new@example.com"):
        response = self.client.post(
            REGISTER, {"email": email, "password": PASSWORD, "tos_agreed": True}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get(email=email)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)[0]}")
        return user

    def sign_in_as(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens(user)[0]}")

    def unconfirmed(self, email="old@example.com", **fields):
        """An account from before confirmation existed: unconfirmed, no deadline."""
        user = User.objects.create_user(email=email, password=PASSWORD, email_confirmed_at=None, **fields)
        self.sign_in_as(user)
        return user


@override_settings(**MAIL)
class SignUpTests(Base):
    def test_trusted_code_makes_confirmed_accounts_and_guests_never_are(self):
        self.assertIsNotNone(User.objects.create_user(email="a@example.com", password=PASSWORD).email_confirmed_at)
        self.assertIsNotNone(User.objects.create_superuser(email="b@example.com", password=PASSWORD).email_confirmed_at)
        guest = User.objects.create_guest()
        self.assertIsNone(guest.email_confirmed_at)
        self.assertIsNone(User.objects.create_user(email="c@x.com", is_guest=True, email_confirmed_at=timezone.now()).email_confirmed_at)

    def test_sign_up_is_unconfirmed_with_a_week_to_confirm_and_gets_a_code(self):
        before = timezone.now()
        user = self.register("New@Example.com".lower())

        self.assertIsNone(user.email_confirmed_at)
        self.assertGreaterEqual(user.confirm_by, before + timedelta(days=7) - timedelta(seconds=5))
        self.assertLessEqual(user.confirm_by, timezone.now() + timedelta(days=7))

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["new@example.com"])
        code = code_in(message)
        self.assertEqual(message.subject, f"xikomu: your code is {code}")
        self.assertIn(code, message.body)
        self.assertIn(code, message.alternatives[0][0])
        self.assertIn("deleted after 7 days", message.body)

        row = EmailCode.objects.get(user=user)
        self.assertNotIn(code, row.code_hash)
        self.assertEqual(row.sent_to, address_hash("new@example.com"))
        self.assertEqual(SentEmail.objects.get(user=user).kind, "verify_code")

    def test_sign_up_still_works_when_the_email_fails(self):
        with mock.patch("django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=OSError("down")):
            user = self.register()
        self.assertFalse(EmailCode.objects.filter(user=user).exists())
        data = self.client.get(ME).data
        self.assertFalse(data["email_confirmed"])
        self.assertIsNone(data["confirmation"]["code_sent_at"])

    def test_upgrade_is_unconfirmed_and_gets_a_code(self):
        guest_access = self.client.post(GUEST, {"tos_agreed": True}, format="json").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {guest_access}")
        response = self.client.post(
            UPGRADE, {"email": "up@example.com", "password": PASSWORD, "tos_agreed": True}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["email_confirmed"])
        user = User.objects.get(email="up@example.com")
        self.assertIsNone(user.email_confirmed_at)
        self.assertIsNotNone(user.confirm_by)
        self.assertEqual(mail.outbox[0].to, ["up@example.com"])

    def test_sign_in_says_whether_the_address_is_confirmed(self):
        User.objects.create_user(email="ok@example.com", password=PASSWORD)
        self.unconfirmed("no@example.com")
        ok = self.client.post(LOGIN, {"email": "ok@example.com", "password": PASSWORD}, format="json")
        no = self.client.post(LOGIN, {"email": "no@example.com", "password": PASSWORD}, format="json")
        self.assertTrue(ok.data["email_confirmed"])
        self.assertFalse(no.data["email_confirmed"])

    def test_sign_up_is_throttled_per_network(self):
        for n in range(20):
            self.client.credentials()
            self.register(f"n{n}@example.com")
        self.client.credentials()
        response = self.client.post(
            REGISTER, {"email": "n20@example.com", "password": PASSWORD, "tos_agreed": True}, format="json"
        )
        self.assertEqual(response.status_code, 429)
        self.assertFalse(User.objects.filter(email="n20@example.com").exists())


@override_settings(**MAIL)
class MeTests(Base):
    def test_unconfirmed_account_gets_the_code_screen_state(self):
        self.register()
        data = self.client.get(ME).data
        self.assertFalse(data["email_confirmed"])
        state = data["confirmation"]
        self.assertIsNotNone(state["confirm_by"])
        self.assertIsNotNone(state["code_sent_at"])
        self.assertIsNotNone(state["code_expires_at"])
        self.assertEqual(state["attempts_left"], 5)
        self.assertTrue(55 <= state["resend_in"] <= 60)

    def test_existing_account_has_no_deadline_and_no_code_yet(self):
        self.unconfirmed()
        state = self.client.get(ME).data["confirmation"]
        self.assertIsNone(state["confirm_by"])
        self.assertIsNone(state["code_sent_at"])
        self.assertEqual(state["resend_in"], 0)

    def test_confirmed_accounts_and_guests_have_no_state(self):
        self.sign_in_as(User.objects.create_user(email="ok@example.com", password=PASSWORD))
        data = self.client.get(ME).data
        self.assertTrue(data["email_confirmed"])
        self.assertIsNone(data["confirmation"])

        self.sign_in_as(User.objects.create_guest())
        data = self.client.get(ME).data
        self.assertFalse(data["email_confirmed"])
        self.assertIsNone(data["confirmation"])


@override_settings(**MAIL)
class ConfirmTests(Base):
    def test_the_right_code_confirms(self):
        user = self.register()
        code = code_in(mail.outbox[0])
        response = self.client.post(CONFIRM, {"code": code}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["email_confirmed"])
        self.assertIsNone(response.data["confirmation"])
        user.refresh_from_db()
        self.assertIsNotNone(user.email_confirmed_at)
        self.assertIsNone(user.confirm_by)
        self.assertFalse(EmailCode.objects.filter(user=user).exists())

    def test_spaces_and_dashes_are_ignored(self):
        self.register()
        code = code_in(mail.outbox[0])
        response = self.client.post(CONFIRM, {"code": f" {code[:3]}-{code[3:]} "}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_confirming_twice_is_harmless(self):
        self.register()
        code = code_in(mail.outbox[0])
        self.client.post(CONFIRM, {"code": code}, format="json")
        self.assertEqual(self.client.post(CONFIRM, {"code": code}, format="json").status_code, 200)

    def test_not_six_digits_is_refused_without_counting_a_try(self):
        user = self.register()
        for bad in ["12345", "1234567", "abcdef", "", None, "١٢٣٤٥٦"]:
            response = self.client.post(CONFIRM, {"code": bad}, format="json")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data["code"], "code_invalid")
        self.assertEqual(EmailCode.objects.get(user=user).attempts, 0)

    def test_five_wrong_tries_use_the_code_up(self):
        self.register()
        code = code_in(mail.outbox[0])
        wrong = "000000" if code != "000000" else "111111"
        for left in [4, 3, 2, 1]:
            response = self.client.post(CONFIRM, {"code": wrong}, format="json")
            self.assertEqual(response.data["code"], "code_wrong")
            self.assertEqual(response.data["attempts_left"], left)
        last = self.client.post(CONFIRM, {"code": wrong}, format="json")
        self.assertEqual(last.data["code"], "code_used_up")
        after = self.client.post(CONFIRM, {"code": code}, format="json")
        self.assertEqual(after.data["code"], "code_expired")
        self.assertIsNone(self.client.get(ME).data["confirmation"]["code_sent_at"])

    def test_an_expired_code_does_not_work(self):
        user = self.register()
        code = code_in(mail.outbox[0])
        back_in_time(user, timedelta(minutes=15, seconds=1))
        response = self.client.post(CONFIRM, {"code": code}, format="json")
        self.assertEqual(response.data["code"], "code_expired")

    def test_no_code_waiting(self):
        self.unconfirmed()
        response = self.client.post(CONFIRM, {"code": "123456"}, format="json")
        self.assertEqual(response.data["code"], "code_expired")

    def test_only_the_newest_code_works(self):
        user = self.register()
        first = code_in(mail.outbox[0])
        back_in_time(user, timedelta(seconds=61))
        self.assertEqual(self.client.post(SEND).status_code, 200)
        second = code_in(mail.outbox[1])
        if first != second:
            response = self.client.post(CONFIRM, {"code": first}, format="json")
            self.assertEqual(response.data["code"], "code_wrong")
        self.assertEqual(self.client.post(CONFIRM, {"code": second}, format="json").status_code, 200)

    def test_a_code_only_confirms_the_address_it_was_sent_to(self):
        user = self.register()
        code = code_in(mail.outbox[0])
        User.objects.filter(pk=user.pk).update(email="moved@example.com")
        response = self.client.post(CONFIRM, {"code": code}, format="json")
        self.assertEqual(response.data["code"], "code_expired")

    def test_codes_belong_to_one_account(self):
        alice = self.register("alice@example.com")
        alice_code = code_in(mail.outbox[0])
        self.client.credentials()
        self.register("bob@example.com")
        response = self.client.post(CONFIRM, {"code": alice_code}, format="json")
        if alice_code != code_in(mail.outbox[1]):
            self.assertEqual(response.data["code"], "code_wrong")
        alice.refresh_from_db()
        self.assertIsNone(alice.email_confirmed_at)

    def test_guests_and_strangers_are_turned_away(self):
        self.sign_in_as(User.objects.create_guest())
        for url in (SEND, CONFIRM, CHANGE):
            response = self.client.post(url, {}, format="json")
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.data["code"], "registration_required")
        self.client.credentials()
        for url in (SEND, CONFIRM, CHANGE):
            self.assertEqual(self.client.post(url, {}, format="json").status_code, 401)


@override_settings(**MAIL)
class SendTests(Base):
    def test_existing_account_asks_for_its_first_code(self):
        user = self.unconfirmed()
        response = self.client.post(SEND)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["confirmation"]["code_sent_at"])
        message = mail.outbox[0]
        self.assertEqual(message.to, ["old@example.com"])
        self.assertNotIn("deleted after 7 days", message.body)
        self.client.post(CONFIRM, {"code": code_in(message)}, format="json")
        user.refresh_from_db()
        self.assertIsNotNone(user.email_confirmed_at)

    def test_a_minute_between_codes(self):
        user = self.register()
        response = self.client.post(SEND)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["code"], "code_cooldown")
        self.assertTrue(1 <= response.data["retry_after"] <= 60)
        self.assertEqual(len(mail.outbox), 1)

        back_in_time(user, timedelta(seconds=61))
        self.assertEqual(self.client.post(SEND).status_code, 200)

    def test_ten_codes_a_day_per_account(self):
        user = self.unconfirmed()
        for _ in range(confirmation.CODES_PER_DAY):
            SentEmail.objects.create(
                kind="verify_code", user=user, to_hash="x" * 64, status=SentEmail.STATUS_SENT
            )
        back_in_time(user, timedelta(minutes=2))
        response = self.client.post(SEND)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["code"], "code_limit")
        self.assertIn("support@xikomu.com", response.data["detail"])

    def test_five_codes_a_day_to_one_address_whoever_asks(self):
        self.unconfirmed("target@example.com")
        for _ in range(5):
            SentEmail.objects.create(
                kind="verify_code", to_hash=address_hash("target@example.com"), status=SentEmail.STATUS_SENT
            )
        response = self.client.post(SEND)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["code"], "code_limit")
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(EmailCode.objects.exists())

    def test_a_failed_send_leaves_no_code_and_still_waits_a_minute(self):
        user = self.unconfirmed()
        with mock.patch("django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=OSError("down")):
            response = self.client.post(SEND)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "email_failed")
        self.assertFalse(EmailCode.objects.filter(user=user).exists())
        self.assertEqual(self.client.post(SEND).data["code"], "code_cooldown")

    @override_settings(MAILER_ENABLED=False)
    def test_email_switched_off_is_a_failure_to_send(self):
        self.unconfirmed()
        response = self.client.post(SEND)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "email_failed")

    def test_confirmed_accounts_get_no_code(self):
        self.sign_in_as(User.objects.create_user(email="ok@example.com", password=PASSWORD))
        response = self.client.post(SEND)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "already_confirmed")
        self.assertEqual(len(mail.outbox), 0)


@override_settings(**MAIL)
class ChangeAddressTests(Base):
    def change(self, email, password=PASSWORD):
        return self.client.post(CHANGE, {"email": email, "password": password}, format="json")

    def test_fixing_a_typo_moves_the_account_and_sends_a_code_at_once(self):
        user = self.register("typo@exmaple.com")
        old_code = code_in(mail.outbox[0])
        response = self.change("Right@Example.com")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.data["code_sent"])
        self.assertIsNone(response.data["send_problem"])
        self.assertEqual(response.data["email"], "right@example.com")
        user.refresh_from_db()
        self.assertEqual(user.email, "right@example.com")
        self.assertEqual(mail.outbox[1].to, ["right@example.com"])
        new_code = code_in(mail.outbox[1])
        if old_code != new_code:
            self.assertEqual(self.client.post(CONFIRM, {"code": old_code}, format="json").data["code"], "code_wrong")
        self.assertEqual(self.client.post(CONFIRM, {"code": new_code}, format="json").status_code, 200)

    def test_the_password_is_asked_again(self):
        user = self.register()
        response = self.change("other@example.com", password="not-it")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)
        user.refresh_from_db()
        self.assertEqual(user.email, "new@example.com")

    def test_an_address_another_account_uses_is_refused(self):
        User.objects.create_user(email="taken@example.com", password=PASSWORD)
        self.register()
        response = self.change("TAKEN@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["email"], ["Another account already uses this address."])

    def test_the_same_address_is_refused(self):
        self.register()
        response = self.change("NEW@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_three_addresses_a_day(self):
        user = self.register("a@example.com")
        self.assertEqual(self.change("b@example.com").status_code, 200)
        self.assertEqual(self.change("c@example.com").status_code, 200)
        response = self.change("d@example.com")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["code"], "address_limit")
        user.refresh_from_db()
        self.assertEqual(user.email, "c@example.com")
        # Going back to one already tried today is fine.
        self.assertEqual(self.change("a@example.com").status_code, 200)

    def test_a_failed_send_still_changes_the_address(self):
        user = self.register()
        with mock.patch("django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=OSError("down")):
            response = self.change("right@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["code_sent"])
        self.assertEqual(response.data["send_problem"]["code"], "email_failed")
        user.refresh_from_db()
        self.assertEqual(user.email, "right@example.com")

    def test_confirmed_accounts_cannot_use_it(self):
        self.sign_in_as(User.objects.create_user(email="ok@example.com", password=PASSWORD))
        response = self.change("other@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "already_confirmed")

    def test_sign_in_uses_the_new_address(self):
        self.register()
        self.change("right@example.com")
        self.client.credentials()
        ok = self.client.post(LOGIN, {"email": "right@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(ok.status_code, 200)


@override_settings(**MAIL)
class GateTests(Base):
    def test_unconfirmed_accounts_cannot_use_their_own_domains(self):
        self.unconfirmed()
        checks = [
            self.client.post("/api/domains/", {"hostname": "example.com"}, format="json"),
            self.client.post("/api/domains/1/verify/", {"method": "dns"}, format="json"),
            self.client.get("/api/watches/"),
            self.client.patch(ME, {"notifications_muted": True}, format="json"),
            self.client.post("/api/scans/create/", {"target_url": "https://example.com/api"}, format="json"),
            self.client.get("/api/scans/stream/", {"target_url": "https://example.com/api"}),
        ]
        for response in checks:
            self.assertEqual(response.status_code, 403, response.content)
            self.assertEqual(response.data["code"], "email_unconfirmed")

    def test_what_stays_open_while_unconfirmed(self):
        self.unconfirmed()
        self.assertEqual(self.client.get(ME).status_code, 200)
        self.assertEqual(self.client.get("/api/scans/").status_code, 200)
        self.assertEqual(self.client.get("/api/domains/").status_code, 200)
        self.assertEqual(self.client.get("/api/notifications/").status_code, 200)

    def test_confirming_opens_everything(self):
        self.register()
        self.client.post(CONFIRM, {"code": code_in(mail.outbox[0])}, format="json")
        response = self.client.post("/api/domains/", {"hostname": "example.com"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.client.patch(ME, {"notifications_muted": True}, format="json").status_code, 200)

    def test_guests_still_get_registration_required(self):
        self.sign_in_as(User.objects.create_guest())
        response = self.client.post("/api/domains/", {"hostname": "example.com"}, format="json")
        self.assertEqual(response.data["code"], "registration_required")


class CleanupTests(TestCase):
    def run_purge(self, *args):
        out = StringIO()
        call_command("purge_guests", *args, stdout=out)
        return out.getvalue()

    def account(self, email, **fields):
        fields.setdefault("email_confirmed_at", None)
        return User.objects.create_user(email=email, password=PASSWORD, **fields)

    def test_unconfirmed_accounts_go_after_their_deadline_with_their_scans(self):
        now = timezone.now()
        late = self.account("late@example.com", confirm_by=now - timedelta(minutes=1))
        Scan.objects.create(user=late, target_url="https://postman-echo.com/get", status="complete")
        in_time = self.account("soon@example.com", confirm_by=now + timedelta(days=1))
        existing = self.account("existing@example.com")  # from before: no deadline
        confirmed = User.objects.create_user(email="ok@example.com", password=PASSWORD)
        staff = self.account("staff@example.com", confirm_by=now - timedelta(days=1), is_staff=True)

        dry = self.run_purge("--dry-run")
        self.assertIn("Would delete 1 unconfirmed accounts past their deadline, 1 scans", dry)
        self.assertTrue(User.objects.filter(pk=late.pk).exists())

        out = self.run_purge()
        self.assertIn("Deleted 1 unconfirmed accounts past their deadline, 1 scans", out)
        self.assertFalse(User.objects.filter(pk=late.pk).exists())
        self.assertFalse(Scan.objects.filter(user_id=late.pk).exists())
        for kept in (in_time, existing, confirmed, staff):
            self.assertTrue(User.objects.filter(pk=kept.pk).exists(), kept.email)

    def test_an_account_that_confirmed_late_is_kept(self):
        user = self.account("late@example.com", confirm_by=timezone.now() - timedelta(days=1))
        User.objects.filter(pk=user.pk).update(email_confirmed_at=timezone.now())
        self.run_purge()
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_expired_codes_are_deleted(self):
        user = self.account("a@example.com")
        now = timezone.now()
        old = EmailCode.objects.create(
            user=user, purpose="confirm", sent_to="x", code_hash="y",
            created_at=now - timedelta(days=2), expires_at=now - timedelta(days=2) + timedelta(minutes=15),
        )
        fresh = EmailCode.objects.create(
            user=user, purpose="confirm", sent_to="x", code_hash="y", expires_at=now + timedelta(minutes=15)
        )
        out = self.run_purge()
        self.assertIn("Deleted 1 expired email codes", out)
        self.assertFalse(EmailCode.objects.filter(pk=old.pk).exists())
        self.assertTrue(EmailCode.objects.filter(pk=fresh.pk).exists())


class AdminTests(TestCase):
    def test_support_can_mark_an_address_confirmed(self):
        user = User.objects.create_user(
            email="a@example.com", password=PASSWORD, email_confirmed_at=None,
            confirm_by=timezone.now() + timedelta(days=7),
        )
        guest = User.objects.create_guest()
        EmailCode.objects.create(
            user=user, purpose="confirm", sent_to="x", code_hash="y", expires_at=timezone.now()
        )
        request = RequestFactory().post("/admin/")
        request.user = User.objects.create_superuser(email="boss@example.com", password=PASSWORD)
        request.session = {}
        request._messages = FallbackStorage(request)

        UserAdmin(User, AdminSite()).mark_confirmed(request, User.objects.filter(pk__in=[user.pk, guest.pk]))

        user.refresh_from_db()
        guest.refresh_from_db()
        self.assertIsNotNone(user.email_confirmed_at)
        self.assertIsNone(user.confirm_by)
        self.assertIsNone(guest.email_confirmed_at)
        self.assertFalse(EmailCode.objects.exists())


class CodeTests(TestCase):
    def test_codes_are_six_random_digits(self):
        codes = {confirmation.new_code() for _ in range(200)}
        self.assertTrue(all(len(c) == 6 and c.isdigit() for c in codes))
        self.assertGreater(len(codes), 190)

    def test_the_hash_depends_on_the_account(self):
        a = User.objects.create_user(email="a@example.com", password=PASSWORD)
        b = User.objects.create_user(email="b@example.com", password=PASSWORD)
        self.assertNotEqual(confirmation.code_hash(a, "123456"), confirmation.code_hash(b, "123456"))


class BusyCleanupTests(TestCase):
    def test_an_account_with_a_scan_running_waits_for_the_next_run(self):
        user = User.objects.create_user(
            email="late@example.com", password=PASSWORD, email_confirmed_at=None,
            confirm_by=timezone.now() - timedelta(minutes=1),
        )
        Scan.objects.create(user=user, target_url="https://postman-echo.com/get", status="running")
        call_command("purge_guests", stdout=StringIO())
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
