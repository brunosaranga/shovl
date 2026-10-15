#!/usr/bin/env bash
# Build command for the web service on Render:  bash build.sh
# Runs on every deploy, with the service's environment variables already set.
set -o errexit

pip install -r requirements.txt

# Refuses to deploy if a production safety setting is off (DEBUG left on, for example).
python manage.py check --deploy --fail-level WARNING

python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py createcachetable
