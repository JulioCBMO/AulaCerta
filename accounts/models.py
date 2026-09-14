from django.conf import settings
from django.db import models


class Professor(models.Model):
    """
    Extensão do usuário padrão do Django (contrib.auth.User) com as
    preferências do professor citadas na proposta (item 4.1).

    Observação de escopo: o cadastro/login completo do professor (Épico
    "Gestão de Autenticação e Conta") está planejado para a Sprint 03.
    Este modelo mínimo existe apenas para suportar o isolamento de dados
    entre professores, exigido como requisito não funcional desde a
    Sprint 01 (toda entidade de aluno/agenda/financeiro é vinculada a um
    professor).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="professor",
    )
    valor_hora_padrao = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Valor padrão da hora-aula, usado quando o aluno não tem valor próprio definido.",
    )
    antecedencia_minima_cancelamento_horas = models.PositiveIntegerField(
        default=24,
        help_text="Antecedência mínima (em horas) para cancelamento sem cobrança.",
    )
    dia_vencimento_padrao = models.PositiveSmallIntegerField(default=10)

    def __str__(self):
        return f"Professor: {self.user.get_username()}"
