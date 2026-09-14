from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from alunos.models import Aluno


class Aula(models.Model):
    """
    US-30332 "Criar agendamento de aula" e US-30338 "Registrar aula realizada".

    Critérios de aceite implementados:
    CA-AGE-01: impede persistência de registros que colidam com o intervalo
               start_time/end_time de uma aula já existente do mesmo professor.
    CA-AGE-02: vinculação obrigatória a um aluno com status = 'ATIVO'.
    CA-AGE-03: impedimento de agendamentos retroativos à data/hora atual.
    CA-REG-01: conteúdo pedagógico com mínimo de 50 caracteres para marcar
               a aula como realizada.
    CA-REG-02: ao registrar a aula, status muda para 'REALIZADA' e o
               timestamp é gravado em data_registro.
    """

    class Modalidade(models.TextChoices):
        PRESENCIAL = "PRESENCIAL", "Presencial"
        ONLINE = "ONLINE", "Online"

    class Status(models.TextChoices):
        AGENDADA = "AGENDADA", "Agendada"
        REALIZADA = "REALIZADA", "Realizada"
        CANCELADA = "CANCELADA", "Cancelada"
        FALTA = "FALTA", "Falta"

    professor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="aulas"
    )
    aluno = models.ForeignKey(Aluno, on_delete=models.PROTECT, related_name="aulas")

    data_hora_inicio = models.DateTimeField()
    duracao_minutos = models.PositiveIntegerField(default=60)
    modalidade = models.CharField(
        max_length=12, choices=Modalidade.choices, default=Modalidade.PRESENCIAL
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.AGENDADA
    )

    conteudo_trabalhado = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    tipo_falta = models.CharField(
        max_length=20, blank=True,
        help_text="JUSTIFICADA ou NAO_JUSTIFICADA, quando status = FALTA.",
    )

    motivo_cancelamento = models.CharField(max_length=255, blank=True)
    data_registro = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["data_hora_inicio"]
        indexes = [
            models.Index(fields=["professor", "data_hora_inicio"], name="idx_aula_professor_data"),
            models.Index(fields=["aluno", "status"], name="idx_aula_aluno_status"),
        ]

    def __str__(self):
        return f"{self.aluno} — {self.data_hora_inicio:%d/%m/%Y %H:%M}"

    @property
    def data_hora_fim(self):
        return self.data_hora_inicio + timedelta(minutes=self.duracao_minutos)

    def clean(self):
        erros = {}

        # CA-AGE-03: impedimento de agendamentos retroativos
        if self.status == self.Status.AGENDADA and self.data_hora_inicio and self._state.adding:
            if self.data_hora_inicio < timezone.now():
                erros["data_hora_inicio"] = "Não é possível agendar uma aula em data/hora retroativa."

        # CA-AGE-02: aluno deve estar ATIVO
        if self.aluno_id and not self.aluno.is_ativo():
            erros["aluno"] = "Só é possível agendar aulas para alunos com situação ATIVO."

        # CA-AGE-01: detecção de conflito de horário para o mesmo professor
        if self.professor_id and self.data_hora_inicio:
            conflitantes = Aula.objects.filter(
                professor_id=self.professor_id,
                status__in=[self.Status.AGENDADA, self.Status.REALIZADA],
                data_hora_inicio__lt=self.data_hora_fim,
            ).exclude(pk=self.pk)
            for outra in conflitantes:
                if outra.data_hora_fim > self.data_hora_inicio:
                    erros["data_hora_inicio"] = (
                        "Erro: Conflito de horário detectado com outra aula já agendada."
                    )
                    break

        # CA-REG-01: mínimo de 50 caracteres para marcar como REALIZADA
        if self.status == self.Status.REALIZADA:
            conteudo = (self.conteudo_trabalhado or "").strip()
            if len(conteudo) < 50:
                erros["conteudo_trabalhado"] = (
                    "O conteúdo ministrado deve ter pelo menos 50 caracteres."
                )

        if erros:
            raise ValidationError(erros)

    def registrar_como_realizada(self, conteudo_trabalhado, observacoes=""):
        """Task 31621 — Registrar aula realizada (CA-REG-02)."""
        self.status = self.Status.REALIZADA
        self.conteudo_trabalhado = conteudo_trabalhado
        self.observacoes = observacoes
        self.full_clean()
        self.data_registro = timezone.now()
        self.save()
        return self

    def registrar_falta(self, justificada, observacoes=""):
        """US-30340 — Registrar falta do aluno."""
        self.status = self.Status.FALTA
        self.tipo_falta = "JUSTIFICADA" if justificada else "NAO_JUSTIFICADA"
        self.observacoes = observacoes
        self.data_registro = timezone.now()
        self.save()
        return self
