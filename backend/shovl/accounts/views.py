# from django.shortcuts import render
from rest_framework import generics, permissions

from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


User = get_user_model()

# Create your views here.

class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from rest_framework.response import response
        return Response({
            'id': request.user.id,
            'email': request.user.email,
        })