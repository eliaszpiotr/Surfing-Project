from django.urls import path
from .views import SpotListView, SpotDetailView, SpotCreateView, SpotMapDataView

app_name = "spots"

urlpatterns = [
    path("", SpotListView.as_view(), name="spot_list"),
    path("new/", SpotCreateView.as_view(), name="spot_create"),
    path("map-data/", SpotMapDataView.as_view(), name="spot_map_data"),
    path("<slug:slug>/", SpotDetailView.as_view(), name="spot_detail"),
]