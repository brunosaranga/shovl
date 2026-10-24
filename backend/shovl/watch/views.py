"""

The watch endpoints. Registered accounts only: guests get the usual 403 with code "registration_regquired;, and someone not signed in get a 401.

    GET     /api/watches/           the account's watched APIs, for Settings
    POST    /api/watches/           {"scan": <id>, "instead": false}        watch the scan's API
    PATCH   /api/watches/           {"active": true | false}                turn one API on or off
    POST /api/watches/<id>/resume                                           start a paused watch again

Refusals carry {detail, code}, like the scan endpoints: 404 "not found", 400 field errors, and from services.WatchRefused: 409 "plan_full" (with can_swap and watch_slots), 403 "domain_not_verified", 400 "practice_target".

"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsRegisteredUser
from scans.models import Scan

from . import services
from .models import Watch
from .serializers import WatchSerializer

WATCH_NOT_FOUND = {"detail": "Watch not found.", "code": "not_found"}
SCAN_NOT_FOUND = {"detail": "Scan not found.", "code": "not_found"}

def _body(request):
    return request.data if isinstance(request.data, dict) else {}

def _serialize(watch, user):
    return WatchSerializer(watch, context={"in_plan": services.in_plan_ids(user)}).data


class WatchListView(APIView):
    permission_classes = [IsRegisteredUser]

    def get(self, request):
        watches = Watch.objects.filter(user=request.user)
        context = {"in_plan": services.in_plan_ids(request.user)}
        return Response(WatchSerializer(watches, many=True, context=context).data)

    def post(self, request):
        data = _body(request)
        scan_id = data.get("scan")
        instead = data.get("instead", False)
        # bool is a kind of int in Python, so true would otherwise pass as scan 1.
        if isinstance(scan_id, bool) or not isinstance(scan_id, int):
            return Response({"scan": ["The id of one of your scans."]}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(instead, bool):
            return Response({"instead": ["Must be true or false."]}, status=status.HTTP_400_BAD_REQUEST)

        scan = Scan.objects.filter(pk=scan_id, user=request.user).first()
        if scan is None:
            return Response(SCAN_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)

        try:
            watch, changed = services.watch_scan(request.user, scan, instead=instead)
        except services.WatchRefused as refused:
            return Response(refused.as_response_data(), status=refused.http_status)

        return Response(
            {"watch": _serialize(watch, request.user), "state": services.scan_watch_state(scan)},
            status=status.HTTP_201_CREATED if changed else status.HTTP_200_OK,
        )


class WatchDetailView(APIView):
    permission_classes = [IsRegisteredUser]

    def patch(self, request, pk):
        watch = Watch.objects.filter(pk=pk, user=request.user).first()
        if watch is None:
            return Response(WATCH_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)

        active = _body(request).get("active")
        if not isinstance(active, bool):
            return Response({"active": ["Must be true or false."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            services.set_active(request.user, watch, active)
        except services.WatchRefused as refused:
            return Response(refused.as_response_data(), status=refused.http_status)
        return Response(_serialize(watch, request.user))


class WatchResumeView(APIView):
    permission_classes = [IsRegisteredUser]

    def post(self, request, pk):
        watch = Watch.objects.filter(pk=pk, user=request.user).first()
        if watch is None:
            return Response(WATCH_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        services.resume_watch(watch)
        return Response(_serialize(watch, request.user))

        