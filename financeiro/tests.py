from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from alunos.models import Aluno
from financeiro.models import Mensalidade, Pagamento


@pytest.fixture
def professor(db):
    return User.objects.create_user(username="prof1", password="senha123")


@pytest.fixture
def aluno(professor):
    aluno = Aluno(
        professor=professor, nome="Maria Silva", cpf="12345678901",
        telefone="83999999999", saldo_devedor=Decimal("200.00"),
    )
    aluno.full_clean()
    aluno.save()
    return aluno


def criar_mensalidade(aluno, dias_vencimento=0, valor=Decimal("200.00"), status=Mensalidade.Status.PENDENTE):
    return Mensalidade.objects.create(
        aluno=aluno,
        competencia=timezone.localdate().replace(day=1),
        valor_total=valor,
        data_vencimento=timezone.localdate() - timedelta(days=dias_vencimento),
        status=status,
    )


class TestRegistrarPagamento:
    """US-30344 / Task 31622 — Registrar pagamento do aluno."""

    def test_cenario_baixa_de_pagamento_realizada(self, aluno):
        mensalidade = criar_mensalidade(aluno)

        Pagamento.registrar(
            mensalidade=mensalidade,
            valor_pago=Decimal("200.00"),
            forma_pagamento=Pagamento.FormaPagamento.PIX,
        )

        mensalidade.refresh_from_db()
        aluno.refresh_from_db()
        assert mensalidade.status == Mensalidade.Status.PAGO
        assert aluno.saldo_devedor == Decimal("0.00")

    def test_pagamento_parcial_mantem_mensalidade_pendente(self, aluno):
        mensalidade = criar_mensalidade(aluno, valor=Decimal("200.00"))

        Pagamento.registrar(
            mensalidade=mensalidade,
            valor_pago=Decimal("100.00"),
            forma_pagamento=Pagamento.FormaPagamento.PIX,
        )

        mensalidade.refresh_from_db()
        assert mensalidade.status == Mensalidade.Status.PENDENTE
        assert mensalidade.saldo == Decimal("100.00")

    def test_cenario_erro_valor_invalido(self, aluno):
        mensalidade = criar_mensalidade(aluno)
        with pytest.raises(ValidationError):
            Pagamento.registrar(
                mensalidade=mensalidade,
                valor_pago=Decimal("0.00"),
                forma_pagamento=Pagamento.FormaPagamento.PIX,
            )

    def test_cenario_erro_valor_negativo(self, aluno):
        mensalidade = criar_mensalidade(aluno)
        with pytest.raises(ValidationError):
            Pagamento.registrar(
                mensalidade=mensalidade,
                valor_pago=Decimal("-50.00"),
                forma_pagamento=Pagamento.FormaPagamento.PIX,
            )


class TestIdentificarInadimplentes:
    """US-30350 / Task 31623 — Identificar alunos inadimplentes."""

    def test_ca_ina_01_mensalidade_vencida_ha_mais_de_5_dias_e_nao_paga(self, client, aluno):
        criar_mensalidade(aluno, dias_vencimento=10)

        client.force_login(aluno.professor)
        response = client.get("/financeiro/inadimplentes/")

        assert response.status_code == 200
        assert "Maria Silva" in response.content.decode()

    def test_ca_ina_01_mensalidade_vencida_ha_menos_de_5_dias_nao_aparece(self, client, aluno):
        criar_mensalidade(aluno, dias_vencimento=2)

        client.force_login(aluno.professor)
        response = client.get("/financeiro/inadimplentes/")

        assert "Maria Silva" not in response.content.decode()

    def test_ca_ina_01_mensalidade_paga_nao_aparece_mesmo_vencida(self, client, aluno):
        criar_mensalidade(aluno, dias_vencimento=30, status=Mensalidade.Status.PAGO)

        client.force_login(aluno.professor)
        response = client.get("/financeiro/inadimplentes/")

        assert "Maria Silva" not in response.content.decode()

    def test_ca_ina_02_agrega_valores_por_aluno(self, aluno):
        criar_mensalidade(aluno, dias_vencimento=10, valor=Decimal("150.00"))
        criar_mensalidade(aluno, dias_vencimento=40, valor=Decimal("150.00"))

        limite = timezone.localdate() - timedelta(days=5)
        total = sum(
            m.saldo
            for m in Mensalidade.objects.filter(aluno=aluno, data_vencimento__lt=limite)
            .exclude(status=Mensalidade.Status.PAGO)
        )
        assert total == Decimal("300.00")
