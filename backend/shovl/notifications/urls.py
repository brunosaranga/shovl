from django.urls import path

from .views import BellView, EmailOffView, ReadAllView, ReadView

urlpatterns = [
    path("", BellView.as_view(), name="bell"),
    path("read-all/", ReadAllView.as_view(), name="bell-read-all"),
    path("<int:pk>/read/", ReadView.as_view(), name="bell-read"),
    # The "turn these emails off" link in murindzi's emails (notifications/emails.py).
    path("email-off/", EmailOffView.as_view(), name="email-off"),
]
