SHELL=/bin/bash
.DEFAULT_GOAL := help
NEUROMANCERS_VENV := .venv/neuromancers/bin/activate
NEUROMANCERS_VENV_PATH := .venv/neuromancers

help: ## Show this help.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

venv: # Create virtual environment
	uv venv $(NEUROMANCERS_VENV_PATH)

venv-delete: # Delete virtual environment
	rm -rf $(NEUROMANCERS_VENV_PATH)

venv-shortcut: # Provides command to activate virtual environment
	@echo "Run 'source $(NEUROMANCERS_VENV)' to activate the virtual environment"

django-migrate: # Run Django migrations
	python ./manage.py migrate

django-makemigrations: # Create Django migrations
	python ./manage.py makemigrations

django-setupdefaultgroups: # Setup default groups
	python ./manage.py setup_default_groups

django-publishsessionsindex: # Publish all unpublished SessionsIndexPages
	python ./manage.py publish_sessions_index


django-createsuperuser: # Create a default superuser
django-createsuperuser: DJANGO_SUPER_USERNAME ?= _neuro
django-createsuperuser: DJANGO_SUPER_PASSWORD ?= _default_password
django-createsuperuser: DJANGO_SUPER_EMAIL ?= _default@neuromancers.org.uk
django-createsuperuser:
	@echo "import sys; from django.contrib.auth import get_user_model; obj = get_user_model().objects.create_superuser('$(DJANGO_SUPER_USERNAME)', '$(DJANGO_SUPER_EMAIL)', '$(DJANGO_SUPER_PASSWORD)');" | python manage.py shell >> /dev/null
	@echo
	@echo "Superuser details: "
	@echo
	@echo "    $(DJANGO_SUPER_USERNAME):$(DJANGO_SUPER_PASSWORD)"
	@echo

django-findstatic: # Find files that will be added when a `static` directory is generated
	python ./manage.py findstatic

django-collectstatic: # Generate `static` directory
	sass assets/scss/styles.scss assets/css/styles.css
	scripts/load_icons.sh assets/icons templates/includes/sprite.svg
	python ./manage.py collectstatic -i scss -i icons

django-runserver: # Start Django server
	python ./manage.py runserver

django-test:
	python ./manage.py test --noinput . apps

django-shell: # Create a Django shell
	python ./manage.py shell

update-requirements: # Compile and update requirements from .in files
	pip-compile requirements/base.in
	pip-compile requirements/development.in
	pip-compile requirements/production.in

install: # Install Python development requirements
	uv pip install -r requirements/development.txt
install-prod: # Install Python production requirements
	uv pip install -r requirements/production.txt

dev: install django-makemigrations django-migrate django-collectstatic django-runserver

sass-watch: # Compile Sass on demand
	sass --watch assets/scss/styles.scss assets/css/styles.css

sprite: # Load custom SVGs
	scripts/load_icons.sh assets/icons templates/includes/sprite.svg

lint-git-files: # Lint files tracked by Git
	git status -s | cut -c4- | xargs pre-commit run --files
