"""
Tests for how long sign-in tokens last.

Run with:  python manage.py test accounts
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

ONE_HOUR = 60 * 60
THIRTY_DAYS = 30 * 24 * 60 * 60


def lifetime_seconds(access):
    token = AccessToken(access)
    return token["exp"] - token["iat"]


class TokenLifetimeTests(TestCase):
    def configured(self):
        return settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()

    def test_the_default_is_longer_than_the_old_one_hour(self):
        self.assertGreater(self.configured(), ONE_HOUR)

    def test_sign_in_gets_the_configured_lifetime(self):
        User.objects.create_user("a@example.com", "v7!Kq2#mXp", tos_agreed=True)
        response = APIClient().post(
            "/api/accounts/login/",
            {"email": "a@example.com", "password": "v7!Kq2#mXp"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(lifetime_seconds(response.data["access"]), self.configured())

    def test_upgrading_gets_the_configured_lifetime(self):
        guest = User.objects.create_guest(tos_agreed=True)
        client = APIClient()
        client.force_authenticate(guest)
        response = client.post(
            "/api/accounts/upgrade/",
            {"email": "b@example.com", "password": "correct horse battery staple", "tos_agreed": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(lifetime_seconds(response.data["access"]), self.configured())

    def test_a_guest_token_still_lasts_thirty_days(self):
        response = APIClient().post("/api/accounts/guest/", {"tos_agreed": True}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(lifetime_seconds(response.data["access"]), THIRTY_DAYS)