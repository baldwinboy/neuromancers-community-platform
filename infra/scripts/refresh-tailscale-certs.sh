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

# Exit if any variable is missing.
if [ -z "${TS_APP_DOMAIN}" ] || [ -z "${TS_METRICS_DOMAIN}" ] || [ -z "${TS_MONITOR_DOMAIN}" ] || [ -z "${TS_PAAS_DOMAIN}" ]; then
    echo "Missing one or more required environment variables: TS_APP_DOMAIN, TS_METRICS_DOMAIN, TS_MONITOR_DOMAIN, TS_PAAS_DOMAIN"
    exit 1
fi

# Ensure Tailscale is running.
tailscale status >/dev/null 2>&1 || exit 1

# Generate Tailscale certificates for Django, Prometheus, and Coolify.
tailscale cert --cert-file /certs/app/cert.pem --key-file /certs/app/key.pem "${TS_APP_DOMAIN}"
tailscale cert --cert-file /certs/metrics/cert.pem --key-file /certs/metrics/key.pem "${TS_METRICS_DOMAIN}"
tailscale cert --cert-file /certs/monitor/cert.pem --key-file /certs/monitor/key.pem "${TS_MONITOR_DOMAIN}"
tailscale cert --cert-file /certs/paas/cert.pem --key-file /certs/paas/key.pem "${TS_PAAS_DOMAIN}"

# Update last refresh timestamp
echo "$(date +%s)" > /etc/tailscale/cert-refreshed-at.txt
