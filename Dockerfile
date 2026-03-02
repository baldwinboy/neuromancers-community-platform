ARG PYTHON_VERSION=3.12-slim-trixie

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Tailscale
RUN curl -fsSL https://tailscale.com/install.sh | sh

# Change the working directory to the `app` directory
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
COPY . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Collect static files using build secrets
RUN uv run python manage.py collectstatic --noinput --clear

# Expose the port that Gunicorn will run on
EXPOSE 8000

# Runtime command with Tailscale
CMD ["sh", "-c", "tailscale up --auth-key $TAILSCALE_AUTHKEY && TAILSCALE_IP=$(tailscale ip -4) && uv run gunicorn --bind $TAILSCALE_IP:8000 --workers 2 neuromancers.wsgi"]
