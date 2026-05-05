#!/usr/bin/env bash
set -o errexit

python manage.py collectstatic --noinput --verbosity 0
python manage.py migrate --noinput --verbosity 0
