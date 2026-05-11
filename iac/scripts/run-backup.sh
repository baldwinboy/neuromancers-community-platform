#!/usr/bin/env bash
set -euo pipefail

TOKEN_FILE="/opt/backups/.bws_token"

if [ ! -r "$TOKEN_FILE" ]; then
    echo "[$(date)] ERROR: Missing Bitwarden token file: $TOKEN_FILE" >&2
    exit 1
fi

BWS_ACCESS_TOKEN="$(tr -d '\r\n' < "$TOKEN_FILE")"
if [ -z "$BWS_ACCESS_TOKEN" ]; then
    echo "[$(date)] ERROR: Bitwarden token file is empty" >&2
    exit 1
fi

export BWS_ACCESS_TOKEN
exec bws run -- /opt/scripts/backup-script.sh