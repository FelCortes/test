#!/bin/bash
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn --bind=0.0.0.0:8000 --workers=4 banco_mgti.wsgi