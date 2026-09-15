#!/usr/bin/env bash
# Script de build executado pelo Render a cada deploy.
# Configurar no painel do Render em: Settings > Build Command
#   bash build.sh
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
