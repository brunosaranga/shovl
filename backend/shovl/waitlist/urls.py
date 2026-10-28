from django.urls import path

from .views import ConfirmView, JoinView, LeaveView

urlpatterns = [
    path("", JoinView.as_view(), name="waitlist-join"),
    path("confirm/", ConfirmView.as_view(), name="waitlist-confirm"),
    path("leave/", LeaveView.as_view(), name="waitlist-leave"),
]
