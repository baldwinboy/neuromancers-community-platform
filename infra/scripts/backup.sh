#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# Neuromancers Network — Database & Volume Backup Script
#
# Scheduled via GitHub Actions (daily at 02:00 UTC) or cron on the host:
#   0 2 * * * /opt/scripts/backup.sh
#
# Backs up PostgreSQL dumps to an S3-compatible bucket.
# ----------------------------------------------------------------------------
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────
: "${AWS_ENDPOINT_URL_S3:?AWS_ENDPOINT_URL_S3 is required}"
: "${AWS_S3_BUCKET_NAME:?AWS_S3_BUCKET_NAME is required}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is required}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is required}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
BACKUP_DIR="/opt/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

if [[ -z "${AWS_DEFAULT_REGION:-}" && -n "${AWS_REGION:-}" ]]; then
    export AWS_DEFAULT_REGION="$AWS_REGION"
fi

if ! command -v aws >/dev/null 2>&1; then
    echo "[$(date)] ERROR: aws CLI not found." >&2
    exit 1
fi

# ── Ensure backup directory exists ───────────────────────────────────────
mkdir -p "$BACKUP_DIR"

# ── Backup PostgreSQL via Coolify-managed container ──────────────────────
DB_CONTAINER="$(docker ps --filter 'name=postgres' --format '{{.Names}}' | head -1)"
if [[ -z "$DB_CONTAINER" ]]; then
    echo "[$(date)] ERROR: no PostgreSQL container found." >&2
    exit 1
fi

echo "[$(date)] Dumping database from container: $DB_CONTAINER"
DUMP_TMP="$BACKUP_DIR/postgres-$TIMESTAMP.sql.partial"
DUMP_FILE="$BACKUP_DIR/postgres-$TIMESTAMP.sql"
trap 'rm -f "$DUMP_TMP"' EXIT

if ! docker exec "$DB_CONTAINER" pg_dumpall -U postgres > "$DUMP_TMP"; then
    echo "[$(date)] ERROR: pg_dumpall failed." >&2
    exit 1
fi

if [[ ! -s "$DUMP_TMP" ]]; then
    echo "[$(date)] ERROR: database dump is empty." >&2
    exit 1
fi

mv "$DUMP_TMP" "$DUMP_FILE"
gzip -f "$DUMP_FILE"
echo "[$(date)] Database dump complete."

# ── Backup Docker volumes (optional — Coolify handles its own) ───────────
# Uncomment to capture named volumes:
# for vol in $(docker volume ls -q); do
#     docker run --rm -v "$vol":/data -v "$BACKUP_DIR":/out alpine \
#         tar czf "/out/$vol-$TIMESTAMP.tar.gz" -C /data .
# done

# ── Upload to S3 ─────────────────────────────────────────────────────────
echo "[$(date)] Uploading backups to s3://$AWS_S3_BUCKET_NAME/"
for file in "$BACKUP_DIR"/*"$TIMESTAMP"*; do
    [[ -f "$file" ]] || continue
    aws --endpoint-url "$AWS_ENDPOINT_URL_S3" s3 cp "$file" "s3://$AWS_S3_BUCKET_NAME/" \
        --only-show-errors
done
echo "[$(date)] Upload complete."

# ── Cleanup old backups ──────────────────────────────────────────────────
echo "[$(date)] Removing backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -type f -mtime "+$RETENTION_DAYS" -delete

echo "[$(date)] Backup job finished."
