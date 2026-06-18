# from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from urllib.parse import urlparse
import os

from .models import Scan
from .serializers import ScanSerializer
from domains.models import Domain
from domains.verification import is_practice_target
from scanner.engine import run_scan
from scanner.report import format_report
from reporter.generator import generate_pdf



# Create your views here.
class ScanListView(generics.ListAPIView):
    serializer_class = ScanSerializer

    def get_queryset(self):
        return Scan.objects.filter(user=self.request.user).order_by("-created_at")
    

class ScanCreateView(APIView):
    def post(self, request):
        target_url = request.data.get("target_url")
        verbose = request.data.get("verbose", False)
        suggest_fix = request.data.get("suggest_fix", False)

        # Validate URL provided
        if not target_url:
            return Response({"error": "target_url is required."}, status=400)
        
        # Validate URL format
        parsed = urlparse(target_url)
        if not parsed.scheme or not parsed.netloc:
            return Response(
                {"error": "Invalied URL format. Include http:// or https://"}
            )
        
        # Check ToS agreement
        if not request.user.tos_agreed:
            return Response(
                {"error": "You must agree to the terms of service before scanning."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verify ownership unless practice target
        if not is_practice_target(target_url):
            hostname = urlparse(target_url).hostname
            domain = Domain.objects.filter(
                user=request.user,
                hostname=hostname,
                verified=True
            ).first()

            if not domain:
                return Response({
                    "error": "Domain not verified.",
                    "detail": "Please verify ownership of this domain before scanning."
                })
            
        # Create scan record
        scan = Scan.objects.create(
            user=request.user,
            target_url=target_url,
            verbose=verbose,
            suggest_fix=suggest_fix,
            status="running"
        )

        try:
            raw = run_scan(target_url, verbose=verbose, suggest_fix=suggest_fix)
            report = format_report(raw)

            pdf_path = f"reports/scan_{scan.id}.pdf"
            os.makedirs("reports", exist_ok=True)
            generate_pdf(report, pdf_path)

            scan.status = "complete"
            scan.risk_score = report["meta"]["risk_score"]
            scan.results = report
            scan.pdf_path = pdf_path
            scan.completed_at = timezone.now()
            scan.save()

            return Response(ScanSerializer(scan).data, status=201)
        
        except Exception as e:
            scan.status = "failed"
            scan.save()
            return Response(
                {"error": f"Scan failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ScanDetailView(generics.RetrieveAPIView):
    serializers_class = ScanSerializer
    permission_classes = [IsAuthenticated]