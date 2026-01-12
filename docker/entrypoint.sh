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

is_true() {
    case "${1:-}" in
        true|TRUE|1|yes|YES) return 0 ;;
        *) return 1 ;;
    esac
}

# Collect static files
if is_true "${COLLECTSTATIC:-true}"; then
    print_step "Collecting static files 📁"
    python manage.py collectstatic --noinput
else
    print_step "Skipping collectstatic"
fi

# Apply database migrations
if is_true "${RUN_MIGRATIONS:-true}"; then
    print_step "Applying database migrations 🗃️"
    python manage.py migrate --noinput
else
    print_step "Skipping migrations"
fi

# Start the Daphne server
print_step "Starting Daphne server 🚀"
exec daphne -b 0.0.0.0 -p 5000 config.asgi:application
