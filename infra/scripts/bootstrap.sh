#!/usr/bin/env bash
# ----------------------------------------------------------------------------
# Neuromancers Network — One-Time Server Bootstrap Script
#
# Run ONCE on a fresh Hetzner Cloud VPS (Ubuntu 24.04 LTS).
# Creates the deploy user, hardens SSH, installs Docker, and sets up
# the directory structure for Coolify.
#
# Usage (run as root on the fresh server):
#   curl -fsSL https://raw.githubusercontent.com/neuromancers/neuromancers_network/main/infra/scripts/server-bootstrap.sh | bash
# ----------------------------------------------------------------------------
set -euo pipefail

HETZNER_SSH_USER="${HETZNER_SSH_USER:-deploy}"
COOLIFY_ADMIN_USERNAME="${COOLIFY_ADMIN_USERNAME:-}"
COOLIFY_ADMIN_PASSWORD="${COOLIFY_ADMIN_PASSWORD:-}"
COOLIFY_ADMIN_EMAIL="${COOLIFY_ADMIN_EMAIL:-}"
HETZNER_SSH_PUBLIC_KEY="${HETZNER_SSH_PUBLIC_KEY:-}"
SSH_PORT="${SSH_PORT:-22}"

echo "=== Neuromancers Network — Server Bootstrap ==="
echo ""

# ── 1. Create deploy user ────────────────────────────────────────────
if ! id "$HETZNER_SSH_USER" &>/dev/null; then
    echo "[1/5] Creating deploy user: $HETZNER_SSH_USER"
    adduser --disabled-password --gecos "" "$HETZNER_SSH_USER"
    usermod -aG sudo "$HETZNER_SSH_USER"
    echo "$HETZNER_SSH_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/99-"$HETZNER_SSH_USER"
    chmod 440 /etc/sudoers.d/99-"$HETZNER_SSH_USER"
    mkdir -p "/home/$HETZNER_SSH_USER/.ssh"
    chmod 700 "/home/$HETZNER_SSH_USER/.ssh"
    chown "$HETZNER_SSH_USER:$HETZNER_SSH_USER" "/home/$HETZNER_SSH_USER/.ssh"
else
    echo "[1/5] Deploy user already exists: $HETZNER_SSH_USER"
    if [ ! -f /etc/sudoers.d/99-"$HETZNER_SSH_USER" ]; then
        echo "$HETZNER_SSH_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/99-"$HETZNER_SSH_USER"
        chmod 440 /etc/sudoers.d/99-"$HETZNER_SSH_USER"
    fi
fi

# ── 2. Add SSH public key only if needed ─────────────────────────────
if [ -f "/home/$HETZNER_SSH_USER/.ssh/authorized_keys" ] && [ -s "/home/$HETZNER_SSH_USER/.ssh/authorized_keys" ]; then
    echo "[2/5] authorized_keys already present for $HETZNER_SSH_USER; skipping"
elif [ -n "$HETZNER_SSH_PUBLIC_KEY" ]; then
    echo "[2/5] Installing SSH key from HETZNER_SSH_PUBLIC_KEY"
    printf '%s\n' "$HETZNER_SSH_PUBLIC_KEY" > "/home/$HETZNER_SSH_USER/.ssh/authorized_keys"
    chmod 600 "/home/$HETZNER_SSH_USER/.ssh/authorized_keys"
    chown "$HETZNER_SSH_USER:$HETZNER_SSH_USER" "/home/$HETZNER_SSH_USER/.ssh/authorized_keys"
else
    echo "[2/5] No SSH key provided and none exists; skipping key install"
fi

# ── 3. Harden SSH ───────────────────────────────────────────────────
echo "[3/5] Hardening SSH configuration..."
SSHD_CONFIG="/etc/ssh/sshd_config"
cp "$SSHD_CONFIG" "${SSHD_CONFIG}.bak"
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' "$SSHD_CONFIG"
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_CONFIG"
sed -i 's/^#\?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' "$SSHD_CONFIG"
sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' "$SSHD_CONFIG"
systemctl reload sshd

# ── 4. Install Coolify only if missing ───────────────────────────────
if [ -f "/data/coolify/source/.env" ]; then
    echo "[4/5] Coolify already installed; skipping"
else
    if [ -z "$COOLIFY_ADMIN_USERNAME" ] || [ -z "$COOLIFY_ADMIN_PASSWORD" ] || [ -z "$COOLIFY_ADMIN_EMAIL" ]; then
        echo "[4/5] Coolify is not installed and required COOLIFY_* values are missing"
        echo "Set COOLIFY_ADMIN_USERNAME, COOLIFY_ADMIN_PASSWORD, COOLIFY_ADMIN_EMAIL and re-run"
        exit 1
    fi
    echo "[4/5] Installing Coolify..."
    env ROOT_USERNAME="$COOLIFY_ADMIN_USERNAME" \
        ROOT_USER_PASSWORD="$COOLIFY_ADMIN_PASSWORD" \
        ROOT_USER_EMAIL="$COOLIFY_ADMIN_EMAIL" \
        bash -c "curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash"
fi
usermod -aG docker "$HETZNER_SSH_USER"

# ── 5. Create IaC directories ────────────────────────────────────────
echo "[5/5] Creating IaC directories..."
mkdir -p /opt/{gatus/config,beszel,scripts,backups}
chown -R "$HETZNER_SSH_USER:$HETZNER_SSH_USER" /opt/gatus /opt/beszel /opt/scripts /opt/backups

echo ""
echo "=== Bootstrap complete! ==="
echo ""
echo "Next steps:"
echo "  1. Log out and back in as $HETZNER_SSH_USER to verify SSH key access."
echo "  2. Run the Ansible playbook from CI/CD to apply full configuration."
echo "  3. Configure Coolify at http://$(hostname -I | awk '{print $1}'):8000"
