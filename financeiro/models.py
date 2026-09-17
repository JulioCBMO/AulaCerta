from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from alunos.models import Aluno


class Mensalidade(models.Model):
    """
    Representa uma cobrança em aberto do aluno (mensalidade, pacote ou
    aula avulsa). A geração automática a partir do contrato é prevista
    para a Sprint 03; na Sprint 01, a mensalidade é lançada manualmente
    como base para o registro de pagamentos e para o cálculo de
    inadimplência.
    """

    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        PAGO = "PAGO", "Pago"
        VENCIDO = "VENCIDO", "Vencido"

    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name="mensalidades")
    competencia = models.DateField(help_text="Use o primeiro dia do mês de referência.")
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    observacoes = models.TextField(blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-competencia"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(valor_total__gt=0),
                name="mensalidade_valor_total_positivo",
            ),
        ]
        indexes = [
            models.Index(fields=["aluno", "status"], name="idx_mensalidade_aluno_status"),
            models.Index(fields=["data_vencimento", "status"], name="idx_mensalidade_venc_status"),
        ]

    def __str__(self):
        return f"{self.aluno} — {self.competencia:%m/%Y}"

    @property
    def valor_pago(self):
        total = self.pagamentos.aggregate(total=models.Sum("valor_pago"))["total"]
        return total or Decimal("0.00")

    @property
    def saldo(self):
        return self.valor_total - self.valor_pago

    def dias_em_atraso(self):
        if self.status == self.Status.PAGO:
            return 0
        delta = (timezone.localdate() - self.data_vencimento).days
        return max(delta, 0)


class Pagamento(models.Model):
    """
    US-30344 / Task 31622 — Registrar pagamento do aluno.

    Critérios de aceite implementados:
    CA-PAG-01: validação estrita de valor positivo.
    CA-PAG-02: a baixa transaciona a atualização do status da mensalidade
               para 'PAGO' e recalcula o saldo devedor do aluno.
    """

    class FormaPagamento(models.TextChoices):
        PIX = "PIX", "Pix"
        DINHEIRO = "DINHEIRO", "Dinheiro"
        CARTAO = "CARTAO", "Cartão"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferência"
        OUTRO = "OUTRO", "Outro"

    mensalidade = models.ForeignKey(
        Mensalidade, on_delete=models.CASCADE, related_name="pagamentos"
    )
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2)
    data_pagamento = models.DateField(default=timezone.localdate)
    forma_pagamento = models.CharField(max_length=15, choices=FormaPagamento.choices)
    observacoes = models.TextField(blank=True)
    data_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_registro"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(valor_pago__gt=0),
                name="pagamento_valor_pago_positivo",
            ),
        ]

    def __str__(self):
        return f"Pagamento de R$ {self.valor_pago} — {self.mensalidade}"

    def clean(self):
        # CA-PAG-01: valor estritamente positivo
        if self.valor_pago is None or self.valor_pago <= 0:
            raise ValidationError({"valor_pago": "Valor inválido: o valor pago deve ser maior que zero."})

    @classmethod
    @transaction.atomic
    def registrar(cls, mensalidade, valor_pago, forma_pagamento, data_pagamento=None, observacoes=""):
        """
        Cenário BDD (Task 31622):
        Dado uma mensalidade pendente; quando o valor recebido é registrado
        com sucesso; então o status da mensalidade muda para 'PAGO' e o
        saldo devedor do aluno é debitado no montante correspondente.
        """
        pagamento = cls(
            mensalidade=mensalidade,
            valor_pago=valor_pago,
            forma_pagamento=forma_pagamento,
            data_pagamento=data_pagamento or timezone.localdate(),
            observacoes=observacoes,
        )
        pagamento.full_clean()
        pagamento.save()

        aluno = mensalidade.aluno
        aluno.saldo_devedor = max(aluno.saldo_devedor - pagamento.valor_pago, Decimal("0.00"))
        aluno.save(update_fields=["saldo_devedor"])

        if mensalidade.saldo <= 0:
            mensalidade.status = Mensalidade.Status.PAGO
            mensalidade.save(update_fields=["status"])

        return pagamento
