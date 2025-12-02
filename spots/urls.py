from django.urls import path
from .views import SpotListView, SpotDetailView, SpotCreateView, SpotUpdateView, SpotDeleteView, SpotMapDataView, SpotListLoadMoreView

app_name = "spots"
urlpatterns = [
    path("", SpotListView.as_view(), name="spot_list"),
    path("load-more/", SpotListLoadMoreView.as_view(), name="spot_list_load_more"),
    path("new/", SpotCreateView.as_view(), name="spot_create"),
    path("map-data/", SpotMapDataView.as_view(), name="spot_map_data"),
    path("<slug:slug>/", SpotDetailView.as_view(), name="spot_detail"),
    path("<slug:slug>/edit/", SpotUpdateView.as_view(), name="spot_update"),
    path("<slug:slug>/delete/", SpotDeleteView.as_view(), name="spot_delete"),
]
