# AulaCerta — Sprint 01

Plataforma de gestão para professores particulares. Este código-fonte
implementa as user stories planejadas para a **Sprint 01** do projeto
(ver `Backlog_geral` e `Proposta de Projeto`):

| US (OpenProject) | Funcionalidade                              | Onde está |
|---|---|---|
| 30356 | Configurar ambiente inicial do projeto | `Dockerfile`, `docker-compose.yml`, `config/settings.py` |
| 30357 | Criar estrutura inicial do banco de dados | `*/models.py` + `*/migrations/0001_initial.py` |
| 30321 | Cadastrar aluno | `alunos/` |
| 30323 | Consultar alunos cadastrados | `alunos/` |
| 30332 | Criar agendamento de aula | `agenda/` |
| 30338 | Registrar aula realizada | `agenda/` |
| 30344 | Registrar pagamento do aluno | `financeiro/` |
| 30350 | Identificar alunos inadimplentes | `financeiro/` |
| 30355 | Visualizar indicadores do sistema | `dashboard/` |

## Stack

Django 5 + PostgreSQL 16 + Bootstrap 5, conforme a Proposta de Projeto
(seção 5.7). Autenticação usa o sistema padrão do Django
(`django.contrib.auth`) como base mínima para o isolamento de dados
entre professores — o Épico completo "Gestão de Autenticação e Conta"
(cadastro de professor, recuperação de senha, preferências) está
planejado para a Sprint 03, conforme o cronograma da proposta.

## Como rodar com Docker (recomendado)

```bash
cp .env.example .env
docker compose up --build
```

A aplicação fica disponível em `http://localhost:8000`. As migrations
são aplicadas automaticamente pelo comando definido no `docker-compose.yml`.

Crie um professor para testar:

```bash
docker compose exec web python manage.py createsuperuser
```

Faça login em `http://localhost:8000/login/` com o usuário criado.

## Como rodar localmente (sem Docker)

Requer Python 3.12 ou 3.13 e um PostgreSQL local, ou use SQLite apenas
para desenvolvimento/teste definindo `USE_SQLITE=True`. No Windows, os
comandos abaixo funcionam no PowerShell e não dependem da ativação do
ambiente virtual:

```powershell
py -3.13 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

$env:USE_SQLITE = "True"   # ou configure DB_* no .env para usar Postgres
$env:SECRET_KEY = "dev-key"

.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py runserver
```

Se preferir ativar o ambiente virtual, use `.\venv\Scripts\Activate.ps1`
e depois execute `python` e `pip` normalmente.

## Rodando os testes automatizados

```powershell
$env:USE_SQLITE = "True"
$env:SECRET_KEY = "teste"
python -m pytest -v
```

Os testes cobrem os critérios de aceite (CA-*) e os cenários BDD
descritos no backlog para cada User Story da Sprint 01:

- `alunos/tests.py` — CA-CAD-01 (CPF único por professor), CA-CAD-02
  (campos obrigatórios) e CA-CAD-03 (sanitização de strings), além do
  isolamento de dados entre professores na listagem.
- `agenda/tests.py` — CA-AGE-01 (conflito de horário), CA-AGE-02
  (aluno deve estar ativo), CA-AGE-03 (bloqueio de agendamento
  retroativo) e CA-REG-01/02 (mínimo de 50 caracteres e timestamp de
  registro da aula realizada).
- `financeiro/tests.py` — CA-PAG-01 (valor positivo), CA-PAG-02 (baixa
  transacional com recálculo de saldo) e CA-INA-01/02 (identificação e
  agregação de inadimplência).

## Observações de escopo (o que fica para as próximas sprints)

Alguns fluxos foram deliberadamente simplificados na Sprint 01 porque
suas User Stories completas só entram no backlog em Sprint 02/03:

- **Mensalidades** ainda não têm uma tela de cadastro para o professor
  (US-30346, Sprint 03). Por ora, lance mensalidades pelo Django Admin
  (`/admin/financeiro/mensalidade/add/`) para poder testar o fluxo de
  "Registrar pagamento".
- **Contratos** (Épico "Gestão de Contratos") ainda não existem; o
  valor-hora do aluno é um campo simples em `Aluno.valor_hora`.
- **Login/cadastro completo do professor** (recuperação de senha,
  preferências) está planejado para a Sprint 03; usamos o
  `django.contrib.auth` padrão como base mínima necessária para
  isolar os dados entre professores desde já.
- A **visualização de agenda por dia/semana/mês** (US-30337) está
  simplificada para uma lista única nesta sprint.

## Estrutura de pastas

```
config/         configurações do projeto (settings, urls)
accounts/       perfil do professor (preferências)
alunos/         cadastro e consulta de alunos
agenda/         agendamento e registro de aulas
financeiro/     mensalidades, pagamentos e inadimplência
dashboard/      painel de indicadores
templates/      layout base e tela de login
```
