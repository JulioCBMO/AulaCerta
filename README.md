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

Requer Python 3.12 e um PostgreSQL local, ou use SQLite apenas para
desenvolvimento/teste definindo `USE_SQLITE=True`.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export USE_SQLITE=True   # ou configure DB_* no .env para usar Postgres
export SECRET_KEY=dev-key
export DEBUG=True        # por padrão DEBUG é False (seguro para produção)

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Dados de demonstração — Task 31780

Depois de aplicar as migrations, use o comando abaixo para criar um
conjunto coerente de dados da Sprint 01:

```bash
export AULACERTA_SEED_PASSWORD="uma-senha-local"
python manage.py seed_sprint1
```

No PowerShell, defina a senha com:

```powershell
$env:AULACERTA_SEED_PASSWORD = "uma-senha-local"
python manage.py seed_sprint1
```

O comando cria ou atualiza o usuário `demo_sprint1`, três alunos, duas
aulas, três mensalidades e dois pagamentos. Ele é idempotente: pode ser
executado novamente sem duplicar esses registros. Se a variável de senha
não for definida na primeira execução, o usuário será criado sem senha
utilizável, mas os dados continuarão disponíveis para inspeção pelo Admin.

As constraints da Task 31780 protegem também no banco de dados a duração
positiva da aula, os valores positivos de mensalidade e pagamento, o saldo
devedor não negativo e o valor-hora nulo ou positivo. A unicidade do CPF por
professor já era garantida e também possui cobertura de teste no banco.

## Deploy em produção (Render — gratuito)

O projeto já está preparado para deploy no [Render](https://render.com),
conforme definido na Proposta de Projeto (item 5.7). Arquivos relevantes:

- `requirements.txt` — inclui `gunicorn` (servidor WSGI de produção),
  `whitenoise` (serve os arquivos estáticos sem precisar de nginx/CDN)
  e `dj-database-url` (lê a `DATABASE_URL` fornecida pelo Render).
- `build.sh` — instala dependências, roda `collectstatic` e `migrate`
  a cada deploy.
- `render.yaml` — Blueprint que cria o banco PostgreSQL e o Web Service
  automaticamente.

### Opção A — Deploy automático via Blueprint (mais rápido)

1. Suba o projeto para um repositório no GitHub.
2. No painel do Render: **New +** → **Blueprint** → selecione o
   repositório. O Render lê o `render.yaml`, cria o banco PostgreSQL
   gratuito e o Web Service já conectados entre si, e gera uma
   `SECRET_KEY` aleatória automaticamente.
3. Aguarde o build (instala dependências, roda `collectstatic` e
   `migrate`). Ao final, acesse a URL `https://aulacerta-web.onrender.com`.
4. Abra a aba **Shell** do Web Service no painel do Render e rode:
   ```bash
   python manage.py createsuperuser
   ```

### Opção B — Deploy manual (passo a passo)

1. **New +** → **PostgreSQL** → plano *Free*. Copie a **Internal
   Database URL** gerada.
2. **New +** → **Web Service** → conecte o repositório.
   - Build Command: `bash build.sh`
   - Start Command: `gunicorn config.wsgi:application`
3. Em **Environment**, adicione:
   - `SECRET_KEY` — gere uma nova (nunca reaproveite a de desenvolvimento)
   - `DEBUG` = `False`
   - `DATABASE_URL` — a Internal Database URL copiada no passo 1
4. Clique em **Create Web Service** e aguarde o primeiro deploy.
5. Crie o professor de teste pela aba **Shell**:
   ```bash
   python manage.py createsuperuser
   ```

### Observações importantes sobre o plano gratuito do Render

- O Web Service gratuito "dorme" após 15 minutos sem receber
  requisições; a primeira requisição seguinte demora ~1 minuto para
  responder (cold start). Isso é aceitável para o ambiente de
  homologação do projeto (não é um requisito de produção real).
- O banco PostgreSQL gratuito expira 30 dias após a criação, com 14
  dias de carência para você fazer upgrade ou exportar os dados antes
  da exclusão definitiva. Para uma disciplina de um semestre, pode ser
  necessário recriar o banco (ou fazer upgrade) perto do fim do prazo.
- Uploads de arquivo gravados no disco local do Web Service **não são
  persistidos** entre deploys (sistema de arquivos efêmero). Nenhuma
  funcionalidade da Sprint 01 depende de upload de arquivos, então
  isso não afeta o escopo atual.

## Rodando os testes automatizados

```bash
export USE_SQLITE=True SECRET_KEY=teste
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
- `dashboard/tests.py` — Task 31780 (criação dos dados da Sprint 01 e
  idempotência do comando `seed_sprint1`).

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
