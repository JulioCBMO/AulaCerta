from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.urls import reverse

from alunos.models import Aluno
from dashboard.models import IndicadorFinanceiro
from financeiro.models import Mensalidade, Pagamento


@pytest.fixture
def cenario_consistencia():
    usuario_model = get_user_model()
    professor = usuario_model.objects.create_user(username="professor_qa")
    outro_professor = usuario_model.objects.create_user(username="professor_qa_isolado")

    aluno = Aluno.objects.create(
        professor=professor,
        nome="Aluno QA",
        cpf="66666666666",
        telefone="83999992222",
        saldo_devedor=Decimal("200.00"),
    )
    aluno_isolado = Aluno.objects.create(
        professor=outro_professor,
        nome="Aluno QA Isolado",
        cpf="77777777777",
        telefone="83999993333",
        saldo_devedor=Decimal("700.00"),
    )

    setembro = date(2026, 9, 1)
    outubro = date(2026, 10, 1)

    mensalidade_paga = Mensalidade.objects.create(
        aluno=aluno,
        competencia=setembro,
        valor_total=Decimal("200.00"),
        data_vencimento=date(2026, 9, 10),
        status=Mensalidade.Status.PAGO,
    )
    mensalidade_parcial = Mensalidade.objects.create(
        aluno=aluno,
        competencia=setembro,
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 9, 10),
        status=Mensalidade.Status.PENDENTE,
    )
    Mensalidade.objects.create(
        aluno=aluno,
        competencia=setembro,
        valor_total=Decimal("100.00"),
        data_vencimento=date(2026, 9, 5),
        status=Mensalidade.Status.VENCIDO,
    )
    Mensalidade.objects.create(
        aluno=aluno,
        competencia=outubro,
        valor_total=Decimal("900.00"),
        data_vencimento=date(2026, 10, 10),
        status=Mensalidade.Status.PENDENTE,
    )
    Mensalidade.objects.create(
        aluno=aluno_isolado,
        competencia=setembro,
        valor_total=Decimal("700.00"),
        data_vencimento=date(2026, 9, 10),
        status=Mensalidade.Status.PENDENTE,
    )

    Pagamento.objects.create(
        mensalidade=mensalidade_paga,
        valor_pago=Decimal("80.00"),
        forma_pagamento=Pagamento.FormaPagamento.PIX,
    )
    Pagamento.objects.create(
        mensalidade=mensalidade_paga,
        valor_pago=Decimal("120.00"),
        forma_pagamento=Pagamento.FormaPagamento.TRANSFERENCIA,
    )
    Pagamento.objects.create(
        mensalidade=mensalidade_parcial,
        valor_pago=Decimal("50.00"),
        forma_pagamento=Pagamento.FormaPagamento.DINHEIRO,
    )

    return {
        "professor": professor,
        "outro_professor": outro_professor,
        "setembro": setembro,
        "outubro": outubro,
        "mensalidade_parcial": mensalidade_parcial,
    }


