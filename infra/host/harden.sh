#!/usr/bin/env bash
# One-time host hardening for the production VM (Oracle A1 / Hetzner).
# Run as root after first SSH. Does not deploy the app.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ufw fail2ban unattended-upgrades logrotate

# SSH + HTTP/S only
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Fail2ban SSH jail (default)
systemctl enable --now fail2ban

# Unattended security upgrades
dpkg-reconfigure -f noninteractive unattended-upgrades || true

# Docker log rotation hint (Compose json-file defaults are fine; document override)
mkdir -p /etc/docker
if [[ ! -f /etc/docker/daemon.json ]]; then
  cat >/etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "20m", "max-file": "5" }
}
EOF
fi

echo "OK host harden. Reboot if docker daemon.json was newly written."
