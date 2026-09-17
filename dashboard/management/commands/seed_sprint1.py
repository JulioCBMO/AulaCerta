import os
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Professor
from agenda.models import Aula
from alunos.models import Aluno
from financeiro.models import Mensalidade, Pagamento


SEED_PREFIX = "[seed_sprint1]"


class Command(BaseCommand):
    help = "Cria ou atualiza dados de demonstração da Sprint 01 sem duplicá-los."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="demo_sprint1",
            help="Nome do usuário de demonstração (padrão: demo_sprint1).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"]
        senha = os.environ.get("AULACERTA_SEED_PASSWORD")
        contagem = {"criados": 0, "atualizados": 0}

        usuario, criado = get_user_model().objects.get_or_create(
            username=username,
            defaults={
                "first_name": "Professor",
                "last_name": "Demonstração",
                "email": "demo.sprint1@aulacerta.local",
            },
        )
        self._contabilizar(criado, contagem)

        if criado:
            if senha:
                usuario.set_password(senha)
            else:
                usuario.set_unusable_password()
            usuario.save(update_fields=["password"])
        elif senha and not usuario.has_usable_password():
            usuario.set_password(senha)
            usuario.save(update_fields=["password"])

        _, criado = Professor.objects.update_or_create(
            user=usuario,
            defaults={
                "valor_hora_padrao": Decimal("80.00"),
                "antecedencia_minima_cancelamento_horas": 24,
                "dia_vencimento_padrao": 10,
            },
        )
        self._contabilizar(criado, contagem)

        ana = self._salvar_aluno(
            usuario,
            contagem,
            cpf="11111111111",
            nome="Ana Beatriz Lima",
            telefone="83991111111",
            email="ana.seed@exemplo.com",
            disciplina="Matemática",
            serie_nivel="9º ano",
            valor_hora=Decimal("80.00"),
            situacao=Aluno.Situacao.ATIVO,
        )
        bruno = self._salvar_aluno(
            usuario,
            contagem,
            cpf="22222222222",
            nome="Bruno César Silva",
            telefone="83992222222",
            email="bruno.seed@exemplo.com",
            disciplina="Física",
            serie_nivel="2º ano do ensino médio",
            valor_hora=Decimal("90.00"),
            situacao=Aluno.Situacao.INATIVO,
        )
        carla = self._salvar_aluno(
            usuario,
            contagem,
            cpf="33333333333",
            nome="Carla Mendes Souza",
            telefone="83993333333",
            email="carla.seed@exemplo.com",
            disciplina="Química",
            serie_nivel="3º ano do ensino médio",
            valor_hora=Decimal("85.00"),
            situacao=Aluno.Situacao.ATIVO,
        )

        hoje = timezone.localdate()
        inicio_mes = hoje.replace(day=1)
        competencia_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
        dia_aula_realizada = max(inicio_mes, hoje - timedelta(days=1))

        self._salvar_aula(
            usuario,
            ana,
            contagem,
            marcador="aula_realizada_ana",
            data_hora_inicio=self._data_hora(dia_aula_realizada, 9),
            duracao_minutos=60,
            modalidade=Aula.Modalidade.ONLINE,
            status=Aula.Status.REALIZADA,
            conteudo_trabalhado=(
                "Revisão de equações do segundo grau com resolução comentada "
                "de exercícios e esclarecimento de dúvidas."
            ),
            data_registro=self._data_hora(dia_aula_realizada, 10),
        )
        self._salvar_aula(
            usuario,
            carla,
            contagem,
            marcador="aula_agendada_carla",
            data_hora_inicio=self._data_hora(hoje + timedelta(days=1), 14),
            duracao_minutos=90,
            modalidade=Aula.Modalidade.PRESENCIAL,
            status=Aula.Status.AGENDADA,
            conteudo_trabalhado="",
            data_registro=None,
        )

        mensalidade_paga = self._salvar_mensalidade(
            ana,
            contagem,
            marcador="mensalidade_paga_ana",
            competencia=inicio_mes,
            valor_total=Decimal("200.00"),
            data_vencimento=hoje - timedelta(days=10),
            status=Mensalidade.Status.PAGO,
        )
        mensalidade_parcial = self._salvar_mensalidade(
            carla,
            contagem,
            marcador="mensalidade_parcial_carla",
            competencia=inicio_mes,
            valor_total=Decimal("250.00"),
            data_vencimento=hoje + timedelta(days=5),
            status=Mensalidade.Status.PENDENTE,
        )
        self._salvar_mensalidade(
            carla,
            contagem,
            marcador="mensalidade_vencida_carla",
            competencia=competencia_anterior,
            valor_total=Decimal("300.00"),
            data_vencimento=hoje - timedelta(days=15),
            status=Mensalidade.Status.VENCIDO,
        )

        self._salvar_pagamento(
            mensalidade_paga,
            contagem,
            marcador="pagamento_integral_ana",
            valor_pago=Decimal("200.00"),
            forma_pagamento=Pagamento.FormaPagamento.PIX,
            data_pagamento=hoje - timedelta(days=9),
        )
        self._salvar_pagamento(
            mensalidade_parcial,
            contagem,
            marcador="pagamento_parcial_carla",
            valor_pago=Decimal("100.00"),
            forma_pagamento=Pagamento.FormaPagamento.TRANSFERENCIA,
            data_pagamento=hoje,
        )

        # Recalcula o saldo a partir das cobranças para que novas execuções do
        # seed produzam exatamente o mesmo estado.
        for aluno in (ana, bruno, carla):
            saldo = sum(
                (
                    mensalidade.saldo
                    for mensalidade in aluno.mensalidades.exclude(
                        status=Mensalidade.Status.PAGO
                    )
                ),
                start=Decimal("0.00"),
            )
            aluno.saldo_devedor = max(saldo, Decimal("0.00"))
            aluno.full_clean()
            aluno.save(update_fields=["saldo_devedor"])

        self.stdout.write(
            self.style.SUCCESS(
                "Seed da Sprint 01 concluído: "
                f"{contagem['criados']} registro(s) criado(s) e "
                f"{contagem['atualizados']} atualizado(s)."
            )
        )
        if not usuario.has_usable_password():
            self.stdout.write(
                self.style.WARNING(
                    "O usuário de demonstração foi criado sem senha utilizável. "
                    "Defina AULACERTA_SEED_PASSWORD e execute o comando novamente."
                )
            )

    @staticmethod
    def _contabilizar(criado, contagem):
        chave = "criados" if criado else "atualizados"
        contagem[chave] += 1

    @staticmethod
    def _data_hora(data, hora):
        valor = datetime.combine(data, time(hour=hora))
        return timezone.make_aware(valor, timezone.get_current_timezone())

    def _salvar_aluno(self, usuario, contagem, *, cpf, **dados):
        aluno, criado = Aluno.objects.update_or_create(
            professor=usuario,
            cpf=cpf,
            defaults=dados,
        )
        aluno.full_clean()
        aluno.save()
        self._contabilizar(criado, contagem)
        return aluno

    def _salvar_aula(self, usuario, aluno, contagem, *, marcador, **dados):
        aula, criado = Aula.objects.update_or_create(
            professor=usuario,
            observacoes=f"{SEED_PREFIX} {marcador}",
            defaults={"aluno": aluno, **dados},
        )
        aula.full_clean()
        aula.save()
        self._contabilizar(criado, contagem)
        return aula

    def _salvar_mensalidade(self, aluno, contagem, *, marcador, **dados):
        mensalidade, criado = Mensalidade.objects.update_or_create(
            aluno=aluno,
            observacoes=f"{SEED_PREFIX} {marcador}",
            defaults=dados,
        )
        mensalidade.full_clean()
        mensalidade.save()
        self._contabilizar(criado, contagem)
        return mensalidade

    def _salvar_pagamento(
        self, mensalidade, contagem, *, marcador, valor_pago, forma_pagamento, data_pagamento
    ):
        observacoes = f"{SEED_PREFIX} {marcador}"
        pagamento = Pagamento.objects.filter(
            mensalidade=mensalidade,
            observacoes=observacoes,
        ).first()
        if pagamento is None:
            pagamento = Pagamento.registrar(
                mensalidade=mensalidade,
                valor_pago=valor_pago,
                forma_pagamento=forma_pagamento,
                data_pagamento=data_pagamento,
                observacoes=observacoes,
            )
            criado = True
        else:
            pagamento.valor_pago = valor_pago
            pagamento.forma_pagamento = forma_pagamento
            pagamento.data_pagamento = data_pagamento
            pagamento.full_clean()
            pagamento.save(
                update_fields=["valor_pago", "forma_pagamento", "data_pagamento"]
            )
            criado = False
        self._contabilizar(criado, contagem)
        return pagamento
