"""
Configurações do projeto AulaCerta.

Sprint 01 — Atividade auxiliar "US - Configurar ambiente inicial do projeto"
e "US - Criar estrutura inicial do banco de dados".
"""
import os
from pathlib import Path

import dj_database_url
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="dev-secret-key-nao-use-em-producao")
# Por segurança, DEBUG é False por padrão: em desenvolvimento local,
# defina DEBUG=True explicitamente no seu .env.
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# A Vercel publica cada deploy em um subdomínio diferente de vercel.app.
# O ponto inicial libera o domínio principal e todos os seus subdomínios.
if ".vercel.app" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(".vercel.app")

# O Render injeta automaticamente RENDER_EXTERNAL_HOSTNAME (algo como
# "aulacerta.onrender.com") em todo Web Service. Adicionamos esse host
# automaticamente para não precisar repeti-lo manualmente na variável
# ALLOWED_HOSTS do painel do Render.
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# O Render também envia requisições internas de health-check; liberamos
# CSRF para o domínio externo, exigido pelo Django 4+ ao usar HTTPS.
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
if "https://*.vercel.app" not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append("https://*.vercel.app")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # apps do domínio AulaCerta
    "accounts",
    "alunos",
    "agenda",
    "financeiro",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Banco de dados: PostgreSQL 16, conforme definido na proposta técnica.
#
# Prioridade de configuração:
#   1. DATABASE_URL (formato "postgres://usuario:senha@host:porta/nome"),
#      que é a variável fornecida automaticamente pelo Render ao conectar
#      um banco PostgreSQL gerenciado a um Web Service.
#   2. USE_SQLITE=True — apenas para rodar testes locais sem subir o
#      container do Postgres.
#   3. Variáveis DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT, usadas pelo
#      docker-compose.yml em desenvolvimento local.
DATABASE_URL = config("DATABASE_URL", default="")

if DATABASE_URL:
    # ssl_require=False porque a "Internal Database URL" fornecida pelo
    # Render (banco e web service na mesma rede privada) não usa/precisa
    # de SSL. Se você usar a "External Database URL" em algum cenário,
    # inclua "?sslmode=require" diretamente na própria DATABASE_URL.
    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=False)
    }
elif config("USE_SQLITE", default=False, cast=bool):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="aulacerta"),
            "USER": config("DB_USER", default="aulacerta"),
            "PASSWORD": config("DB_PASSWORD", default="aulacerta"),
            "HOST": config("DB_HOST", default="db"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise: serve os arquivos estáticos coletados (collectstatic)
# diretamente pelo processo do Gunicorn, com hashing e compressão,
# dispensando um servidor de arquivos estáticos separado (nginx/CDN)
# no ambiente de homologação gratuito.
#
# O storage com manifest (hashing de nomes de arquivo) só é usado em
# produção: ele exige que "collectstatic" já tenha rodado, o que
# atrapalharia rodar testes/servidor local sem esse passo manual.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        ),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:index"
LOGOUT_REDIRECT_URL = "login"

# Segurança para produção. O Render fica atrás de um proxy HTTPS, então
# confiamos no cabeçalho X-Forwarded-Proto para saber quando a conexão
# original já era segura (evita loop de redirecionamento).
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
