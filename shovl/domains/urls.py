from django.urls import path
from .views import  DomainListCreateView, DomainVerifyView

urlpatterns = [
    path("", DomainListCreateView.as_view(), name="domain-list"),
    path("<int:pk>/verify/", DomainVerifyView.as_view(), name="domain-verify"),
]