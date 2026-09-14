from django.urls import path

from . import views

app_name = "financeiro"

urlpatterns = [
    path("mensalidades/", views.listar_mensalidades, name="mensalidades"),
    path("mensalidades/<int:mensalidade_id>/pagar/", views.registrar_pagamento, name="pagar"),
    path("inadimplentes/", views.identificar_inadimplentes, name="inadimplentes"),
]
