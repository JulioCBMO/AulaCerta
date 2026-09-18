from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection

from agenda.models import Aula
from alunos.models import Aluno
from dashboard.models import IndicadorFinanceiro
from financeiro.models import Mensalidade, Pagamento


@pytest.mark.django_db
def test_seed_sprint1_e_idempotente(monkeypatch):
    monkeypatch.setenv("AULACERTA_SEED_PASSWORD", "SenhaLocal123!")
    saida = StringIO()

    call_command("seed_sprint1", stdout=saida)

    usuario = get_user_model().objects.get(username="demo_sprint1")
    assert usuario.check_password("SenhaLocal123!")
    assert Aluno.objects.filter(professor=usuario).count() == 3
    assert Aula.objects.filter(professor=usuario).count() == 2
    assert Mensalidade.objects.filter(aluno__professor=usuario).count() == 3
    assert Pagamento.objects.filter(mensalidade__aluno__professor=usuario).count() == 2

    quantidades_primeira_execucao = (
        get_user_model().objects.count(),
        Aluno.objects.count(),
        Aula.objects.count(),
        Mensalidade.objects.count(),
        Pagamento.objects.count(),
    )

    call_command("seed_sprint1", stdout=saida)

    quantidades_segunda_execucao = (
        get_user_model().objects.count(),
        Aluno.objects.count(),
        Aula.objects.count(),
        Mensalidade.objects.count(),
        Pagamento.objects.count(),
    )
    assert quantidades_segunda_execucao == quantidades_primeira_execucao

    carla = Aluno.objects.get(professor=usuario, cpf="33333333333")
    assert carla.saldo_devedor == Decimal("450.00")
    assert Mensalidade.objects.get(
        observacoes="[seed_sprint1] mensalidade_paga_ana"
    ).status == Mensalidade.Status.PAGO


@pytest.mark.django_db
class TestIndicadoresFinanceirosView:
    """Task 31772 - View SQL de agregacao financeira."""

    @pytest.fixture
    def indicadores(self):
        usuario_model = get_user_model()
        professor = usuario_model.objects.create_user(username="professor_view")
        outro_professor = usuario_model.objects.create_user(
            username="outro_professor_view"
        )

        aluno = Aluno.objects.create(
            professor=professor,
            nome="Aluno da View",
            cpf="44444444444",
            telefone="83999990000",
        )
        aluno_outro_professor = Aluno.objects.create(
            professor=outro_professor,
            nome="Aluno Isolado",
            cpf="55555555555",
            telefone="83999991111",
        )
        competencia = date(2026, 9, 1)

        mensalidade_parcial = Mensalidade.objects.create(
            aluno=aluno,
            competencia=competencia,
            valor_total=Decimal("100.00"),
            data_vencimento=date(2026, 9, 10),
            status=Mensalidade.Status.PENDENTE,
        )
        mensalidade_paga = Mensalidade.objects.create(
            aluno=aluno,
            competencia=competencia,
            valor_total=Decimal("200.00"),
            data_vencimento=date(2026, 9, 10),
            status=Mensalidade.Status.PAGO,
        )
        Mensalidade.objects.create(
            aluno=aluno,
            competencia=competencia,
            valor_total=Decimal("50.00"),
            data_vencimento=date(2026, 9, 5),
            status=Mensalidade.Status.VENCIDO,
        )
        Mensalidade.objects.create(
            aluno=aluno_outro_professor,
            competencia=competencia,
            valor_total=Decimal("500.00"),
            data_vencimento=date(2026, 9, 10),
            status=Mensalidade.Status.PENDENTE,
        )

        # Dois pagamentos para a mesma mensalidade comprovam que o JOIN nao
        # duplica o valor da cobranca no faturamento consolidado.
        Pagamento.objects.create(
            mensalidade=mensalidade_parcial,
            valor_pago=Decimal("30.00"),
            forma_pagamento=Pagamento.FormaPagamento.PIX,
        )
        Pagamento.objects.create(
            mensalidade=mensalidade_parcial,
            valor_pago=Decimal("20.00"),
            forma_pagamento=Pagamento.FormaPagamento.DINHEIRO,
        )
        Pagamento.objects.create(
            mensalidade=mensalidade_paga,
            valor_pago=Decimal("200.00"),
            forma_pagamento=Pagamento.FormaPagamento.TRANSFERENCIA,
        )

        return professor, outro_professor, competencia

    def test_view_existe_no_banco(self):
        with connection.cursor() as cursor:
            tabelas_e_views = connection.introspection.table_names(
                cursor, include_views=True
            )

        assert "dashboard_indicadores_financeiros" in tabelas_e_views

    def test_agrega_valores_sem_duplicar_mensalidades(self, indicadores):
        professor, _, competencia = indicadores

        resumo = IndicadorFinanceiro.objects.get(
            professor=professor,
            competencia=competencia,
        )

        assert resumo.total_mensalidades == 3
        assert resumo.faturamento_gerado == Decimal("350.00")
        assert resumo.valor_total_pago == Decimal("250.00")
        assert resumo.valor_pendente == Decimal("100.00")
        assert resumo.total_pendentes == 2
        assert resumo.total_vencidas == 1
        assert resumo.indice_inadimplencia == Decimal("28.6")

    def test_isola_os_indicadores_por_professor(self, indicadores):
        professor, outro_professor, competencia = indicadores

        assert IndicadorFinanceiro.objects.filter(
            professor=professor,
            competencia=competencia,
        ).count() == 1

        resumo_outro = IndicadorFinanceiro.objects.get(
            professor=outro_professor,
            competencia=competencia,
        )
        assert resumo_outro.total_mensalidades == 1
        assert resumo_outro.faturamento_gerado == Decimal("500.00")
        assert resumo_outro.valor_total_pago == Decimal("0.00")
        assert resumo_outro.valor_pendente == Decimal("500.00")
        assert resumo_outro.indice_inadimplencia == Decimal("100.0")
