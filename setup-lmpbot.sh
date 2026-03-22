#!/bin/bash
# =============================================================================
#  LMPBot Beta - Raspberry Pi Setup Script
#  Auto-installs, configures systemd, and sets up auto-updates
#
#  Usage:  chmod +x setup-lmpbot.sh && sudo ./setup-lmpbot.sh
# =============================================================================

set -e

# ── Colors for pretty output ─────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log()   { echo -e "${GREEN}[✔]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✘]${NC} $1"; }
info()  { echo -e "${CYAN}[i]${NC} $1"; }

# ── Configurable variables ────────────────────────────────────────────────────
REPO_URL="https://github.com/lamp-studios/lmpbot-beta.git"
REPO_BRANCH="main"
BOT_USER="${SUDO_USER:-$USER}"          # whoever ran sudo
INSTALL_DIR="/home/${BOT_USER}/lmpbot-beta"
SERVICE_NAME="lmpbot"
UPDATE_TIMER_INTERVAL="*:0/5"           # every 5 minutes (systemd calendar fmt)
NODE_MAJOR=22                           # Node.js LTS version to install

# ── Root check ────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    err "Run this script with sudo, bro."
    echo "    sudo ./setup-lmpbot.sh"
    exit 1
fi

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     LMPBot Beta - Raspberry Pi Installer     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — Install system dependencies
# ═════════════════════════════════════════════════════════════════════════════
info "Updating system packages..."
apt-get update -qq

info "Installing prerequisites (git, curl, build tools for native modules)..."
apt-get install -y -qq git curl ca-certificates gnupg build-essential python3 > /dev/null 2>&1
log "System deps installed."

# ── Install Node.js (via NodeSource) if not present or outdated ───────────
NEED_NODE=false
if ! command -v node &> /dev/null; then
    NEED_NODE=true
elif [[ $(node -v | cut -d. -f1 | tr -d 'v') -lt $NODE_MAJOR ]]; then
    warn "Node.js is older than v${NODE_MAJOR}, upgrading..."
    NEED_NODE=true
fi

if $NEED_NODE; then
    info "Installing Node.js v${NODE_MAJOR}.x..."
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg 2>/dev/null
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list
    apt-get update -qq
    apt-get install -y -qq nodejs > /dev/null 2>&1
    log "Node.js $(node -v) installed."
else
    log "Node.js $(node -v) already installed. We're chillin."
fi

# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — Clone the repo
# ═════════════════════════════════════════════════════════════════════════════
if [[ -d "$INSTALL_DIR/.git" ]]; then
    warn "Repo already cloned at ${INSTALL_DIR}. Pulling latest..."
    sudo -u "$BOT_USER" git -C "$INSTALL_DIR" pull --ff-only origin "$REPO_BRANCH"
else
    info "Cloning ${REPO_URL} (branch: ${REPO_BRANCH})..."
    sudo -u "$BOT_USER" git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi
log "Repo ready at ${INSTALL_DIR}."

# ═════════════════════════════════════════════════════════════════════════════
# STEP 3 — npm install + native module rebuild
# ═════════════════════════════════════════════════════════════════════════════
info "Running npm install..."
cd "$INSTALL_DIR"
sudo -u "$BOT_USER" npm install --omit=dev 2>&1 | tail -3

# Rebuild native modules (sqlite3 needs this on RPi/ARM)
info "Rebuilding native modules (sqlite3)..."
sudo -u "$BOT_USER" npm rebuild sqlite3 2>&1 | tail -1 || warn "sqlite3 rebuild had issues — may still work."
log "npm dependencies installed."

# ═════════════════════════════════════════════════════════════════════════════
# STEP 4 — Create database directory
# ═════════════════════════════════════════════════════════════════════════════
DB_DIR="${INSTALL_DIR}/database"
if [[ ! -d "$DB_DIR" ]]; then
    info "Creating database directory..."
    sudo -u "$BOT_USER" mkdir -p "$DB_DIR"
    log "Database directory created at ${DB_DIR}."
else
    log "Database directory already exists."
fi

