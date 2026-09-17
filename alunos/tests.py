from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from alunos.models import Aluno


@pytest.fixture
def professor(db):
    return User.objects.create_user(username="prof1", password="senha123")


@pytest.fixture
def outro_professor(db):
    return User.objects.create_user(username="prof2", password="senha123")


def criar_aluno(professor, **kwargs):
    dados = dict(
        professor=professor,
        nome="Maria Silva",
        cpf="12345678901",
        telefone="83999999999",
    )
    dados.update(kwargs)
    aluno = Aluno(**dados)
    aluno.full_clean()
    aluno.save()
    return aluno


class TestCadastrarAluno:
    """US-30321 — Cadastrar aluno."""

    def test_cadastro_com_sucesso(self, professor):
        aluno = criar_aluno(professor)
        assert aluno.pk is not None
        assert aluno.situacao == Aluno.Situacao.ATIVO

    def test_ca_cad_01_cpf_duplicado_para_mesmo_professor_e_rejeitado(self, professor):
        criar_aluno(professor, cpf="12345678901")
        with pytest.raises(ValidationError):
            criar_aluno(professor, nome="Outro Aluno", cpf="123.456.789-01")

    def test_ca_cad_01_mesmo_cpf_em_professores_diferentes_e_permitido(self, professor, outro_professor):
        criar_aluno(professor, cpf="12345678901")
        # não deve levantar exceção: isolamento de dados entre professores
        criar_aluno(outro_professor, cpf="12345678901")

    @pytest.mark.parametrize("campo", ["nome", "cpf", "telefone"])
    def test_ca_cad_02_campos_obrigatorios(self, professor, campo):
        dados = {"nome": "Maria Silva", "cpf": "12345678901", "telefone": "83999999999"}
        dados[campo] = ""
        with pytest.raises(ValidationError):
            criar_aluno(professor, **dados)

    def test_ca_cad_03_sanitizacao_de_espacos_no_nome(self, professor):
        aluno = criar_aluno(professor, nome="  Maria   Silva  ")
        assert aluno.nome == "Maria Silva"

    def test_ca_cad_03_cpf_e_normalizado_para_apenas_digitos(self, professor):
        aluno = criar_aluno(professor, cpf="123.456.789-01")
        assert aluno.cpf == "12345678901"


class TestConsultarAlunos:
    """US-30323 — Consultar alunos cadastrados."""

    def test_listagem_filtra_apenas_alunos_do_professor_logado(self, client, professor, outro_professor):
        criar_aluno(professor, nome="Aluno do Prof1", cpf="11111111111")
        criar_aluno(outro_professor, nome="Aluno do Prof2", cpf="22222222222")

        client.force_login(professor)
        response = client.get("/alunos/")

        assert response.status_code == 200
        conteudo = response.content.decode()
        assert "Aluno do Prof1" in conteudo
        assert "Aluno do Prof2" not in conteudo

    def test_filtro_por_nome(self, client, professor):
        criar_aluno(professor, nome="Ana Souza", cpf="11111111111")
        criar_aluno(professor, nome="Bruno Lima", cpf="22222222222")

        client.force_login(professor)
        response = client.get("/alunos/?nome=Ana")

        conteudo = response.content.decode()
        assert "Ana Souza" in conteudo
        assert "Bruno Lima" not in conteudo


class TestConstraintsAluno:
    """Task 31780 — constraints de integridade do cadastro de alunos."""

    def test_banco_rejeita_saldo_devedor_negativo(self, professor):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Aluno.objects.create(
                    professor=professor,
                    nome="Saldo Inválido",
                    cpf="44444444444",
                    telefone="83994444444",
                    saldo_devedor=Decimal("-0.01"),
                )

    def test_banco_rejeita_valor_hora_zero(self, professor):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Aluno.objects.create(
                    professor=professor,
                    nome="Valor Inválido",
                    cpf="55555555555",
                    telefone="83995555555",
                    valor_hora=Decimal("0.00"),
                )

    def test_banco_rejeita_cpf_duplicado_para_o_mesmo_professor(self, professor):
        criar_aluno(professor, cpf="66666666666")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Aluno.objects.create(
                    professor=professor,
                    nome="CPF Duplicado",
                    cpf="66666666666",
                    telefone="83996666666",
                )
