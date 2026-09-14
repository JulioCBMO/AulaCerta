from django.contrib import admin

from .models import Professor


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ("user", "valor_hora_padrao", "dia_vencimento_padrao")
