#!/usr/bin/env bash
# One-shot setup for a dedicated Ubuntu/Debian server that runs only this bot.
#
# Run as root (or via sudo) FROM the cloned repo, e.g.:
#   git clone <repo-url> /opt/funpay-steamguard-bot
#   cd /opt/funpay-steamguard-bot
#   sudo bash deploy/setup_server.sh
#
# What it does:
#   - installs system packages (python3, venv, ufw, chrony, unattended-upgrades)
#   - creates a dedicated non-root system user that owns the bot
#   - creates a venv and installs requirements.txt
#   - sets up .env (from .env.example) with correct ownership/permissions
#   - installs and enables the systemd service (does NOT start it, since
#     .env still needs real credentials)
#   - enables automatic security updates
#   - enables chrony (NTP) time sync
#   - configures ufw to allow only SSH inbound
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run this script as root (sudo bash deploy/setup_server.sh)." >&2
    exit 1
fi

SERVICE_USER="${SERVICE_USER:-funpaybot}"
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Installing system packages"
apt-get update
apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip \
    ufw chrony unattended-upgrades

echo "==> Creating service user '${SERVICE_USER}' (if missing)"
if ! id "${SERVICE_USER}" &>/dev/null; then
    useradd --system --create-home --home-dir "/home/${SERVICE_USER}" --shell /usr/sbin/nologin "${SERVICE_USER}"
fi

echo "==> Handing ownership of ${INSTALL_DIR} to ${SERVICE_USER}"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}"

echo "==> Creating virtualenv and installing dependencies"
sudo -u "${SERVICE_USER}" python3 -m venv "${INSTALL_DIR}/.venv"
sudo -u "${SERVICE_USER}" "${INSTALL_DIR}/.venv/bin/pip" install --upgrade pip
sudo -u "${SERVICE_USER}" "${INSTALL_DIR}/.venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

if [[ ! -f "${INSTALL_DIR}/.env" ]]; then
    echo "==> Creating .env from .env.example (fill in real values before starting the service!)"
    sudo -u "${SERVICE_USER}" cp "${INSTALL_DIR}/.env.example" "${INSTALL_DIR}/.env"
fi
chmod 600 "${INSTALL_DIR}/.env"
chown "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}/.env"

echo "==> Installing systemd unit"
sed \
    -e "s#__INSTALL_DIR__#${INSTALL_DIR}#g" \
    -e "s#__SERVICE_USER__#${SERVICE_USER}#g" \
    "${INSTALL_DIR}/deploy/funpay-bot.service" > /etc/systemd/system/funpay-bot.service
systemctl daemon-reload
systemctl enable funpay-bot.service

echo "==> Enabling automatic security updates"
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> Enabling time sync (chrony)"
systemctl enable --now chrony

echo "==> Configuring firewall (allow SSH only)"
ufw allow OpenSSH
ufw --force enable

cat <<EOF

Setup complete.

Next steps:
  1. Fill in real credentials:
       sudo -u ${SERVICE_USER} nano ${INSTALL_DIR}/.env
  2. Start the bot:
       systemctl start funpay-bot
  3. Check status / logs:
       systemctl status funpay-bot
       journalctl -u funpay-bot -f
       tail -f ${INSTALL_DIR}/logs/bot.log
EOF
