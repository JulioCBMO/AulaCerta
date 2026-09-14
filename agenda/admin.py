from django.contrib import admin

from .models import Aula


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ("aluno", "professor", "data_hora_inicio", "status", "modalidade")
    list_filter = ("status", "modalidade", "professor")
    search_fields = ("aluno__nome",)
