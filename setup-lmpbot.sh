#!/bin/bash
# =============================================================================
#  LMPBot Beta - Raspberry Pi Setup Script
#  Auto-installs Node.js deps, configures systemd, sets up auto-updates
#
#  Usage:  chmod +x setup-lmpbot.sh && sudo ./setup-lmpbot.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[x]${NC} $1"; }
info()  { echo -e "${CYAN}[i]${NC} $1"; }

REPO_URL="https://github.com/lamp-studios/lmpbot-beta.git"
REPO_BRANCH="main"
BOT_USER="${SUDO_USER:-$USER}"
INSTALL_DIR="/home/${BOT_USER}/lmpbot-beta"
SERVICE_NAME="lmpbot"
UPDATE_TIMER_INTERVAL="*:0/5"
NODE_MAJOR="20"

if [[ $EUID -ne 0 ]]; then
    err "Run this script with sudo."
    exit 1
fi

echo ""
echo -e "${CYAN}  LMPBot Beta - Raspberry Pi Installer${NC}"
echo ""

# -- system deps --------------------------------------------------------------

info "Updating packages..."
apt-get update -qq

info "Installing prerequisites..."
apt-get install -y -qq git curl ca-certificates > /dev/null 2>&1
log "System deps installed."

# -- node.js + pnpm -----------------------------------------------------------

if ! command -v node > /dev/null 2>&1 || [[ "$(node -v | cut -d. -f1 | tr -d 'v')" -lt "$NODE_MAJOR" ]]; then
    info "Installing Node.js ${NODE_MAJOR}.x..."
    curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs > /dev/null 2>&1
fi
log "Node.js $(node -v) ready."

info "Enabling pnpm via corepack..."
corepack enable > /dev/null 2>&1
corepack prepare pnpm@latest --activate > /dev/null 2>&1
log "pnpm $(pnpm -v) ready."

# -- clone repo ---------------------------------------------------------------

if [[ -d "$INSTALL_DIR/.git" ]]; then
    warn "Repo already exists. Pulling latest..."
    sudo -u "$BOT_USER" git -C "$INSTALL_DIR" pull --ff-only origin "$REPO_BRANCH"
else
    info "Cloning repo..."
    sudo -u "$BOT_USER" git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi
log "Repo ready at ${INSTALL_DIR}."

# -- purge old python install -------------------------------------------------

if [[ -d "$INSTALL_DIR/.venv" ]] || [[ -f "$INSTALL_DIR/requirements.txt" ]] || \
   compgen -G "$INSTALL_DIR/*.py" > /dev/null 2>&1; then
    warn "Detected old Python install — cleaning up Python artifacts..."
    # The new JS code arrives via git pull above; here we only strip Python
    # leftovers git can't remove (untracked venv/caches) plus any stray .py files.
    rm -rf "$INSTALL_DIR/.venv"
    rm -f "$INSTALL_DIR/requirements.txt"
    find "$INSTALL_DIR" -path "$INSTALL_DIR/node_modules" -prune -o \
        -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$INSTALL_DIR" -path "$INSTALL_DIR/node_modules" -prune -o \
        -type f -name "*.py" -delete 2>/dev/null || true
    find "$INSTALL_DIR" -path "$INSTALL_DIR/node_modules" -prune -o \
        -type f -name "*.pyc" -delete 2>/dev/null || true
    log "Python artifacts removed."
fi

# -- node deps ----------------------------------------------------------------

info "Installing Node.js dependencies..."
sudo -u "$BOT_USER" sh -c "cd '$INSTALL_DIR' && pnpm install --prod --frozen-lockfile"
log "Node.js dependencies installed."

# -- .env setup ---------------------------------------------------------------

ENV_FILE="${INSTALL_DIR}/.env"

echo ""
echo -e "${CYAN}--- Discord Bot Token Setup ---${NC}"

if [[ -f "$ENV_FILE" ]]; then
    warn ".env already exists. Edit manually if needed: nano ${ENV_FILE}"
    if ! grep -q '^MONGODB_URI=' "$ENV_FILE"; then
        echo "MONGODB_URI=" >> "$ENV_FILE"
        log "Added missing MONGODB_URI= line to .env."
    fi
