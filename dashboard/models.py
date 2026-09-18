from django.conf import settings
from django.db import models


class IndicadorFinanceiro(models.Model):
    """Resumo financeiro mensal exposto pela view da Task 31772.

    A view é somente de leitura. A pré-agregação dos pagamentos ocorre no
    banco para que uma mensalidade com vários pagamentos seja contabilizada
    uma única vez no faturamento.
    """

    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="professor_id",
        on_delete=models.DO_NOTHING,
        related_name="+",
    )
    competencia = models.DateField()
    total_mensalidades = models.IntegerField()
    faturamento_gerado = models.DecimalField(max_digits=14, decimal_places=2)
    valor_total_pago = models.DecimalField(max_digits=14, decimal_places=2)
    valor_pendente = models.DecimalField(max_digits=14, decimal_places=2)
    total_pendentes = models.IntegerField()
    total_vencidas = models.IntegerField()
    indice_inadimplencia = models.DecimalField(max_digits=7, decimal_places=1)

    class Meta:
        managed = False
        db_table = "dashboard_indicadores_financeiros"
        ordering = ["professor_id", "competencia"]

    def __str__(self):
        return f"Indicadores de {self.competencia:%m/%Y}"
