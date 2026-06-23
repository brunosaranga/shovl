# from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from .models import Domain
from .serializers import DomainSerializer
from .verification import verify_dns, verify_file, is_practice_target

class DomainListCreateView(generics.ListCreateAPIView):
    serializer_class = DomainSerializer

    def get_queryset(self):
        return Domain.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class DomainVerifyView(APIView):
    def post(self, request, pk):
        try:
            domain = Domain.objects.get(pk=pk, user=request.user)
        except Domain.DoesNotExist:
            return Response({"error": "Domain not found."}, status=404)
        
        method = domain.verification_method
        token = domain.verification_token
        verified = False

        if method == "dns":
            verified = verify_dns(domain.hostname, token)
        elif method == "file":
            verified = verify_file(domain.hostname, token)

        if verified:
            domain.verified = True
            domain.verified_at = timezone.now()
            domain.save()
            return Response({"status": "verified"})
        
        return Response(
            {"status": "failed", "detail": "Verification record not found."},
            status=status.HTTP_400_BAD_REQUEST
        )