#!/bin/sh

set -e  # Exit immediately if a command exits with a non-zero status

cd /green_power_backend

# Define color and style codes
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_step() {
    echo ""
    echo "${CYAN}${BOLD}==> $1${NC}"
}

# Collect static files
print_step "Collecting static files 📁"
python manage.py collectstatic --noinput

# Make database migrations
print_step "Creating database migrations 🛠️"
python manage.py makemigrations --noinput

# Apply database migrations
print_step "Applying database migrations 🗃️"
python manage.py migrate --noinput

# Start the Daphne server
print_step "Starting Daphne server 🚀"
exec daphne -b 0.0.0.0 -p 5000 green_power_backend.asgi:application