else
    read -rp "  Paste your Discord bot token (or Enter to skip): " BOT_TOKEN

    cat > "$ENV_FILE" <<EOF
DANGER_DONTSHARETOYKEN=${BOT_TOKEN:-PASTE_YOUR_TOKEN_HERE}
GEMINI_API_KEY=
MONGODB_URI=
EOF
    chown "${BOT_USER}:${BOT_USER}" "$ENV_FILE"
    chmod 600 "$ENV_FILE"

    if [[ -n "$BOT_TOKEN" ]]; then
        log "Token saved."
    else
        warn "No token entered. Edit .env before starting: nano ${ENV_FILE}"
    fi
fi

# -- systemd service -----------------------------------------------------------

info "Creating systemd service..."

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=LMPBot Beta Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${BOT_USER}
Group=${BOT_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=$(command -v node) ${INSTALL_DIR}/index.js
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${INSTALL_DIR}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service" > /dev/null 2>&1
log "Service enabled."

# -- auto-updater --------------------------------------------------------------

UPDATER_SCRIPT="/usr/local/bin/lmpbot-updater.sh"

cat > "$UPDATER_SCRIPT" <<'UPDATER_EOF'
#!/bin/bash
set -e
INSTALL_DIR="__INSTALL_DIR__"
SERVICE_NAME="__SERVICE_NAME__"
BOT_USER="__BOT_USER__"
REPO_BRANCH="__REPO_BRANCH__"

cd "$INSTALL_DIR"
sudo -u "$BOT_USER" git fetch origin "$REPO_BRANCH" --quiet 2>/dev/null

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/${REPO_BRANCH}")
[[ "$LOCAL" == "$REMOTE" ]] && exit 0

logger -t lmpbot-updater "Updating ${LOCAL:0:7} -> ${REMOTE:0:7}"
sudo -u "$BOT_USER" git pull --ff-only origin "$REPO_BRANCH" 2>/dev/null
sudo -u "$BOT_USER" sh -c "cd '$INSTALL_DIR' && pnpm install --prod --frozen-lockfile" 2>/dev/null
systemctl restart "$SERVICE_NAME"
UPDATER_EOF

sed -i "s|__INSTALL_DIR__|${INSTALL_DIR}|g" "$UPDATER_SCRIPT"
sed -i "s|__SERVICE_NAME__|${SERVICE_NAME}|g" "$UPDATER_SCRIPT"
sed -i "s|__BOT_USER__|${BOT_USER}|g" "$UPDATER_SCRIPT"
sed -i "s|__REPO_BRANCH__|${REPO_BRANCH}|g" "$UPDATER_SCRIPT"
chmod +x "$UPDATER_SCRIPT"

cat > "/etc/systemd/system/${SERVICE_NAME}-updater.service" <<EOF
[Unit]
Description=LMPBot Auto-Updater
After=network-online.target

[Service]
Type=oneshot
ExecStart=${UPDATER_SCRIPT}
EOF

cat > "/etc/systemd/system/${SERVICE_NAME}-updater.timer" <<EOF
[Unit]
Description=Run LMPBot updater every 5 minutes

[Timer]
OnCalendar=${UPDATE_TIMER_INTERVAL}
Persistent=true
RandomizedDelaySec=30

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now "${SERVICE_NAME}-updater.timer" > /dev/null 2>&1
log "Auto-updater enabled."

# -- start bot -----------------------------------------------------------------

echo ""
if grep -q "PASTE_YOUR_TOKEN_HERE" "$ENV_FILE" 2>/dev/null; then
    warn "Token not set. Start manually after editing .env:"
    warn "    sudo systemctl start ${SERVICE_NAME}"
else
    info "Starting bot..."
    systemctl start "${SERVICE_NAME}" || true
    sleep 2
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log "Bot is running!"
    else
        err "Failed to start. Check: journalctl -u ${SERVICE_NAME} -f"
    fi
fi

echo ""
echo "  Commands:"
echo "    start:   sudo systemctl start ${SERVICE_NAME}"
echo "    stop:    sudo systemctl stop ${SERVICE_NAME}"
echo "    logs:    journalctl -u ${SERVICE_NAME} -f"
echo "    token:   nano ${ENV_FILE}"
echo ""
