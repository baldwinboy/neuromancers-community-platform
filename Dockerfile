ARG PYTHON_VERSION=3.12-slim

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Tailscale
RUN curl -fsSL https://tailscale.com/install.sh | sh

RUN mkdir -p /code
WORKDIR /code

# Install Python dependencies
RUN pip install poetry
COPY pyproject.toml poetry.lock /code/
RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-root --no-interaction

# Copy application code
COPY . /code

# Collect static files using build secrets
RUN python manage.py collectstatic --noinput --clear

# Expose the port that Gunicorn will run on
EXPOSE 8000

# Runtime command with Tailscale
CMD ["sh", "-c", "tailscale up --auth-key $TAILSCALE_AUTHKEY && TAILSCALE_IP=$(tailscale ip -4) && gunicorn --bind $TAILSCALE_IP:8000 --workers 2 neuromancers.wsgi"]
