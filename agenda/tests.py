from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from agenda.forms import RegistrarAulaForm
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

    def test_ca_reg_01_aceita_conteudo_com_exatamente_50_caracteres(
        self, professor, aluno_ativo
    ):
        aula = criar_aula(professor, aluno_ativo)
        conteudo = "A" * 50

        aula.registrar_como_realizada(conteudo_trabalhado=conteudo)

        aula.refresh_from_db()
        assert aula.status == Aula.Status.REALIZADA
        assert aula.conteudo_trabalhado == conteudo

    def test_persiste_observacoes_pedagogicas(self, professor, aluno_ativo):
        aula = criar_aula(professor, aluno_ativo)
        observacoes = "A aluna apresentou boa evolução durante os exercícios."

        aula.registrar_como_realizada(
            conteudo_trabalhado="A" * 50,
            observacoes=f"  {observacoes}  ",
        )

        aula.refresh_from_db()
        assert aula.observacoes == observacoes

    def test_bloqueia_novo_registro_quando_a_aula_ja_foi_realizada(
        self, professor, aluno_ativo
    ):
        aula = criar_aula(professor, aluno_ativo)
        aula.registrar_como_realizada(conteudo_trabalhado="A" * 50)

        with pytest.raises(ValidationError, match="Somente aulas agendadas"):
            aula.registrar_como_realizada(conteudo_trabalhado="B" * 50)


class TestRegistrarAulaForm:
    def test_formulario_bloqueia_texto_insuficiente(self):
        form = RegistrarAulaForm(
            data={"conteudo_trabalhado": "A" * 49, "observacoes": ""}
        )

        assert not form.is_valid()
        assert "pelo menos 50 caracteres" in form.errors["conteudo_trabalhado"][0]

    def test_formulario_aceita_exatamente_50_caracteres(self):
        form = RegistrarAulaForm(
            data={"conteudo_trabalhado": "A" * 50, "observacoes": ""}
        )

        assert form.is_valid()


class TestRegistrarAulaRealizadaView:
    def test_post_valido_atualiza_aula_e_redireciona(
        self, client, professor, aluno_ativo
    ):
        aula = criar_aula(professor, aluno_ativo)
        client.force_login(professor)

        response = client.post(
            reverse("agenda:registrar", args=[aula.pk]),
            data={
                "conteudo_trabalhado": "Conteúdo válido para registrar a aula com mais de cinquenta caracteres.",
                "observacoes": "Participação satisfatória.",
            },
        )

        assert response.status_code == 302
        assert response.url == reverse("agenda:detalhe", args=[aula.pk])
        aula.refresh_from_db()
        assert aula.status == Aula.Status.REALIZADA
        assert aula.data_registro is not None
        assert aula.observacoes == "Participação satisfatória."

    def test_post_invalido_mantem_aula_agendada(
        self, client, professor, aluno_ativo
    ):
        aula = criar_aula(professor, aluno_ativo)
        client.force_login(professor)

        response = client.post(
            reverse("agenda:registrar", args=[aula.pk]),
            data={"conteudo_trabalhado": "Texto curto", "observacoes": ""},
        )

        assert response.status_code == 200
        assert "pelo menos 50 caracteres" in response.content.decode()
        aula.refresh_from_db()
        assert aula.status == Aula.Status.AGENDADA
        assert aula.data_registro is None

    def test_professor_nao_acessa_aula_de_outro_professor(
        self, client, professor, aluno_ativo
    ):
        outro_professor = User.objects.create_user(
            username="prof2", password="senha123"
        )
        outro_aluno = Aluno.objects.create(
            professor=outro_professor,
            nome="Aluno do Prof2",
            cpf="98765432100",
            telefone="83988888888",
        )
        aula = criar_aula(outro_professor, outro_aluno)
        client.force_login(professor)

        response = client.get(reverse("agenda:registrar", args=[aula.pk]))

        assert response.status_code == 404

    def test_acesso_sem_login_redireciona_para_login(
        self, client, professor, aluno_ativo
    ):
        aula = criar_aula(professor, aluno_ativo)

        response = client.get(reverse("agenda:registrar", args=[aula.pk]))

        assert response.status_code == 302
        assert response.url.startswith(reverse("login"))

    def test_template_possui_bloqueio_e_contador_no_frontend(
        self, client, professor, aluno_ativo
    ):
        aula = criar_aula(professor, aluno_ativo)
        client.force_login(professor)

        response = client.get(reverse("agenda:registrar", args=[aula.pk]))

        assert response.status_code == 200
        conteudo = response.content.decode()
        assert 'minlength="50"' in conteudo
        assert 'id="conteudo-contador"' in conteudo
        assert 'id="btn-concluir"' in conteudo
        assert "disabled" in conteudo


class TestConstraintsAula:
    """Task 31780 — constraints de integridade da agenda."""

    def test_banco_rejeita_aula_com_duracao_zero(self, professor, aluno_ativo):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Aula.objects.create(
                    professor=professor,
                    aluno=aluno_ativo,
                    data_hora_inicio=timezone.now() + timedelta(days=1),
                    duracao_minutos=0,
                )
