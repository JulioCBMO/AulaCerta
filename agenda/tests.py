from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from agenda.models import Aula
from alunos.models import Aluno


@pytest.fixture
def professor(db):
    return User.objects.create_user(username="prof1", password="senha123")


@pytest.fixture
def aluno_ativo(professor):
    aluno = Aluno(
        professor=professor, nome="Maria Silva", cpf="12345678901", telefone="83999999999"
    )
    aluno.full_clean()
    aluno.save()
    return aluno


@pytest.fixture
def aluno_inativo(professor):
    aluno = Aluno(
        professor=professor, nome="João Souza", cpf="98765432100", telefone="83988888888",
        situacao=Aluno.Situacao.INATIVO,
    )
    aluno.full_clean()
    aluno.save()
    return aluno


def criar_aula(professor, aluno, inicio=None, **kwargs):
    inicio = inicio or (timezone.now() + timedelta(days=1))
    aula = Aula(professor=professor, aluno=aluno, data_hora_inicio=inicio, **kwargs)
    aula.full_clean()
    aula.save()
    return aula


class TestCriarAgendamento:
    """US-30332 — Criar agendamento de aula."""

    def test_agendamento_com_sucesso(self, professor, aluno_ativo):
        aula = criar_aula(professor, aluno_ativo)
        assert aula.status == Aula.Status.AGENDADA

    def test_ca_age_01_conflito_de_horario_e_rejeitado(self, professor, aluno_ativo):
        inicio = timezone.now() + timedelta(days=1)
        criar_aula(professor, aluno_ativo, inicio=inicio.replace(minute=0), duracao_minutos=60)

        conflitante = inicio.replace(minute=30)
        with pytest.raises(ValidationError):
            criar_aula(professor, aluno_ativo, inicio=conflitante, duracao_minutos=60)

    def test_ca_age_01_horarios_nao_sobrepostos_sao_permitidos(self, professor, aluno_ativo):
        inicio = (timezone.now() + timedelta(days=1)).replace(minute=0, second=0, microsecond=0)
        criar_aula(professor, aluno_ativo, inicio=inicio, duracao_minutos=60)
        # começa exatamente quando a primeira termina: não deve conflitar
        criar_aula(professor, aluno_ativo, inicio=inicio + timedelta(hours=1), duracao_minutos=60)

    def test_ca_age_02_aluno_deve_estar_ativo(self, professor, aluno_inativo):
        with pytest.raises(ValidationError):
            criar_aula(professor, aluno_inativo)

    def test_ca_age_03_bloqueia_agendamento_retroativo(self, professor, aluno_ativo):
        passado = timezone.now() - timedelta(days=1)
        with pytest.raises(ValidationError):
            criar_aula(professor, aluno_ativo, inicio=passado)


class TestRegistrarAulaRealizada:
    """US-30338 / Task 31621 — Registrar aula realizada."""

    def test_ca_reg_02_marca_status_realizada_e_grava_timestamp(self, professor, aluno_ativo):
        aula = criar_aula(professor, aluno_ativo)
        conteudo = "Revisão de equações do segundo grau com exercícios práticos e discussão."
        aula.registrar_como_realizada(conteudo_trabalhado=conteudo)

        aula.refresh_from_db()
        assert aula.status == Aula.Status.REALIZADA
        assert aula.data_registro is not None
        assert aula.conteudo_trabalhado == conteudo

    def test_ca_reg_01_bloqueia_conteudo_com_menos_de_50_caracteres(self, professor, aluno_ativo):
        aula = criar_aula(professor, aluno_ativo)
        with pytest.raises(ValidationError):
            aula.registrar_como_realizada(conteudo_trabalhado="Texto curto")
