from django.urls import path
from .views import buy_data
from .views_api import DataPlanByCategory

urlpatterns = [
    path("buy/", buy_data, name="buy_data"),
    path("plans", DataPlanByCategory.as_view(), name="plans_by_category"),
]
