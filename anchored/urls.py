from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='anchored'),
    path('vwaps/', views.get_daily_equity, name='vwaps'),
]