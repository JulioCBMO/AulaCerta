import re
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from agenda.models import Aula
from alunos.models import Aluno
from dashboard.models import IndicadorFinanceiro
from financeiro.models import Mensalidade

DIAS_TOLERANCIA_INADIMPLENCIA = 5
PADRAO_COMPETENCIA = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


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


def _competencia_solicitada(valor):
    """Converte YYYY-MM para o primeiro dia da competência."""
    if valor is None:
        return timezone.localdate().replace(day=1)
    if not PADRAO_COMPETENCIA.fullmatch(valor):
        raise ValueError("Competência deve estar no formato YYYY-MM.")

    ano, mes = (int(parte) for parte in valor.split("-"))
    try:
        return date(ano, mes, 1)
    except ValueError as erro:
        raise ValueError("Competência deve estar no formato YYYY-MM.") from erro


def _payload_zerado(competencia):
    return {
        "competencia": competencia.strftime("%Y-%m"),
        "total_mensalidades": 0,
        "faturamento_gerado": "0.00",
        "valor_total_pago": "0.00",
        "valor_pendente": "0.00",
        "total_pendentes": 0,
        "total_vencidas": 0,
        "indice_inadimplencia": "0.0",
    }


def estatisticas_dashboard(request):
    """Task 31773 - endpoint autenticado de indicadores financeiros."""
    if not request.user.is_authenticated:
        return JsonResponse(
            {"erro": "Autenticação necessária."},
            status=401,
        )

    if request.method != "GET":
        resposta = JsonResponse(
            {"erro": "Método não permitido. Utilize GET."},
            status=405,
        )
        resposta["Allow"] = "GET"
        return resposta

    try:
        competencia = _competencia_solicitada(request.GET.get("competencia"))
    except ValueError as erro:
        return JsonResponse({"erro": str(erro)}, status=400)

    indicador = IndicadorFinanceiro.objects.filter(
        professor_id=request.user.pk,
        competencia=competencia,
    ).first()

    if indicador is None:
        return JsonResponse(_payload_zerado(competencia))

    return JsonResponse(
        {
            "competencia": competencia.strftime("%Y-%m"),
            "total_mensalidades": indicador.total_mensalidades,
            "faturamento_gerado": f"{indicador.faturamento_gerado:.2f}",
            "valor_total_pago": f"{indicador.valor_total_pago:.2f}",
            "valor_pendente": f"{indicador.valor_pendente:.2f}",
            "total_pendentes": indicador.total_pendentes,
            "total_vencidas": indicador.total_vencidas,
            "indice_inadimplencia": f"{indicador.indice_inadimplencia:.1f}",
        }
    )
