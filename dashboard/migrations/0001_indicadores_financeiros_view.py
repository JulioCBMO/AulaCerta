import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


NOME_VIEW = "dashboard_indicadores_financeiros"

SQL_CRIAR_VIEW = f"""
CREATE VIEW {NOME_VIEW} AS
WITH pagamentos_por_mensalidade AS (
    SELECT
        mensalidade_id,
        COALESCE(SUM(valor_pago), 0) AS valor_pago
    FROM financeiro_pagamento
    GROUP BY mensalidade_id
),
mensalidades_calculadas AS (
    SELECT
        mensalidade.id AS mensalidade_id,
        aluno.professor_id,
        mensalidade.competencia,
        mensalidade.valor_total,
        COALESCE(pagamento.valor_pago, 0) AS valor_pago,
        CASE
            WHEN mensalidade.valor_total - COALESCE(pagamento.valor_pago, 0) > 0
            THEN mensalidade.valor_total - COALESCE(pagamento.valor_pago, 0)
            ELSE 0
        END AS valor_pendente,
        mensalidade.status
    FROM financeiro_mensalidade AS mensalidade
    INNER JOIN alunos_aluno AS aluno
        ON aluno.id = mensalidade.aluno_id
    LEFT JOIN pagamentos_por_mensalidade AS pagamento
        ON pagamento.mensalidade_id = mensalidade.id
)
SELECT
    MIN(mensalidade_id) AS id,
    professor_id,
    competencia,
    COUNT(*) AS total_mensalidades,
    COALESCE(SUM(valor_total), 0) AS faturamento_gerado,
    COALESCE(SUM(valor_pago), 0) AS valor_total_pago,
    COALESCE(SUM(valor_pendente), 0) AS valor_pendente,
    SUM(CASE WHEN status <> 'PAGO' THEN 1 ELSE 0 END) AS total_pendentes,
    SUM(CASE WHEN status = 'VENCIDO' THEN 1 ELSE 0 END) AS total_vencidas,
    CASE
        WHEN SUM(valor_total) > 0
        THEN ROUND((SUM(valor_pendente) * 100.0) / SUM(valor_total), 1)
        ELSE 0
    END AS indice_inadimplencia
FROM mensalidades_calculadas
GROUP BY professor_id, competencia
"""


def criar_view(apps, schema_editor):
    # A SQL utilizada e suportada tanto pelo PostgreSQL/Neon quanto pelo
    # SQLite empregado nos testes locais.
    schema_editor.execute(f"DROP VIEW IF EXISTS {NOME_VIEW}")
    schema_editor.execute(SQL_CRIAR_VIEW)


def remover_view(apps, schema_editor):
    schema_editor.execute(f"DROP VIEW IF EXISTS {NOME_VIEW}")


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("financeiro", "0002_mensalidade_mensalidade_valor_total_positivo_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="IndicadorFinanceiro",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("competencia", models.DateField()),
                ("total_mensalidades", models.IntegerField()),
                (
                    "faturamento_gerado",
                    models.DecimalField(decimal_places=2, max_digits=14),
                ),
                (
                    "valor_total_pago",
                    models.DecimalField(decimal_places=2, max_digits=14),
                ),
                (
                    "valor_pendente",
                    models.DecimalField(decimal_places=2, max_digits=14),
                ),
                ("total_pendentes", models.IntegerField()),
                ("total_vencidas", models.IntegerField()),
                (
                    "indice_inadimplencia",
                    models.DecimalField(decimal_places=1, max_digits=7),
                ),
                (
                    "professor",
                    models.ForeignKey(
                        db_column="professor_id",
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "dashboard_indicadores_financeiros",
                "ordering": ["professor_id", "competencia"],
                "managed": False,
            },
        ),
        migrations.RunPython(criar_view, remover_view),
    ]
