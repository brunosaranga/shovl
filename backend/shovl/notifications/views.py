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
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
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
