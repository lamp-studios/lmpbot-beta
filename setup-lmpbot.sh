#!/bin/bash
# =============================================================================
#  LMPBot Beta - Raspberry Pi Setup Script
#  Installs Python deps into a venv, configures systemd, sets up auto-updates.
#  Safe to re-run: it also migrates an existing Node.js install to Python.
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
REPO_BRANCH="master"
BOT_USER="${SUDO_USER:-$USER}"
BOT_HOME="$(getent passwd "$BOT_USER" | cut -d: -f6)"
INSTALL_DIR="${BOT_HOME}/lmpbot-beta"
VENV_DIR="${INSTALL_DIR}/.venv"
SERVICE_NAME="lmpbot"
UPDATE_TIMER_INTERVAL="*:0/5"
# py-cord 2.8 needs Python 3.10+; older systems get a uv-managed Python instead
PY_MIN_MINOR=10
UV_PYTHON="3.12"
# last commit the updater successfully deployed, so a failed update is retried
STATE_DIR="/var/lib/${SERVICE_NAME:-lmpbot}"

# run as the bot user with its own HOME (plain `sudo -u` can keep root's on Debian)
as_bot() { sudo -H -u "$BOT_USER" "$@"; }

if [[ $EUID -ne 0 ]]; then
    err "Run this script with sudo."
    exit 1
fi

echo ""
echo -e "${CYAN}  LMPBot Beta - Raspberry Pi Installer${NC}"
echo ""

if [[ "$(uname -m)" == "armv7l" || "$(uname -m)" == "armv6l" ]]; then
    warn "32-bit OS detected. Some dependencies (pydantic-core) may have to compile"
    warn "from source, which is slow. A 64-bit Raspberry Pi OS is recommended."
fi

# -- stop a running bot / updater while files change ---------------------------

# The bot is stopped from here on, so a failure part-way through must say so
# rather than leaving it silently offline.
trap 'err "Setup failed on line ${LINENO}. The bot is stopped. Fix the error above and re-run this script; .env and database/ are untouched."' ERR

systemctl stop "${SERVICE_NAME}-updater.timer" > /dev/null 2>&1 || true
systemctl stop "${SERVICE_NAME}.service" > /dev/null 2>&1 || true

# -- system deps --------------------------------------------------------------

info "Updating packages..."
apt-get update -qq

info "Installing prerequisites..."
apt-get install -y -qq git curl ca-certificates python3 python3-venv python3-pip > /dev/null 2>&1
log "System deps installed."

# -- python -------------------------------------------------------------------

PYTHON_BIN=""
if command -v python3 > /dev/null 2>&1 && \
   python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, ${PY_MIN_MINOR}) else 1)"; then
    PYTHON_BIN="$(command -v python3)"
    log "Using system $(python3 --version)."
else
    warn "System Python is older than 3.${PY_MIN_MINOR}; installing Python ${UV_PYTHON} with uv..."
    if [[ ! -x "${BOT_HOME}/.local/bin/uv" ]]; then
        as_bot sh -c "curl -LsSf https://astral.sh/uv/install.sh | sh" > /dev/null 2>&1
    fi
    as_bot "${BOT_HOME}/.local/bin/uv" python install "$UV_PYTHON" > /dev/null 2>&1
    PYTHON_BIN="$(as_bot "${BOT_HOME}/.local/bin/uv" python find "$UV_PYTHON")"
    log "Using $("$PYTHON_BIN" --version) from uv."
fi

# -- clone repo ---------------------------------------------------------------

if [[ -d "$INSTALL_DIR/.git" ]]; then
    warn "Repo already exists. Forcing working tree to origin/${REPO_BRANCH}..."
    as_bot git -C "$INSTALL_DIR" fetch origin "$REPO_BRANCH"
    # Move onto the target branch and make the tree EXACTLY match the remote,
    # discarding any local edits. This also deletes every tracked Node.js file
    # (index.js, commands/*.js, package.json, ...) from the old install.
    as_bot git -C "$INSTALL_DIR" checkout -f -B "$REPO_BRANCH" "origin/${REPO_BRANCH}"
    # Remove untracked leftovers while keeping gitignored runtime files like
    # .env, database/ and .venv/.
    as_bot git -C "$INSTALL_DIR" clean -fd
else
    info "Cloning repo..."
    as_bot git clone -b "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi
log "Repo ready at ${INSTALL_DIR}."

# node_modules is gitignored, so `git clean` leaves it behind after the switch
if [[ -d "${INSTALL_DIR}/node_modules" ]]; then
    rm -rf "${INSTALL_DIR}/node_modules"
    log "Removed old node_modules/."
fi

# -- python deps --------------------------------------------------------------

# a venv built by another Python (e.g. before a uv switch) is rebuilt from scratch
if [[ -x "${VENV_DIR}/bin/python" ]] && \
   [[ "$("${VENV_DIR}/bin/python" -c 'import sys; print(sys.version_info[:2])')" != \
      "$("$PYTHON_BIN" -c 'import sys; print(sys.version_info[:2])')" ]]; then
    warn "Existing venv uses a different Python; recreating it."
    rm -rf "$VENV_DIR"
fi

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    info "Creating virtualenv..."
    as_bot "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

info "Installing Python dependencies (this can take a few minutes on a Pi)..."
as_bot "${VENV_DIR}/bin/python" -m pip install --quiet --upgrade pip
as_bot "${VENV_DIR}/bin/python" -m pip install --quiet -r "${INSTALL_DIR}/requirements.txt"
log "Python dependencies installed."

