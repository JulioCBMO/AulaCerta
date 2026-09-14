from django.urls import path

from . import views

app_name = "alunos"

urlpatterns = [
    path("", views.listar_alunos, name="listar"),
    path("novo/", views.cadastrar_aluno, name="cadastrar"),
    path("<int:pk>/", views.detalhe_aluno, name="detalhe"),
    path("<int:pk>/editar/", views.editar_aluno, name="editar"),
]
