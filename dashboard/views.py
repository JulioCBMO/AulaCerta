from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from agenda.models import Aula
from alunos.models import Aluno
from financeiro.models import Mensalidade

DIAS_TOLERANCIA_INADIMPLENCIA = 5


@login_required
def index(request):
    """
    US-30355 — Visualizar indicadores do sistema.

    Lógica de agregação (conforme descrição da US):
    - total de alunos com status 'Ativo';
    - soma de aulas concluídas (REALIZADA) no mês vigente;
    - índice de inadimplência: proporção de pagamentos pendentes em
      relação ao total de faturamento gerado no período.
    """
    professor = request.user
    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)

    total_alunos_ativos = Aluno.objects.filter(
        professor=professor, situacao=Aluno.Situacao.ATIVO
    ).count()

    aulas_realizadas_mes = Aula.objects.filter(
        professor=professor,
        status=Aula.Status.REALIZADA,
        data_hora_inicio__date__gte=inicio_mes,
        data_hora_inicio__date__lte=hoje,
    ).count()

    mensalidades_periodo = Mensalidade.objects.filter(
        aluno__professor=professor,
        competencia__gte=inicio_mes,
    )
    faturamento_gerado = mensalidades_periodo.aggregate(total=Sum("valor_total"))["total"] or 0

    pendentes = mensalidades_periodo.exclude(status=Mensalidade.Status.PAGO)
    valor_pendente = sum((m.saldo for m in pendentes), start=0)

    if faturamento_gerado:
        indice_inadimplencia = round((valor_pendente / faturamento_gerado) * 100, 1)
    else:
        indice_inadimplencia = 0

    limite_atraso = hoje.fromordinal(hoje.toordinal() - DIAS_TOLERANCIA_INADIMPLENCIA)
    total_inadimplentes = (
        Mensalidade.objects.filter(aluno__professor=professor, data_vencimento__lt=limite_atraso)
        .exclude(status=Mensalidade.Status.PAGO)
        .values("aluno")
        .distinct()
        .count()
    )

    contexto = {
        "total_alunos_ativos": total_alunos_ativos,
        "aulas_realizadas_mes": aulas_realizadas_mes,
        "faturamento_gerado": faturamento_gerado,
        "valor_pendente": valor_pendente,
        "indice_inadimplencia": indice_inadimplencia,
        "total_inadimplentes": total_inadimplentes,
        "mes_referencia": inicio_mes,
    }
    return render(request, "dashboard/index.html", contexto)