@pytest.mark.django_db
class TestConsistenciaDadosDashboard:
    """Task 31775 - QA de consistência dos indicadores financeiros."""

    def test_view_confere_com_as_fontes_operacionais(self, cenario_consistencia):
        professor = cenario_consistencia["professor"]
        competencia = cenario_consistencia["setembro"]
        mensalidades = Mensalidade.objects.filter(
            aluno__professor=professor,
            competencia=competencia,
        )

        faturamento_esperado = mensalidades.aggregate(total=Sum("valor_total"))["total"]
        pagamentos_esperados = Pagamento.objects.filter(
            mensalidade__in=mensalidades
        ).aggregate(total=Sum("valor_pago"))["total"]
        pendente_esperado = sum(
            (max(mensalidade.saldo, Decimal("0.00")) for mensalidade in mensalidades),
            start=Decimal("0.00"),
        )

        indicador = IndicadorFinanceiro.objects.get(
            professor=professor,
            competencia=competencia,
        )

        assert indicador.total_mensalidades == mensalidades.count() == 3
        assert indicador.faturamento_gerado == faturamento_esperado == Decimal("450.00")
        assert indicador.valor_total_pago == pagamentos_esperados == Decimal("250.00")
        assert indicador.valor_pendente == pendente_esperado == Decimal("200.00")
        assert indicador.total_pendentes == 2
        assert indicador.total_vencidas == 1
        assert indicador.indice_inadimplencia == Decimal("44.4")

    def test_endpoint_replica_exatamente_a_view(self, client, cenario_consistencia):
        professor = cenario_consistencia["professor"]
        competencia = cenario_consistencia["setembro"]
        client.force_login(professor)
        indicador = IndicadorFinanceiro.objects.get(
            professor=professor,
            competencia=competencia,
        )

        resposta = client.get(
            reverse("dashboard:estatisticas"),
            {"competencia": competencia.strftime("%Y-%m")},
        )

        assert resposta.status_code == 200
        assert resposta.json() == {
            "competencia": "2026-09",
            "total_mensalidades": indicador.total_mensalidades,
            "faturamento_gerado": f"{indicador.faturamento_gerado:.2f}",
            "valor_total_pago": f"{indicador.valor_total_pago:.2f}",
            "valor_pendente": f"{indicador.valor_pendente:.2f}",
            "total_pendentes": indicador.total_pendentes,
            "total_vencidas": indicador.total_vencidas,
            "indice_inadimplencia": f"{indicador.indice_inadimplencia:.1f}",
        }

    def test_cards_e_endpoint_usam_a_mesma_competencia(
        self, client, cenario_consistencia, monkeypatch
    ):
        professor = cenario_consistencia["professor"]
        client.force_login(professor)
        monkeypatch.setattr(
            "dashboard.views.timezone.localdate",
            lambda: date(2026, 9, 18),
        )

        painel = client.get(reverse("dashboard:index"))
        endpoint = client.get(
            reverse("dashboard:estatisticas"),
            {"competencia": "2026-09"},
        ).json()

        assert painel.status_code == 200
        assert painel.context["mes_referencia"] == date(2026, 9, 1)
        assert painel.context["faturamento_gerado"] == Decimal(
            endpoint["faturamento_gerado"]
        )
        assert painel.context["valor_pendente"] == Decimal(endpoint["valor_pendente"])
        assert painel.context["indice_inadimplencia"] == Decimal(
            endpoint["indice_inadimplencia"]
        )

    def test_competencias_e_professores_permanecem_isolados(
        self, cenario_consistencia
    ):
        professor = cenario_consistencia["professor"]
        outro_professor = cenario_consistencia["outro_professor"]

        setembro = IndicadorFinanceiro.objects.get(
            professor=professor,
            competencia=cenario_consistencia["setembro"],
        )
        outubro = IndicadorFinanceiro.objects.get(
            professor=professor,
            competencia=cenario_consistencia["outubro"],
        )
        setembro_isolado = IndicadorFinanceiro.objects.get(
            professor=outro_professor,
            competencia=cenario_consistencia["setembro"],
        )

        assert setembro.faturamento_gerado == Decimal("450.00")
        assert outubro.faturamento_gerado == Decimal("900.00")
        assert setembro_isolado.faturamento_gerado == Decimal("700.00")

    def test_invariantes_de_valores_e_quantidades(self, cenario_consistencia):
        indicador = IndicadorFinanceiro.objects.get(
            professor=cenario_consistencia["professor"],
            competencia=cenario_consistencia["setembro"],
        )
        total_pagas = indicador.total_mensalidades - indicador.total_pendentes
        total_pendentes_no_prazo = (
            indicador.total_pendentes - indicador.total_vencidas
        )

        assert (
            indicador.valor_total_pago + indicador.valor_pendente
            == indicador.faturamento_gerado
        )
        assert (
            total_pagas + total_pendentes_no_prazo + indicador.total_vencidas
            == indicador.total_mensalidades
        )
        assert Decimal("0.0") <= indicador.indice_inadimplencia <= Decimal("100.0")

    def test_view_reflete_baixa_sem_cache_inconsistente(self, cenario_consistencia):
        mensalidade = cenario_consistencia["mensalidade_parcial"]
        Pagamento.registrar(
            mensalidade=mensalidade,
            valor_pago=Decimal("100.00"),
            forma_pagamento=Pagamento.FormaPagamento.PIX,
        )

        mensalidade.refresh_from_db()
        indicador = IndicadorFinanceiro.objects.get(
            professor=cenario_consistencia["professor"],
            competencia=cenario_consistencia["setembro"],
        )

        assert mensalidade.status == Mensalidade.Status.PAGO
        assert indicador.valor_total_pago == Decimal("350.00")
        assert indicador.valor_pendente == Decimal("100.00")
        assert indicador.total_pendentes == 1
        assert indicador.total_vencidas == 1
        assert indicador.indice_inadimplencia == Decimal("22.2")
