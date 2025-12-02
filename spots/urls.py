from django.urls import path
from .views import SpotCreateView

urlpatterns = [
    # path('', SpotListView.as_view(), name='spot_list'),
    path('new/', SpotCreateView.as_view(), name='spot_create'),
    # path('<slug:slug>/', SpotDetailView.as_view(), name='spot_detail'),
]