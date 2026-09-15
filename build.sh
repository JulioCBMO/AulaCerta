#!/usr/bin/env bash
# Script de build executado pelo Render a cada deploy.
# Configurar no painel do Render em: Settings > Build Command
#   bash build.sh
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Cria o professor/superusuário automaticamente a partir de variáveis
# de ambiente, já que o plano gratuito do Render não dá acesso a Shell
# interativo para rodar "createsuperuser" manualmente. Não faz nada se
# as variáveis DJANGO_SUPERUSER_USERNAME/PASSWORD não estiverem
# definidas, e não sobrescreve a senha se o usuário já existir.
python manage.py create_default_superuser
