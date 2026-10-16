from django.urls import path
from .views import ScanListView, ScanCreateView, ScanDetailView, ScanStreamView, ScanPDFView, ScanControlView

urlpatterns = [
    path("", ScanListView.as_view(), name="scan-list"),
    path("create/", ScanCreateView.as_view(), name="scan-create"),
    path("stream/", ScanStreamView.as_view(), name="scan-stream"),
    path("<int:pk>/", ScanDetailView.as_view(), name="scan-detail"),
    path("<int:pk>/pdf/", ScanPDFView.as_view(), name="scan-pdf"),
    # Pause, resume and stop a running scan (scans/controls.py).
    path("<int:pk>/pause/", ScanControlView.as_view(control="pause"), name="scan-pause"),
    path("<int:pk>/resume/", ScanControlView.as_view(control="resume"), name="scan-resume"),
    path("<int:pk>/stop/", ScanControlView.as_view(control="stop"), name="scan-stop"),
]
