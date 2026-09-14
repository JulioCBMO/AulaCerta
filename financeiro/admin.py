from django.contrib import admin

from .models import Mensalidade, Pagamento


@admin.register(Mensalidade)
class MensalidadeAdmin(admin.ModelAdmin):
    list_display = ("aluno", "competencia", "valor_total", "data_vencimento", "status")
    list_filter = ("status",)
    search_fields = ("aluno__nome",)


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ("mensalidade", "valor_pago", "data_pagamento", "forma_pagamento")
    list_filter = ("forma_pagamento",)
