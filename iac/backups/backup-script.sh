#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# Neuromancers Network — Database & Volume Backup Script
#
# Scheduled via cron on the Hetzner server (e.g. daily at 2 AM):
#   0 2 * * * /opt/scripts/backup-script.sh
#
# Backs up PostgreSQL dumps and Docker volumes to an S3-compatible bucket.
# ----------------------------------------------------------------------------
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────
AWS_ENDPOINT_URL_S3="${AWS_ENDPOINT_URL_S3:-}"
AWS_S3_BUCKET_NAME="${AWS_S3_BUCKET_NAME:-neuromancers-backups}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
BACKUP_DIR="/opt/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

# ── Ensure backup directory exists ───────────────────────────────────────
mkdir -p "$BACKUP_DIR"

# ── Backup PostgreSQL via Coolify-managed container ──────────────────────
DB_CONTAINER="$(docker ps --filter 'name=postgres' --format '{{.Names}}' | head -1)"
if [ -n "$DB_CONTAINER" ]; then
    echo "[$(date)] Dumping database from container: $DB_CONTAINER"
    docker exec "$DB_CONTAINER" pg_dumpall -U postgres \
        > "$BACKUP_DIR/postgres-$TIMESTAMP.sql"
    gzip -f "$BACKUP_DIR/postgres-$TIMESTAMP.sql"
    echo "[$(date)] Database dump complete."
else
    echo "[$(date)] WARNING: No PostgreSQL container found."
fi

# ── Backup Docker volumes (optional — Coolify handles its own) ───────────
# Uncomment to capture named volumes:
# for vol in $(docker volume ls -q); do
#     docker run --rm -v "$vol":/data -v "$BACKUP_DIR":/out alpine \
#         tar czf "/out/$vol-$TIMESTAMP.tar.gz" -C /data .
# done

# ── Upload to S3 ─────────────────────────────────────────────────────────
if [ -n "$AWS_ENDPOINT_URL_S3" ] && [ -n "$AWS_ACCESS_KEY_ID" ]; then
    echo "[$(date)] Uploading backups to s3://$AWS_S3_BUCKET_NAME/"
    for file in "$BACKUP_DIR"/*"$TIMESTAMP"*; do
        [ -f "$file" ] || continue
        aws --endpoint-url "$AWS_ENDPOINT_URL_S3" s3 cp "$file" "s3://$AWS_S3_BUCKET_NAME/" \
            --only-show-errors
    done
    echo "[$(date)] Upload complete."
else
    echo "[$(date)] WARNING: S3 not configured; backups kept locally."
fi

# ── Cleanup old backups ──────────────────────────────────────────────────
echo "[$(date)] Removing backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -type f -mtime "+$RETENTION_DAYS" -delete

echo "[$(date)] Backup job finished."
