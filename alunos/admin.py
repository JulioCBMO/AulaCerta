from django.contrib import admin

from .models import Aluno


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "professor", "situacao", "data_cadastro")
    list_filter = ("situacao", "professor")
    search_fields = ("nome", "cpf")
