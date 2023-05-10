from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_daily_equity, name='anchored'),

]