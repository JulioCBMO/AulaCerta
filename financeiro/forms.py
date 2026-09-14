from django import forms

from .models import Pagamento


class PagamentoForm(forms.Form):
    """US-30344 / Task 31622 — Registrar pagamento do aluno (CA-PAG-01)."""

    valor_pago = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0.01,
        label="Valor recebido (R$)",
        error_messages={"min_value": "Valor inválido: o valor pago deve ser maior que zero."},
    )
    forma_pagamento = forms.ChoiceField(choices=Pagamento.FormaPagamento.choices)
    data_pagamento = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), required=False
    )
    observacoes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
