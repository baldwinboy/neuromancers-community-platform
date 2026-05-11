#!/usr/bin/env bash
set -euo pipefail

# Run cleanup only every 90 days (day-of-year modulo 90).
if [ "$((10#$(date +%j) % 90))" -ne 0 ]; then
    exit 0
fi

docker_bin="/usr/bin/docker"

# Coolify names containers dynamically, so target the running Django service by compose label and image.
django_container="$(${docker_bin} ps \
    --filter "label=com.docker.compose.service=django" \
    --filter "ancestor=neuromancers_network_production_django" \
    --format '{{.Names}}' | head -n 1)"

if [ -z "${django_container}" ]; then
    exit 0
fi

session_engine="$(${docker_bin} exec "${django_container}" python manage.py shell -c "from django.conf import settings; print(settings.SESSION_ENGINE)")"

case "${session_engine}" in
    django.contrib.sessions.backends.db|django.contrib.sessions.backends.cached_db)
        ${docker_bin} exec "${django_container}" python manage.py clearsessions
        ;;
    *)
        # Non-DB session engines do not use django_session table cleanup.
        exit 0
        ;;
esac