# ═════════════════════════════════════════════════════════════════════════════
# STEP 5 — Discord bot token / .env setup
# ═════════════════════════════════════════════════════════════════════════════
#
#   The bot uses @dotenvx/dotenvx to load .env automatically.
#   The token variable is: DANGER_DONTSHARETOYKEN
#   (yes, that's the actual variable name — don't question it lol)
#
ENV_FILE="${INSTALL_DIR}/.env"

echo ""
echo -e "${CYAN}─── Discord Bot Token Setup ───${NC}"

if [[ -f "$ENV_FILE" ]]; then
    warn ".env file already exists. Skipping token setup."
    warn "Edit it manually if you need to change the token:"
    warn "    nano ${ENV_FILE}"
else
    echo ""
    echo "  You need your bot token from the Discord Developer Portal:"
    echo "    1. Go to https://discord.com/developers/applications"
    echo "    2. Click your bot application"
    echo "    3. Go to 'Bot' tab on the left"
    echo "    4. Click 'Reset Token' or 'Copy' under the token section"
    echo ""

    read -rp "  Paste your Discord bot token here (or press Enter to skip): " BOT_TOKEN

    if [[ -n "$BOT_TOKEN" ]]; then
        cat > "$ENV_FILE" <<EOF
# LMPBot Beta - Environment Config
# DO NOT commit this file to git!
# The bot reads this via @dotenvx/dotenvx
DANGER_DONTSHARETOYKEN=${BOT_TOKEN}
EOF
        chown "${BOT_USER}:${BOT_USER}" "$ENV_FILE"
        chmod 600 "$ENV_FILE"
        log "Token saved to .env (permissions locked to owner only)."
    else
        warn "No token entered. You MUST create .env before the bot will work:"
        warn "    nano ${ENV_FILE}"
        cat > "$ENV_FILE" <<EOF
# LMPBot Beta - Environment Config
# REPLACE the value below with your actual bot token!
# The bot reads this via @dotenvx/dotenvx
DANGER_DONTSHARETOYKEN=PASTE_YOUR_TOKEN_HERE
EOF
        chown "${BOT_USER}:${BOT_USER}" "$ENV_FILE"
        chmod 600 "$ENV_FILE"
    fi
fi

# Make sure .env is in .gitignore so it never gets committed
if ! grep -qxF '.env' "${INSTALL_DIR}/.gitignore" 2>/dev/null; then
    echo '.env' >> "${INSTALL_DIR}/.gitignore"
    chown "${BOT_USER}:${BOT_USER}" "${INSTALL_DIR}/.gitignore"
    log ".env added to .gitignore (your token stays safe)."
fi

