#!/usr/bin/env bash
set -o errexit

export CARGO_HOME="${CARGO_HOME:-/tmp/cargo}"

python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --noinput