# -- .env setup ---------------------------------------------------------------

ENV_FILE="${INSTALL_DIR}/.env"

echo ""
echo -e "${CYAN}--- Discord Bot Token Setup ---${NC}"

if [[ -f "$ENV_FILE" ]]; then
    warn ".env already exists. Filling in any missing keys: nano ${ENV_FILE}"
    # a file without a trailing newline would glue the first new key onto its last line
    if [[ -s "$ENV_FILE" && -n "$(tail -c1 "$ENV_FILE")" ]]; then
        echo "" >> "$ENV_FILE"
    fi
    # add any expected keys that aren't already present, leaving existing values
    # untouched (blank values count as unset, so blank storage keys just disable that tier)
    for KEY in DANGER_DONTSHARETOYKEN GEMINI_API_KEY OPENAI_API_KEY OPENAI_BASE_URL OLLAMA_HOST MONGODB_URI SUPABASE_URL SUPABASE_KEY DATABASE_URL DATABASE_URL_UNPOOLED TURSO_DATABASE_URL TURSO_AUTH_TOKEN KUMA_PUSH_URL PUSHGATEWAY_URL BOT_API_KEY BOT_API_PORT; do
        if ! grep -q "^${KEY}=" "$ENV_FILE"; then
            if [[ "$KEY" == "DANGER_DONTSHARETOYKEN" ]]; then
                echo "${KEY}=PASTE_YOUR_TOKEN_HERE" >> "$ENV_FILE"
            else
                echo "${KEY}=" >> "$ENV_FILE"
            fi
            log "Added missing ${KEY}= line to .env."
        fi
    done
else
    read -rp "  Paste your Discord bot token (or Enter to skip): " BOT_TOKEN

    cat > "$ENV_FILE" <<EOF
DANGER_DONTSHARETOYKEN=${BOT_TOKEN:-PASTE_YOUR_TOKEN_HERE}
GEMINI_API_KEY=
OPENAI_API_KEY=
OPENAI_BASE_URL=
OLLAMA_HOST=
MONGODB_URI=
SUPABASE_URL=
SUPABASE_KEY=
DATABASE_URL=
DATABASE_URL_UNPOOLED=
TURSO_DATABASE_URL=
TURSO_AUTH_TOKEN=
KUMA_PUSH_URL=
PUSHGATEWAY_URL=
BOT_API_KEY=
BOT_API_PORT=
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
ExecStart=${VENV_DIR}/bin/python ${INSTALL_DIR}/main.py
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
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
# Deploys origin/<branch> whenever it differs from the last successful deploy.
# Errors go to the journal: journalctl -u lmpbot-updater
set -e
INSTALL_DIR="__INSTALL_DIR__"
VENV_DIR="__VENV_DIR__"
SERVICE_NAME="__SERVICE_NAME__"
BOT_USER="__BOT_USER__"
REPO_BRANCH="__REPO_BRANCH__"
STATE_DIR="__STATE_DIR__"

# git refuses repos owned by another user ("dubious ownership"), so every git
# call runs as the bot user rather than as root
as_bot() { sudo -H -u "$BOT_USER" "$@"; }

cd "$INSTALL_DIR"
as_bot git fetch origin "$REPO_BRANCH" --quiet

REMOTE=$(as_bot git rev-parse "origin/${REPO_BRANCH}")
DEPLOYED=$(cat "${STATE_DIR}/deployed-commit" 2>/dev/null || true)
# compared against the last *successful* deploy, not HEAD, so a pull whose
# install or restart failed is retried on the next run instead of forgotten
[[ "$REMOTE" == "$DEPLOYED" ]] && exit 0

logger -t lmpbot-updater "Updating ${DEPLOYED:0:7} -> ${REMOTE:0:7}"

if ! as_bot git merge --ff-only --quiet "origin/${REPO_BRANCH}"; then
    logger -t lmpbot-updater "Fast-forward failed (local changes or a force-push). Re-run setup-lmpbot.sh."
    exit 1
fi
if ! as_bot "${VENV_DIR}/bin/python" -m pip install --quiet -r "${INSTALL_DIR}/requirements.txt"; then
    logger -t lmpbot-updater "pip install failed; the bot keeps running the old code. Retrying next run."
    exit 1
fi

systemctl restart "$SERVICE_NAME"
mkdir -p "$STATE_DIR"
echo "$REMOTE" > "${STATE_DIR}/deployed-commit"
logger -t lmpbot-updater "Deployed ${REMOTE:0:7}"
UPDATER_EOF

sed -i "s|__INSTALL_DIR__|${INSTALL_DIR}|g" "$UPDATER_SCRIPT"
sed -i "s|__VENV_DIR__|${VENV_DIR}|g" "$UPDATER_SCRIPT"
sed -i "s|__SERVICE_NAME__|${SERVICE_NAME}|g" "$UPDATER_SCRIPT"
sed -i "s|__BOT_USER__|${BOT_USER}|g" "$UPDATER_SCRIPT"
sed -i "s|__REPO_BRANCH__|${REPO_BRANCH}|g" "$UPDATER_SCRIPT"
sed -i "s|__STATE_DIR__|${STATE_DIR}|g" "$UPDATER_SCRIPT"
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

mkdir -p "$STATE_DIR"
as_bot git -C "$INSTALL_DIR" rev-parse HEAD > "${STATE_DIR}/deployed-commit"

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
    sleep 3
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
