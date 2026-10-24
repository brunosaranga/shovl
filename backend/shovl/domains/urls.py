from django.urls import path
from .views import DomainDetailView, DomainListCreateView, DomainVerifyView, PendingDomainsView

urlpatterns = [
    path("", DomainListCreateView.as_view(), name="domain-list"),
    path("pending/", PendingDomainsView.as_view(), name="domain-pending"),
    path("<int:pk>/", DomainDetailView.as_view(), name="domain-detail"),
    path("<int:pk>/verify/", DomainVerifyView.as_view(), name="domain-verify"),
]