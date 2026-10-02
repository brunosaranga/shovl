# from django.shortcuts import render
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from scans.limits import scans_remaining

from .serializers import RegisterSerializer, UpgradeSerializer, LoginSerializer
from .throttles import GuestCreationThrottle


User = get_user_model()

# Guests only get an access token (the frontend doesn't store a refresh token), so it has to last long enough for them to come back to their dashboard
GUEST_TOKEN_LIKETIME = timedelta(days=30)
# GUEST_TOKEN_LIFETIME is mispelled here - change if necessary but has to be across the board



# Create your views here.

class LoginView(TokenObtainPairView):
    # Same email + password sign-in as before. It also accepts an optional `guest_token` in the body and moves that guest's scans onto the account.
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class TooManySessions(Throttled):
    """
    A429 with a friendly message and a code the frontend can act on.
    """

    def __init__(self, wait=None):
        super().__init__(wait=wait)
        self.detail = {
            'detail': 'Too many new sessions from your network. Try again later, or create a free account.',
            'code': 'too_many_sessions',
            'retry_after': self.wait,
        }


class GuestSessionView(APIView):
    """
    POST /api/accounts/guest/   body: {"tos_agreed": true}

    Creates a guest account and returns a long-lived access token, so a first-time visitor can run a scan and find it on their dashboard. Consent is required: without it no account is created.
    
    """
    permission_classes = [permissions.AllowAny]
    # No authentication on purpose. An old or expired token in the request header would otherwise be rejected with a 401 before this view runs.
    authentication_classes = []

    # Stops anyone creating endless guests to get around the scan allowance.
    throttle_classes = [GuestCreationThrottle]

    def throttled(self, request, wait):
        raise TooManySessions(wait=wait)

    def post(self, request):
        data = request.data if isinstance(request.data, dict) else {}

        if data.get('tos_agreed') is not True:
            return Response(
                {'tos_agreed': ['You must confirm you have permission to test the target.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_guest(
            tos_agreed=True,
            tos_agreed_at=timezone.now(),
        )

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        access.set_exp(lifetime=GUEST_TOKEN_LIKETIME)

        return Response(
            {'access': str(access), 'refresh': str(refresh), 'is_guest': True},
            status=status.HTTP_201_CREATED,
        )




class UpgradeView(APIView):
    """
    POST /api/accounts/upgrade/     header: Authorization: Bearer <guest token>
    body: {"email"}: "...", "password": "...", "tos_agreed": true}

    Turns the calling guest into a registered user. The account keeps its id, so its scans stay attached. Returns a normal login token pair.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        with transaction.atomic():
            # Lock the row so two identical requests arriving together cannot both pass the guest check (this takes effect on Postgres).
            user = User.objects.select_for_update().get(pk=request.user.pk)

            if not user.is_guest:
                return Response(
                    {'detail': 'Only guest accounts can be upgraded.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

            serializer = UpgradeSerializer(
                data=request.data,
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.upgrade(user)

        refresh = RefreshToken.for_user(user)
        return Response(
            {'access': str(refresh.access_token), 'refresh': str(refresh), 'is_guest': False},
            status=status.HTTP_200_OK,
        )





class MeView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'id': request.user.id,
            'email': request.user.email,
            'is_guest': request.user.is_guest,
            # {"limit", "used", "remaining", "period"}, or null for accounts with no limit.
            'allowance': scans_remaining(request.user),
        })