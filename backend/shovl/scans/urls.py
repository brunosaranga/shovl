from django.urls import path
from .views import ScanListView, ScanCreateView, ScanDetailView, ScanStreamView, ScanPDFView

urlpatterns = [
    path("", ScanListView.as_view(), name="scan-list"),
    path("create/", ScanCreateView.as_view(), name="scan-create"),
    path("stream/", ScanStreamView.as_view(), name="scan-stream"),
    path("<int:pk>/", ScanDetailView.as_view(), name="scan-detail"),
    path("<int:pk>/pdf/", ScanPDFView.as_view(), name="scan-pdf"),
]