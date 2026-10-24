from django.urls import path

from .views import WatchDetailView, WatchListView, WatchResumeView

urlpatterns = [
    path("", WatchListView.as_view(), name="watch-list"),
    path("<int:pk>/", WatchDetailView.as_view(), name="watch-detail"),
    path("<int:pk>/resume/", WatchResumeView.as_view(), name="watch-resume"),
]