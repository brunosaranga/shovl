from django.urls import path
from .views import ScanListView, ScanCreateView, ScanDetailView

urlpatterns = [
    path("", ScanListView.as_view(), name="scan-list"),
    path("create/", ScanCreateView.as_view(), name="scan-create"),
    path("<int:pk>/", ScanDetailView.as_view(), name="scan-detail")
]