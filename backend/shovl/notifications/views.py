"""
The bell. Any signed-in account; guests simply get an empty bell.

    GET  /api/notifications/             the bell, newest news first
         ?before=<id>                    older news (the next page)
    POST /api/notifications/<id>/read/   one item read (opening it)
    POST /api/notifications/read-all/    every item read

The mute is the account's notifications_muted (PATCH /api/accounts/me/).
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import emails, services
from .models import Notification
from .serializers import NotificationSerializer

PAGE = 30
NOT_FOUND = {"detail": "Notification not found.", "code": "not_found"}


class BellView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        news = Notification.objects.filter(user=user)

        before = request.query_params.get("before")
        if before is not None:
            if not before.isdigit():
                return Response(
                    {"before": ["The id of a notification."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            news = news.filter(pk__lt=int(before))

        page = list(news.order_by("-pk")[:PAGE + 1])
        needs = services.needs_action(user)
        unread = services.unread_news(user)
        return Response({
            "badge": services.badge(user, needs=needs, unread=unread),
            "muted": user.notifications_muted,
            "needs_action": needs,
            "news": NotificationSerializer(page[:PAGE], many=True).data,
            "news_unread": unread,
            "has_more": len(page) > PAGE,
        })


class ReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        item = Notification.objects.filter(pk=pk, user=request.user).first()
        if item is None:
            return Response(NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        if item.read_at is None:
            item.read_at = timezone.now()
            item.save(update_fields=["read_at"])
        return Response(NotificationSerializer(item).data)


class ReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        marked = Notification.objects.filter(
            user=request.user, read_at__isnull=True
        ).update(read_at=timezone.now())
        return Response({"marked": marked})


class EmailOffView(APIView):
    """
    POST /api/notifications/email-off/   {"token": "..."}   (no sign-in needed)

    The "turn these emails off" link in murindzi's alert emails opens a page on the site
    (/email-off), which sends its token here once the person clicks. A genuine token turns
    off that account's alert emails (User.email_alerts) and answers 200 {"done": true};
    anything else 400 {"code": "link_invalid"}. It never says which account, or whether it
    was already off.
    """
    permission_classes = [AllowAny]
    # A stale sign-in token in the header must never get in the way of this.
    authentication_classes = []

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}
        if emails.turn_off(data.get("token")):
            return Response({"done": True})
        return Response(
            {
                "detail": "This link isn't valid. You can turn murindzi's emails off in settings.",
                "code": "link_invalid",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
