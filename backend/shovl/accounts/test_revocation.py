"""
Tests for revoking tokens: upgrading a guest must sign out the guest token.

Run with:  python manage.py test accounts
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from accounts.tokens import TOKEN_VERSION_CLAIM, issue_tokens, token_version_of
from scans.models import Scan

User = get_user_model()

GUEST = "/api/accounts/guest/"
UPGRADE = "/api/accounts/upgrade/"
LOGIN = "/api/accounts/login/"
ME = "/api/accounts/me/"
REFRESH = "/api/accounts/token/refresh/"

PASSWORD = "correct horse battery staple"
UPGRADE_BODY = {"email": "real@example.com", "password": PASSWORD, "tos_agreed": True}


def bearer(token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def new_guest_session():
    response = APIClient().post(GUEST, {"tos_agreed": True}, format="json")
    assert response.status_code == 201, response.data
    return response.data["access"], response.data["refresh"]


class UpgradeRevokesTheGuestTokenTests(TestCase):
    def test_the_guest_token_works_before_the_upgrade(self):
        access, _ = new_guest_session()
        self.assertEqual(bearer(access).get(ME).status_code, 200)

    def test_the_guest_access_token_is_refused_after_the_upgrade(self):
        guest_access, _ = new_guest_session()
        self.assertEqual(bearer(guest_access).post(UPGRADE, UPGRADE_BODY, format="json").status_code, 200)

        response = bearer(guest_access).get(ME)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["detail"].code, "token_revoked")
        self.assertIn("sign in again", str(response.data["detail"]).lower())

    def test_the_guest_refresh_token_cannot_bring_the_session_back(self):
        guest_access, guest_refresh = new_guest_session()
        bearer(guest_access).post(UPGRADE, UPGRADE_BODY, format="json")

        renewed = APIClient().post(REFRESH, {"refresh": guest_refresh}, format="json")
        if renewed.status_code == 200:       # a new access token is issued, but it carries the old version
            self.assertEqual(bearer(renewed.data["access"]).get(ME).status_code, 401)
        else:
            self.assertEqual(renewed.status_code, 401)

    def test_the_new_tokens_from_the_upgrade_work(self):
        guest_access, _ = new_guest_session()
        upgraded = bearer(guest_access).post(UPGRADE, UPGRADE_BODY, format="json")

        me = bearer(upgraded.data["access"]).get(ME)
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["email"], "real@example.com")
        self.assertFalse(me.data["is_guest"])

    def test_the_new_refresh_token_renews_the_session(self):
        guest_access, _ = new_guest_session()
        upgraded = bearer(guest_access).post(UPGRADE, UPGRADE_BODY, format="json")

        renewed = APIClient().post(REFRESH, {"refresh": upgraded.data["refresh"]}, format="json")
        self.assertEqual(renewed.status_code, 200)
        self.assertEqual(bearer(renewed.data["access"]).get(ME).status_code, 200)

    def test_scans_stay_attached_to_the_account(self):
        guest_access, _ = new_guest_session()
        user = User.objects.get(is_guest=True)
        Scan.objects.create(user=user, target_url="https://postman-echo.com")
        upgraded = bearer(guest_access).post(UPGRADE, UPGRADE_BODY, format="json")

        self.assertEqual(upgraded.status_code, 200)
        self.assertEqual(Scan.objects.filter(user__email="real@example.com").count(), 1)

    def test_the_version_goes_up_by_one(self):
        guest_access, _ = new_guest_session()
        user = User.objects.get(is_guest=True)
        self.assertEqual(user.token_version, 0)
        bearer(guest_access).post(UPGRADE, UPGRADE_BODY, format="json")
        user.refresh_from_db()
        self.assertEqual(user.token_version, 1)

    def test_a_refused_upgrade_leaves_the_guest_token_working(self):
        guest_access, _ = new_guest_session()
        weak = dict(UPGRADE_BODY, password="qwertyuiop")
        self.assertEqual(bearer(guest_access).post(UPGRADE, weak, format="json").status_code, 400)

        self.assertEqual(bearer(guest_access).get(ME).status_code, 200)
        self.assertEqual(User.objects.get(is_guest=True).token_version, 0)

    def test_the_old_token_cannot_upgrade_again(self):
        guest_access, _ = new_guest_session()
        bearer(guest_access).post(UPGRADE, UPGRADE_BODY, format="json")
        again = bearer(guest_access).post(UPGRADE, dict(UPGRADE_BODY, email="other@example.com"), format="json")
        self.assertEqual(again.status_code, 401)
        self.assertFalse(User.objects.filter(email="other@example.com").exists())

    def test_a_registered_user_cannot_upgrade_with_the_new_token_either(self):
        guest_access, _ = new_guest_session()
        upgraded = bearer(guest_access).post(UPGRADE, UPGRADE_BODY, format="json")
        again = bearer(upgraded.data["access"]).post(UPGRADE, UPGRADE_BODY, format="json")
        self.assertEqual(again.status_code, 403)

    def test_revoked_tokens_are_refused_on_the_scan_endpoints_too(self):
        guest_access, _ = new_guest_session()
        bearer(guest_access).post(UPGRADE, UPGRADE_BODY, format="json")
        for path in ("/api/scans/", "/api/domains/"):
            self.assertEqual(bearer(guest_access).get(path).status_code, 401, path)


class TokensCarryTheVersionTests(TestCase):
    def test_guest_tokens_carry_version_zero(self):
        access, refresh = new_guest_session()
        self.assertEqual(AccessToken(access)[TOKEN_VERSION_CLAIM], 0)
        self.assertEqual(RefreshToken(refresh)[TOKEN_VERSION_CLAIM], 0)

    def test_the_upgrade_tokens_carry_the_new_version(self):
        guest_access, _ = new_guest_session()
        upgraded = bearer(guest_access).post(UPGRADE, UPGRADE_BODY, format="json")
        self.assertEqual(AccessToken(upgraded.data["access"])[TOKEN_VERSION_CLAIM], 1)
        self.assertEqual(RefreshToken(upgraded.data["refresh"])[TOKEN_VERSION_CLAIM], 1)

    def test_sign_in_tokens_carry_the_current_version(self):
        user = User.objects.create_user("a@example.com", PASSWORD, tos_agreed=True)
        user.token_version = 3
        user.save()
        response = APIClient().post(LOGIN, {"email": "a@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(AccessToken(response.data["access"])[TOKEN_VERSION_CLAIM], 3)
        self.assertEqual(RefreshToken(response.data["refresh"])[TOKEN_VERSION_CLAIM], 3)
        self.assertEqual(bearer(response.data["access"]).get(ME).status_code, 200)

    def test_the_guest_token_keeps_its_thirty_day_life(self):
        access, _ = new_guest_session()
        token = AccessToken(access)
        self.assertEqual(token["exp"] - token["iat"], 30 * 24 * 60 * 60)


class TokensFromBeforeThisChangeTests(TestCase):
    """Tokens issued before versions existed have no claim. They must not be signed out."""

    def old_style_access(self, user):
        refresh = RefreshToken.for_user(user)     # no version claim, as before
        return str(refresh.access_token)

    def test_a_token_without_a_version_works_for_a_version_zero_account(self):
        user = User.objects.create_user("old@example.com", PASSWORD, tos_agreed=True)
        token = self.old_style_access(user)
        self.assertNotIn(TOKEN_VERSION_CLAIM, AccessToken(token))
        self.assertEqual(bearer(token).get(ME).status_code, 200)

    def test_a_token_without_a_version_is_refused_once_the_account_is_upgraded(self):
        guest = User.objects.create_guest(tos_agreed=True)
        old_token = self.old_style_access(guest)
        self.assertEqual(bearer(old_token).get(ME).status_code, 200)

        response = bearer(old_token).post(UPGRADE, UPGRADE_BODY, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(bearer(old_token).get(ME).status_code, 401)


class RevokingAnyAccountTests(TestCase):
    def test_raising_the_version_signs_out_every_earlier_token(self):
        user = User.objects.create_user("a@example.com", PASSWORD, tos_agreed=True)
        access, refresh = issue_tokens(user)
        self.assertEqual(bearer(access).get(ME).status_code, 200)

        user.token_version += 1
        user.save(update_fields=["token_version"])

        self.assertEqual(bearer(access).get(ME).status_code, 401)
        fresh_access, _ = issue_tokens(user)
        self.assertEqual(bearer(fresh_access).get(ME).status_code, 200)

    def test_one_accounts_revocation_does_not_affect_another(self):
        first = User.objects.create_user("a@example.com", PASSWORD, tos_agreed=True)
        second = User.objects.create_user("b@example.com", PASSWORD, tos_agreed=True)
        second_access, _ = issue_tokens(second)

        first.token_version += 1
        first.save(update_fields=["token_version"])
        self.assertEqual(bearer(second_access).get(ME).status_code, 200)

    def test_token_version_of_reads_a_missing_claim_as_zero(self):
        self.assertEqual(token_version_of({}), 0)
        self.assertEqual(token_version_of({"tv": 4}), 4)