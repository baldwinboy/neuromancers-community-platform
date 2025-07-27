SHELL=/bin/bash
.DEFAULT_GOAL := help

help: ## Show this help.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

venv: # Create virtual environment
	uv venv .venv/neuromancers

venv-delete: # Delete virtual environment
	rm -rf .venv/neuromancers

venv-shortcut: # Creates a shortcut to activate virtual environment
	@alias venv_activate="source .venv/neruomancers/bin/activate"
	@echo "Run `venv_activate` to activate the virtual environment"

django-migrate: # Run Django migrations
	python ./manage.py migrate

django-makemigrations: # Create Django migrations
	python ./manage.py makemigrations

django-createsuperuser: # Create a default superuser
django-createsuperuser: DJANGO_SUPER_USERNAME ?= _default@neuromancers
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
	sass assets/scss/styles.scss assets/css/styles.css && python ./manage.py collectstatic -i scss

django-runserver: # Start Django server
	python ./manage.py runserver

django-test:
	python ./manage.py test --noinput . apps

django-shell: # Create a Django shell
	python ./manage.py shell

update-python-dev-requirements: # Update Python development requirements
	uv pip freeze > requirements/development.txt
update-python-prod-requirements: # Update Python production requirements
	pipreqs --savepath requirements/production.txt --ignore .venv
update-python-requirements: update-python-dev-requirements update-python-prod-requirements

install-python-dev-requirements: # Install Python development requirements
	uv pip install -r requirements/development.txt
install-python-prod-requirements: # Install Python production requirements
	uv pip install -r requirements/production.txt

dev: install-python-dev-requirements django-makemigrations django-migrate django-collectstatic django-runserver

sass-watch: # Compile Sass on demand
	sass --watch assets/scss/styles.scss assets/css/styles.css
