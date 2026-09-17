from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from agenda.models import Aula
from alunos.models import Aluno
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
