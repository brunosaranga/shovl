# from django.shortcuts import render
from django.db import IntegrityError
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from accounts.permissions import IsRegisteredUser
from watch.services import domain_verified_again
from .models import Domain
from .serializers import DomainSerializer
from .verification import verify_dns, verify_file, is_practice_target

class DomainListCreateView(generics.ListCreateAPIView):
    serializer_class = DomainSerializer

    def get_permissions(self):
        # Adding a domain needs a registered account. Listing stays open to guests: they simply get an empty list.
        if self.request.method == 'POST':
            return [IsRegisteredUser()]
        return super().get_permissions()

    def get_queryset(self):
        return Domain.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except IntegrityError:
            # Two identical requests racing past the serializer check.
            raise ValidationError({"hostname": ["You have already added this domain."]})

class DomainVerifyView(APIView):
    permission_classes = [IsRegisteredUser]
    
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
            # shovl watch: watches paused by rule A start again.
            domain_verified_again(domain)
            return Response({"status": "verified"})
        
        return Response(
            {"status": "failed", "detail": "Verification record not found."},
            status=status.HTTP_400_BAD_REQUEST
        )


# The unverified cache: domains added on the verify page but never verified (also the ones
# shovl watch's rule A put back to pending). Verified domains can't be removed here yet.
DOMAIN_NOT_FOUND = {"detail": "Domain not found.", "code": "not_found"}
DOMAIN_VERIFIED = {
    "detail": "Verified domains can't be removed here yet.",
    "code": "domain_verified",
}


class DomainDetailView(APIView):
    """DELETE /api/domains/<id>/   remove one pending domain (and any watch on it). 204."""
    permission_classes = [IsRegisteredUser]

    def delete(self, request, pk):
        domain = Domain.objects.filter(pk=pk, user=request.user).first()
        if domain is None:
            return Response(DOMAIN_NOT_FOUND, status=status.HTTP_404_NOT_FOUND)
        if domain.verified:
            return Response(DOMAIN_VERIFIED, status=status.HTTP_409_CONFLICT)
        domain.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PendingDomainsView(APIView):
    """DELETE /api/domains/pending/   empty the unverified cache. 200 {"removed": n}."""
    permission_classes = [IsRegisteredUser]

    def delete(self, request):
        pending = Domain.objects.filter(user=request.user, verified=False)
        removed = pending.count()
        pending.delete()
        return Response({"removed": removed})