# ═════════════════════════════════════════════════════════════════════════════
# STEP 6 — Create systemd service (auto-start on boot)
# ═════════════════════════════════════════════════════════════════════════════
info "Setting up systemd service: ${SERVICE_NAME}..."

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=LMPBot Beta Discord Bot
Documentation=https://github.com/lamp-studios/lmpbot-beta
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${BOT_USER}
Group=${BOT_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/node index.js
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${INSTALL_DIR}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service" > /dev/null 2>&1
log "systemd service created and enabled on boot."

# ═════════════════════════════════════════════════════════════════════════════
# STEP 7 — Auto-updater script + systemd timer
# ═════════════════════════════════════════════════════════════════════════════
UPDATER_SCRIPT="/usr/local/bin/lmpbot-updater.sh"

info "Creating auto-updater script..."

cat > "$UPDATER_SCRIPT" <<'UPDATER_EOF'
#!/bin/bash
# LMPBot Auto-Updater — checks for new commits, pulls, reinstalls deps, restarts
# Runs via systemd timer. Does NOT touch .env (your token is safe).

set -e

INSTALL_DIR="__INSTALL_DIR__"
SERVICE_NAME="__SERVICE_NAME__"
BOT_USER="__BOT_USER__"
REPO_BRANCH="__REPO_BRANCH__"
LOG_TAG="lmpbot-updater"

log() { logger -t "$LOG_TAG" "$1"; }

cd "$INSTALL_DIR"

# Fetch latest from remote
sudo -u "$BOT_USER" git fetch origin "$REPO_BRANCH" --quiet 2>/dev/null

LOCAL_HASH=$(git rev-parse HEAD)
REMOTE_HASH=$(git rev-parse "origin/${REPO_BRANCH}")

if [[ "$LOCAL_HASH" == "$REMOTE_HASH" ]]; then
    # No updates, we out
    exit 0
fi

log "New commit detected! Updating from ${LOCAL_HASH:0:7} -> ${REMOTE_HASH:0:7}"

# Stash any local changes (just in case)
sudo -u "$BOT_USER" git stash --quiet 2>/dev/null || true

# Pull the latest code
sudo -u "$BOT_USER" git pull --ff-only origin "$REPO_BRANCH" 2>/dev/null

# Ensure database directory exists after pull
sudo -u "$BOT_USER" mkdir -p "${INSTALL_DIR}/database"

# Restore .env if git somehow nuked it (paranoia check)
if [[ ! -f "${INSTALL_DIR}/.env" ]]; then
    log "WARNING: .env went missing after pull — this shouldn't happen!"
fi

# Reinstall deps (in case package.json changed)
cd "$INSTALL_DIR"
sudo -u "$BOT_USER" npm install --omit=dev --quiet 2>/dev/null

# Restart the bot service
systemctl restart "$SERVICE_NAME"
log "Bot updated and restarted successfully."
UPDATER_EOF

# Replace placeholders with actual values
sed -i "s|__INSTALL_DIR__|${INSTALL_DIR}|g" "$UPDATER_SCRIPT"
sed -i "s|__SERVICE_NAME__|${SERVICE_NAME}|g" "$UPDATER_SCRIPT"
sed -i "s|__BOT_USER__|${BOT_USER}|g" "$UPDATER_SCRIPT"
sed -i "s|__REPO_BRANCH__|${REPO_BRANCH}|g" "$UPDATER_SCRIPT"

chmod +x "$UPDATER_SCRIPT"
log "Updater script created at ${UPDATER_SCRIPT}."

# ── systemd timer for auto-updates ───────────────────────────────────────────
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
log "Auto-updater timer enabled (checks every 5 min)."

# ═════════════════════════════════════════════════════════════════════════════
# STEP 8 — Start the bot (if token is configured)
# ═════════════════════════════════════════════════════════════════════════════
echo ""
if grep -q "PASTE_YOUR_TOKEN_HERE" "$ENV_FILE" 2>/dev/null; then
    warn "Bot token not set yet — skipping auto-start."
    warn "Once you set the token, start with:"
    warn "    sudo systemctl start ${SERVICE_NAME}"
else
    info "Starting the bot..."
    systemctl start "${SERVICE_NAME}" || true
    sleep 2
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log "Bot is running! Let's gooo"
    else
        err "Bot failed to start. Check logs with:"
        echo "    journalctl -u ${SERVICE_NAME} -f"
    fi
fi

# ═════════════════════════════════════════════════════════════════════════════
# Done — print summary
# ═════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              Setup Complete!                  ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  Useful commands:"
echo "  ─────────────────────────────────────────────"
echo "  Start bot:       sudo systemctl start ${SERVICE_NAME}"
echo "  Stop bot:        sudo systemctl stop ${SERVICE_NAME}"
echo "  Restart bot:     sudo systemctl restart ${SERVICE_NAME}"
echo "  Bot status:      sudo systemctl status ${SERVICE_NAME}"
echo "  Live logs:       journalctl -u ${SERVICE_NAME} -f"
echo "  Updater logs:    journalctl -u ${SERVICE_NAME}-updater -f"
echo "  Edit token:      nano ${ENV_FILE}"
echo "  Force update:    sudo ${UPDATER_SCRIPT}"
echo ""
echo "  Install dir:     ${INSTALL_DIR}"
echo "  .env file:       ${ENV_FILE}"
echo "  Database dir:    ${INSTALL_DIR}/database"
echo ""
