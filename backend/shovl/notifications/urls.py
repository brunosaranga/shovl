from django.urls import path

from .views import BellView, ReadAllView, ReadView

urlpatterns = [
    path("", BellView.as_view(), name="bell"),
    path("read-all/", ReadAllView.as_view(), name="bell-read-all"),
    path("<int:pk>/read/", ReadView.as_view(), name="bell-read"),
]
