from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path(
        "api/dashboard/estatisticas/",
        views.estatisticas_dashboard,
        name="estatisticas",
    ),
]
