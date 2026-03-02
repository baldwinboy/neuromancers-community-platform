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
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy Tailscale binaries from the tailscale image on GitHub Container Registry.
RUN mkdir -p /app
COPY --from=ghcr.io/tailscale/tailscale:stable /usr/local/bin/tailscaled /app/tailscaled
COPY --from=ghcr.io/tailscale/tailscale:stable /usr/local/bin/tailscale /app/tailscale
RUN mkdir -p /var/run/tailscale /var/cache/tailscale /var/lib/tailscale \
    && chown -R root:root /var/run/tailscale /var/cache/tailscale /var/lib/tailscale \
    && chmod -R 755 /var/run/tailscale /var/cache/tailscale /var/lib/tailscale

# Enable IP forwarding for both IPv4 and IPv6 (required for subnet routing)
RUN mkdir -p /etc/sysctl.d \
    && touch /etc/sysctl.d/99-tailscale.conf \
    && echo 'net.ipv4.ip_forward = 1' > /etc/sysctl.d/99-tailscale.conf \
    && echo 'net.ipv6.conf.all.forwarding = 1' >> /etc/sysctl.d/99-tailscale.conf \
    && sysctl -p /etc/sysctl.d/99-tailscale.conf

# Start the Tailscale daemon in the background (required for subnet routing)
RUN tailscaled --state=mem: --socket=/var/run/tailscale/tailscaled.sock &

# Set network prefix
RUN export NETWORK_IPV6=$(dig +short aaaa neuromancers-community-platform.internal @fdaa::3) \
    && export NETWORK_IPV4=$(dig +short a neuromancers-community-platform.internal @fdaa::3) \
    && echo "NETWORK_IPV6=$NETWORK_IPV6" >> /etc/environment \
    && echo "NETWORK_IPV4=$NETWORK_IPV4" >> /etc/environment

# Change the working directory to the `app` directory
WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy the project into the image
COPY . .

# Sync the project (installs the project itself)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Collect static files (venv is on PATH so python/gunicorn are available)
RUN python manage.py collectstatic --noinput --clear

# Migrate the database (venv is on PATH so python/gunicorn are available)
RUN python manage.py migrate --noinput

# Setup default groups
RUN python manage.py setup_default_groups || true

# Publish sessions index page
RUN python manage.py publish_sessions_index || true

# Expose the port that Gunicorn will run on
EXPOSE 8000

# Allow entrypoint.sh to be executable
RUN chmod +x /app/entrypoint.sh

# Run the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]
