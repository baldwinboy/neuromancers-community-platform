#!/bin/bash
set -e

# Enable IP forwarding (required for Tailscale subnet routing)
# Note: Container must have NET_ADMIN capability for this to work
echo "Enabling IP forwarding..."
if sysctl -w net.ipv4.ip_forward=1 2>/dev/null; then
    echo "IPv4 forwarding enabled"
else
    echo "Warning: Could not enable IPv4 forwarding (may require --cap-add=NET_ADMIN)"
fi

if sysctl -w net.ipv6.conf.all.forwarding=1 2>/dev/null; then
    echo "IPv6 forwarding enabled"
else
    echo "Warning: Could not enable IPv6 forwarding (may require --cap-add=NET_ADMIN)"
fi

echo "Starting Tailscale daemon..."
/app/tailscaled --state=/var/lib/tailscale/tailscaled.state --socket=/var/run/tailscale/tailscaled.sock &

# Wait for tailscaled to be ready
sleep 2

# Get the IPv6 dynamically (example using dig)
IPV6=$(dig +short aaaa neuromancers-community-platform.internal @fdaa::3)

# Compute network prefix (first 3 hextets)
NETWORK_PREFIX=$(echo $IPV6 | cut -d':' -f1-3)::/48

echo "Connecting to Tailscale network..."
# Run Tailscale with the prefix
/app/tailscale up \
  --auth-key="${TAILSCALE_AUTHKEY}" \
  --advertise-connector \
  --advertise-routes="${NETWORK_PREFIX}" \
  --advertise-tags="tag:neuromancers-community-platform" \
  --hostname="neuromancers-community-platform" \
  --accept-routes

IPV4=$(/app/tailscale ip -4)
echo "Tailscale IP: ${IPV4}"

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Setup default groups (ignore errors if already exists)
echo "Setting up default groups..."
python manage.py setup_default_groups || true

# Publish sessions index page (ignore errors if already exists)
echo "Publishing sessions index..."
python manage.py publish_sessions_index || true

# Run the main application (Gunicorn)
echo "Starting Gunicorn on ${IPV4}:8000..."
exec gunicorn --bind "${IPV4}:8000" --workers 2 neuromancers.wsgi
