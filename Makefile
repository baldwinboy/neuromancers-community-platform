SHELL=/bin/bash
.DEFAULT_GOAL := help

help: ## Show this help.
	@grep -E '^[a-zA-Z0-9 -]+:.*#'  Makefile | sort | while read -r l; do printf "\033[1;32m$$(echo $$l | cut -f 1 -d':')\033[00m:$$(echo $$l | cut -f 2- -d'#')\n"; done

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

django-runserver: # Start Django server
	python ./manage.py runserver

django-test:
	python ./manage.py test --noinput . apps

update-python-dev-requirements: # Update Python development requirements
	pip freeze > requirements/development.txt
update-python-prod-requirements: # Update Python production requirements
	pipreqs --savepath requirements/production.txt --ignore .venv

install-python-dev-requirements: # Install Python development requirements
	pip install -r requirements/development.txt
install-python-prod-requirements: # Install Python production requirements
	pip install -r requirements/production.txt
