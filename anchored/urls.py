from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='anchored'),
    path('vwaps/', views.get_daily_equity, name='vwaps'),
    path('analogs/', views.get_analogs, name='analogs'),
    path('relative/', views.rolling_comparison, name='relative'),
    path('ratiogrid/', views.rolling_comparison_grid, name='grid'),
    path('ratiogridintl/', views.rolling_comparison_grid_intl, name='gridintl')
]