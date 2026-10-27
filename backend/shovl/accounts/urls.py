from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    EmailChangeView,
    EmailCodeView,
    EmailConfirmView,
    GuestSessionView,
    LoginView,
    MeView,
    RegisterView,
    UpgradeView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("guest/", GuestSessionView.as_view(), name="guest"),
    path("upgrade/", UpgradeView.as_view(), name="upgrade"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    # Confirming the email address with a 6-digit code (accounts/confirmation.py).
    path("email/code/", EmailCodeView.as_view(), name="email_code"),
    path("email/confirm/", EmailConfirmView.as_view(), name="email_confirm"),
    path("email/change/", EmailChangeView.as_view(), name="email_change"),
]
