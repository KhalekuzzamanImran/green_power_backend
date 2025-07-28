#!/bin/sh

set -e

echo "🚀 Running collectstatic..."
python manage.py collectstatic --noinput

echo "📦 Making migrations..."
python manage.py makemigrations

echo "🧱 Applying migrations..."
python manage.py migrate

echo "🚀 Starting Daphne..."
exec daphne green_power_backend.asgi:application --bind 0.0.0.0 --port 5000
