export COMPOSE_FILE := "docker-compose.local.yml"

## Just does not yet manage signals for subprocesses reliably, which can lead to unexpected behavior.
## Exercise caution before expanding its usage in production environments.
## For more information, see https://github.com/casey/just/issues/2473 .


# Default command to list all available commands.
default:
    @just --list

# dev: Executes `manage.py` command in a development environment.
dev +args:
    @python ./manage.py {{ args }} --settings=config.settings.dev

# runserver: Run Django with Tailwind watch mode, but only for the development server
runserver:
    @python ./manage.py tailwind runserver --settings=config.settings.dev

# nuke: Clears all migrations and database files in a development environment
nuke:
    @rm -rf dev.db neuromancers_network/core/migrations neuromancers_network/emails/migrations neuromancers_network/events/migrations 

# createsuperuser: Creates a superuser in a dev environment
createsuperuser:
    @python ./manage.py shell -c "from django.contrib.auth import get_user_model; obj = get_user_model().objects.create_superuser('_neuro', '_default@neuromancers.org.uk', '_default_password')" --settings=config.settings.dev

# build: Build python image.
build *args:
    @echo "Building python image..."
    @docker compose build {{args}}

# up: Start up containers.
up:
    @echo "Starting up containers..."
    @docker compose up -d --remove-orphans

# down: Stop containers.
down:
    @echo "Stopping containers..."
    @docker compose down

# prune: Remove containers and their volumes.
prune *args:
    @echo "Killing containers and removing volumes..."
    @docker compose down -v {{args}}

# logs: View container logs
logs *args:
    @docker compose logs -f {{args}}

# manage: Executes `manage.py` command.
manage +args:
    @docker compose run --rm django python ./manage.py {{args}}

# worker: Start Celery worker.
worker:
    @docker compose run --rm django celery -A config.celery_app worker -l info

# beat: Start Celery beat.
beat:
    @docker compose run --rm django celery -A config.celery_app beat -l info

# Django Tailwind CLI: # Build production CSS
tailwind-build:
    @docker compose run --rm django python manage.py tailwind build

# Django Tailwind CLI: # Run Django with Tailwind watch mode
tailwind-watch:
    @docker compose run --rm django python manage.py tailwind watch

# Django Tailwind CLI: # Run Django with Tailwind watch mode, but only for the development server (not Celery)
tailwind-runserver:
    @docker compose run --rm django python manage.py tailwind runserver

# Django Tailwind CLI: # Build production CSS and collect static files
tailwind-prod:
    @docker compose run --rm django python manage.py tailwind build --minify
    @docker compose run --rm django python manage.py collectstatic --noinput

# test-email: Send a test email using the runtime backend (dev)
test-email +args:
    @docker compose run --rm django python manage.py shell -c "from django.core.mail import send_mail; send_mail('Test', 'Runtime SMTP is working.', None, ['{{args}}'])"