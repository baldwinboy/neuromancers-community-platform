#!/usr/bin/env bash
set -euo pipefail

# Get date of last refresh
DAY_SECS=86400
LAST_REFRESH=$(cat /etc/tailscale/cert-refreshed-at.txt)
NOW=$(date +%s)
DIFF=$((NOW - LAST_REFRESH))
DIFF_DAYS=$((DIFF / DAY_SECS))

# Exit if last refresh was less than 90 days ago.
if [ "$DIFF_DAYS" -lt 90 ]; then
    echo "Last refresh was less than 90 days ago; not refreshing certificates"
    exit 0
fi

echo "Last refresh was more than 90 days ago; refreshing certificates"

# Exit if the variable is missing.
if [ -z "${TS_PAAS_DOMAIN}" ]; then
    echo "Missing required environment variable: TS_PAAS_DOMAIN"
    exit 1
fi

# Ensure Tailscale is running.
tailscale status >/dev/null 2>&1 || exit 1

# Generate the Tailscale certificate for the Coolify host.
tailscale cert --cert-file /certs/paas/cert.pem --key-file /certs/paas/key.pem "${TS_PAAS_DOMAIN}"

# Update last refresh timestamp
echo "$(date +%s)" > /etc/tailscale/cert-refreshed-at.txt
