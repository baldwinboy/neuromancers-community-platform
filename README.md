# NEUROMANCERS Community Platform

NEUROMANCERS community platform for attending and scheduling support sessions. Built with Django.

# Requirements

- [Make GNU](https://www.gnu.org/software/make/)
- [uv](https://docs.astral.sh/uv/)
- [Dart Sass](https://sass-lang.com/install/)

# Relevant Documentation

- [Django](https://docs.djangoproject.com/en/5.2/)
- [Wagtail](https://wagtail.org/)
- [wagtailmenus](https://wagtailmenus.readthedocs.io/en/stable/index.html)
- [allauth](https://docs.allauth.org/en/latest/index.html)
- [Stripe](https://docs.stripe.com/)
- [Whereby](https://docs.whereby.com/)
- [heroicons](https://github.com/adamchainz/heroicons)

# Local setup

1. Ensure [Make GNU](https://www.gnu.org/software/make/) and [uv](https://docs.astral.sh/uv/) and installed and available in your shell's path.
2. Run `make venv` to create a virtual environment.
3. Run `make venv-shortcut` to create a shortcut that will allow you to activate the virtual environment.
4. Run `source .venv/neuromancers/bin/activate`.
5. Setup environment variables. Duplicate `.env.development` and change the name to `.env` to use development environment variables. Variables for other environments should be populated from a secure source, such as password manager and **should not be committed to the repository**.
6. Run `make fresh`. The server should be available on http://localhost:8000 (if port 8000 is open).
7. On subsequent runs, run `make dev`.
