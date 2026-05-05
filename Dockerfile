ARG PYTHON_VERSION=3.12-slim-trixie

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# uv configuration
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Add venv to PATH so installed packages are available
ENV PATH="/app/.venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    git \
    ca-certificates \
    iptables \
    dnsutils \
    procps \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Get Tailscale auth key from build secret and set it as an environment variable for the build (if needed for build steps)
RUN --mount=type=secret,id=TAILSCALE_AUTHKEY \
    export TAILSCALE_AUTHKEY="$(cat /run/secrets/TAILSCALE_AUTHKEY)" TS_ACCEPT_DNS=1

# Copy Tailscale binaries from the tailscale image on GitHub Container Registry.
RUN mkdir -p /app
COPY --from=ghcr.io/tailscale/tailscale:stable /usr/local/bin/tailscaled /app/tailscaled
COPY --from=ghcr.io/tailscale/tailscale:stable /usr/local/bin/tailscale /app/tailscale
RUN mkdir -p /var/run/tailscale /var/cache/tailscale /var/lib/tailscale \
    && chown -R root:root /var/run/tailscale /var/cache/tailscale /var/lib/tailscale \
    && chmod -R 755 /var/run/tailscale /var/cache/tailscale /var/lib/tailscale

# Note: IP forwarding (sysctl) must be configured at runtime, not build time
# The entrypoint script handles this

# Change the working directory to the `app` directory
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
COPY . .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Sync the project (installs the project itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Collect static files (venv is on PATH so python/gunicorn are available)
RUN python manage.py collectstatic --noinput --clear

# Note: Database migrations and setup commands run at runtime in entrypoint.sh
# (they require database access which isn't available during build)

# Expose ports (443 for HTTPS, 8000 for HTTP fallback)
EXPOSE 443 8000

# Run the entrypoint script (it execs gunicorn bound to Tailscale IP)
ENTRYPOINT ["/app/entrypoint.sh"]
