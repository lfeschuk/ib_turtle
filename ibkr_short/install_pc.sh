#!/usr/bin/env bash
# ==============================================================================
# Dual-Strategy IBKR Bot (Gap Short + 0DTE SPX Put BWB) — All-in-One PC Installer
# ==============================================================================
# Usage on your Ubuntu PC:
#   bash install_pc.sh
#
# Optional flags:
#   --yes / -y              Accept defaults without interactive prompts
#   --port <4002|7497|...>  Set IB Gateway / TWS socket port (default: 4002 for IB Gateway Paper)
#   --shared-100k           Configure Shared 1x$100k mode (yearly_house + 95% margin guard)
#                           (default is Independent 2x$100k Paper Ledgers)
#   --skip-sudo             Skip sudo steps (apt, timedatectl, sleep mask, linger)
# ==============================================================================

set -u

# Colors & badges
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC}   $*"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $*"; WARNINGS+=("$*"); }
fail() { echo -e "  ${RED}[FAIL]${NC} $*"; ISSUES+=("$*"); }
info() { echo -e "  ${BLUE}[..]${NC}   $*"; }
step() { echo -e "\n${BOLD}=== $* ===${NC}"; }

ISSUES=()
WARNINGS=()
NEXT_STEPS=()

# Defaults
ASSUME_YES=0
SKIP_SUDO=0
BROKER_PORT=""
CAPITAL_MODE="independent"   # "independent" (2x$100k) or "shared" (1x$100k yearly_house)
TARGET_DIR="${HOME}/gapshort"
CONFIG_DIR="${HOME}/.config/gapshort"
CONFIG_FILE="${CONFIG_DIR}/config.toml"
SECRETS_FILE="${CONFIG_DIR}/secrets.json"
DATA_DIR="${HOME}/.local/share/gapshort"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes|--non-interactive)
      ASSUME_YES=1
      shift
      ;;
    --port)
      BROKER_PORT="${2:-4002}"
      shift 2
      ;;
    --shared-100k)
      CAPITAL_MODE="shared"
      shift
      ;;
    --independent-200k)
      CAPITAL_MODE="independent"
      shift
      ;;
    --skip-sudo)
      SKIP_SUDO=1
      shift
      ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      warn "Unknown flag ignored: $1"
      shift
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BOLD}==============================================================================${NC}"
echo -e "${BOLD} Dual-Strategy IBKR Bot Installer (Small-Cap Gap Short + 0DTE SPX Put BWB)${NC}"
echo -e "${BOLD} Target Directory : ${TARGET_DIR}${NC}"
echo -e "${BOLD} Config File      : ${CONFIG_FILE}${NC}"
echo -e "${BOLD}==============================================================================${NC}"

# ------------------------------------------------------------------------------
# Helper: probe whether a localhost TCP port is open
# ------------------------------------------------------------------------------
port_is_open() {
  local p="$1"
  python3 - "$p" <<'PY' >/dev/null 2>&1
import socket, sys
port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.5)
try:
    s.connect(("127.0.0.1", port))
    sys.exit(0)
except Exception:
    sys.exit(1)
finally:
    s.close()
PY
}

# ------------------------------------------------------------------------------
# STEP 1: System Prerequisites, Clock Sync & Sleep Prevention
# ------------------------------------------------------------------------------
step "Step 1/7: Checking Ubuntu System Prerequisites & Clock Sync"

if command -v python3 >/dev/null 2>&1; then
  PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')"
  ok "Python 3 found (v${PY_VER})"
else
  fail "python3 is not installed."
fi

# Check python3-venv and curl
NEED_APT=0
if ! python3 -m venv --help >/dev/null 2>&1; then
  NEED_APT=1
fi
if ! command -v curl >/dev/null 2>&1; then
  NEED_APT=1
fi

if [[ "$NEED_APT" -eq 1 ]]; then
  if [[ "$SKIP_SUDO" -eq 0 ]] && command -v apt-get >/dev/null 2>&1; then
    info "Installing python3-venv, python3-pip, and curl via apt..."
    if sudo apt-get update && sudo apt-get install -y python3-venv python3-pip curl; then
      ok "Installed python3-venv, python3-pip, and curl"
    else
      fail "Could not install python3-venv via apt. Run: sudo apt update && sudo apt install -y python3-venv python3-pip curl"
    fi
  else
    fail "Missing python3-venv or curl. Run: sudo apt update && sudo apt install -y python3-venv python3-pip curl"
  fi
else
  ok "python3-venv and curl are installed"
fi

# Check NTP clock sync
if command -v timedatectl >/dev/null 2>&1; then
  NTP_SYNC="$(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo "unknown")"
  if [[ "$NTP_SYNC" == "yes" ]]; then
    ok "System clock is NTP-synchronized"
  else
    if [[ "$SKIP_SUDO" -eq 0 ]]; then
      info "Enabling NTP clock synchronization..."
      sudo timedatectl set-ntp true >/dev/null 2>&1 || true
    fi
    NTP_SYNC="$(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo "unknown")"
    if [[ "$NTP_SYNC" == "yes" ]]; then
      ok "System clock is now NTP-synchronized"
    else
      warn "Clock NTP sync reported '${NTP_SYNC}'. Verify with: sudo timedatectl set-ntp true"
    fi
  fi
fi

# Optional sleep/lid-close masking on Ubuntu PC
if [[ "$SKIP_SUDO" -eq 0 ]] && command -v systemctl >/dev/null 2>&1; then
  DO_SLEEP_MASK="y"
  if [[ "$ASSUME_YES" -eq 0 ]]; then
    read -r -p "  Prevent Ubuntu PC from sleeping/suspending during market hours? [Y/n]: " ans
    DO_SLEEP_MASK="${ans:-y}"
  fi
  if [[ "${DO_SLEEP_MASK,,}" =~ ^y ]]; then
    sudo mkdir -p /etc/systemd/logind.conf.d 2>/dev/null || true
    printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n' \
      | sudo tee /etc/systemd/logind.conf.d/gapshort.conf >/dev/null 2>&1 || true
    sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null 2>&1 || true
    ok "Ubuntu sleep/suspend targets masked (PC will stay awake 24/7)"
  else
    info "Skipped Ubuntu sleep masking"
  fi
fi

# ------------------------------------------------------------------------------
# STEP 2: Install / Extract Bot Files into ~/gapshort
# ------------------------------------------------------------------------------
step "Step 2/7: Installing Bot Code into ${TARGET_DIR}"

mkdir -p "${TARGET_DIR}"

# Locate source: either we are inside the repo/extracted folder, or next to gapshort-live-*.tar.gz
TARBALL=""
for candidate in \
  "${SCRIPT_DIR}"/dist/gapshort-live-*.tar.gz \
  "${SCRIPT_DIR}"/gapshort-live-*.tar.gz \
  "${HOME}"/Downloads/gapshort-live-*.tar.gz; do
  if [[ -f "$candidate" ]]; then
    TARBALL="$candidate"
  fi
done

if [[ -f "${SCRIPT_DIR}/trading_system/live/main.py" ]]; then
  if [[ "${SCRIPT_DIR}" == "${TARGET_DIR}" ]]; then
    ok "Already running directly inside ${TARGET_DIR}"
  else
    info "Copying bot files from ${SCRIPT_DIR} to ${TARGET_DIR}..."
    cp -a "${SCRIPT_DIR}/trading_system" "${TARGET_DIR}/"
    cp -a "${SCRIPT_DIR}/deploy" "${TARGET_DIR}/"
    [[ -f "${SCRIPT_DIR}/README.md" ]] && cp -a "${SCRIPT_DIR}/README.md" "${TARGET_DIR}/"
    [[ -f "${SCRIPT_DIR}/install_pc.sh" ]] && cp -a "${SCRIPT_DIR}/install_pc.sh" "${TARGET_DIR}/"
    ok "Copied bot files to ${TARGET_DIR}"
  fi
elif [[ -f "${SCRIPT_DIR}/../trading_system/live/main.py" ]]; then
  SRC_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
  if [[ "${SRC_ROOT}" == "${TARGET_DIR}" ]]; then
    ok "Already running inside ${TARGET_DIR}"
  else
    info "Copying bot files from ${SRC_ROOT} to ${TARGET_DIR}..."
    cp -a "${SRC_ROOT}/trading_system" "${TARGET_DIR}/"
    cp -a "${SRC_ROOT}/deploy" "${TARGET_DIR}/"
    [[ -f "${SRC_ROOT}/README.md" ]] && cp -a "${SRC_ROOT}/README.md" "${TARGET_DIR}/"
    ok "Copied bot files to ${TARGET_DIR}"
  fi
elif [[ -n "${TARBALL}" ]]; then
  info "Found archive: ${TARBALL}"
  if [[ -f "${TARBALL}.sha256" ]]; then
    if (cd "$(dirname "${TARBALL}")" && sha256sum -c "$(basename "${TARBALL}.sha256")" >/dev/null 2>&1); then
      ok "SHA-256 checksum verified for $(basename "${TARBALL}")"
    else
      fail "SHA-256 checksum mismatch for ${TARBALL}"
    fi
  fi
  tar -xzf "${TARBALL}" -C "${TARGET_DIR}"
  ok "Extracted $(basename "${TARBALL}") into ${TARGET_DIR}"
else
  fail "Could not find trading_system/ or gapshort-live-*.tar.gz in ${SCRIPT_DIR} or ~/Downloads."
fi

if [[ -f "${TARGET_DIR}/trading_system/live/main.py" ]] && [[ -f "${TARGET_DIR}/trading_system/live/bwb_service.py" ]]; then
  ok "Verified both bots present in ${TARGET_DIR} (Gap Short + 0DTE SPX Put BWB)"
else
  fail "Bot source files missing in ${TARGET_DIR}/trading_system/live/"
fi

# ------------------------------------------------------------------------------
# STEP 3: Python Virtual Environment & Package Installation
# ------------------------------------------------------------------------------
step "Step 3/7: Setting Up Python Virtual Environment (${TARGET_DIR}/.venv)"

if [[ ! -x "${TARGET_DIR}/.venv/bin/python" ]]; then
  info "Creating virtualenv at ${TARGET_DIR}/.venv ..."
  if python3 -m venv "${TARGET_DIR}/.venv"; then
    ok "Created virtualenv ${TARGET_DIR}/.venv"
  else
    fail "Failed to create virtualenv at ${TARGET_DIR}/.venv"
  fi
else
  ok "Virtualenv ${TARGET_DIR}/.venv already exists"
fi

if [[ -x "${TARGET_DIR}/.venv/bin/pip" ]]; then
  info "Installing Python dependencies from deploy/requirements-live.txt ..."
  if "${TARGET_DIR}/.venv/bin/pip" install -q --upgrade pip >/dev/null 2>&1 && \
     "${TARGET_DIR}/.venv/bin/pip" install -q -r "${TARGET_DIR}/deploy/requirements-live.txt"; then
    ok "Installed all Python dependencies (numpy, pandas, ib_async, fastapi, uvicorn)"
  elif "${TARGET_DIR}/.venv/bin/python" -c "import numpy, pandas, ib_async, fastapi, uvicorn" >/dev/null 2>&1; then
    ok "All Python dependencies already installed in ${TARGET_DIR}/.venv"
  else
    fail "pip install failed — check internet connection on the PC"
  fi
fi

# Verify imports and strategy math
SELF_TEST_ERR="$(cd "${TARGET_DIR}" && "${TARGET_DIR}/.venv/bin/python" -c "
import numpy, pandas, ib_async, fastapi, uvicorn
from trading_system.live.config import LiveConfig
from trading_system.live.bwb_strategy import compute_earned_kelly_fraction, summarize_bwb_premium_audit
import trading_system.live.main
import trading_system.live.bwb_service
import trading_system.live.web_server
assert abs(compute_earned_kelly_fraction(100000, 100000, 100000, LiveConfig().bwb) - 0.075) < 1e-6
assert summarize_bwb_premium_audit([], 0.20, 0.20, 'paper')['verdict'] == 'early'
" 2>&1)"
if [[ $? -eq 0 ]]; then
  ok "Self-test passed: all modules import cleanly and Kelly sizing math verified"
else
  fail "Python module self-test failed inside ${TARGET_DIR}/.venv: ${SELF_TEST_ERR}"
fi

# ------------------------------------------------------------------------------
# STEP 4: Detect IB Gateway / TWS Port & Create ~/.config/gapshort/config.toml
# ------------------------------------------------------------------------------
step "Step 4/7: Configuring IB Gateway / TWS Port & Capital Mode"

mkdir -p "${CONFIG_DIR}" "${DATA_DIR}"
chmod 700 "${CONFIG_DIR}" "${DATA_DIR}" 2>/dev/null || true

DETECTED_PORT=""
if port_is_open 4002; then
  DETECTED_PORT="4002"
  ok "Detected IB Gateway Paper Trading actively listening on port 4002!"
elif port_is_open 7497; then
  DETECTED_PORT="7497"
  ok "Detected TWS Paper Trading actively listening on port 7497!"
elif port_is_open 4001; then
  DETECTED_PORT="4001"
  ok "Detected IB Gateway Live Trading listening on port 4001!"
elif port_is_open 7496; then
  DETECTED_PORT="7496"
  ok "Detected TWS Live Trading listening on port 7496!"
else
  info "No IB Gateway/TWS port is listening right now (defaulting to IB Gateway Paper port 4002)"
fi

if [[ -z "${BROKER_PORT}" ]]; then
  DEFAULT_PORT="${DETECTED_PORT:-4002}"
  if [[ "$ASSUME_YES" -eq 0 ]]; then
    echo ""
    echo "  Which broker port should the bot connect to?"
    echo "    4002 = IB Gateway Paper Trading (Recommended default)"
    echo "    4001 = IB Gateway Live Trading"
    echo "    7497 = TWS Paper Trading"
    echo "    7496 = TWS Live Trading"
    read -r -p "  Enter port [${DEFAULT_PORT}]: " input_port
    BROKER_PORT="${input_port:-$DEFAULT_PORT}"
  else
    BROKER_PORT="${DEFAULT_PORT}"
  fi
fi

if [[ "$ASSUME_YES" -eq 0 ]]; then
  echo ""
  echo "  How should capital be allocated between the 2 strategies?"
  echo "    1) Two Independent \$100,000 Paper Ledgers (\$200k total — monitor each strategy separately) [Default]"
  echo "    2) Shared \$100,000 Account (return-stacked on same \$100k with Jan-1 principal lock + 95% margin guard)"
  read -r -p "  Select 1 or 2 [1]: " cap_choice
  if [[ "${cap_choice:-1}" == "2" ]]; then
    CAPITAL_MODE="shared"
  else
    CAPITAL_MODE="independent"
  fi
fi

WRITE_CFG="y"
if [[ -f "${CONFIG_FILE}" ]] && [[ "$ASSUME_YES" -eq 0 ]]; then
  read -r -p "  Config ${CONFIG_FILE} already exists. Update it with these settings? (backup saved) [Y/n]: " ow_ans
  WRITE_CFG="${ow_ans:-y}"
fi

if [[ "${WRITE_CFG,,}" =~ ^y ]]; then
  [[ -f "${CONFIG_FILE}" ]] && cp "${CONFIG_FILE}" "${CONFIG_FILE}.bak"
  if [[ "${CAPITAL_MODE}" == "shared" ]]; then
    cat > "${CONFIG_FILE}" <<EOF
# Auto-generated by install_pc.sh — Shared \$100,000 Capital Mode (Yearly Jan-1 Lock + 95% Margin Guard)
mode = "paper"
tws_host = "127.0.0.1"
tws_port = ${BROKER_PORT}
client_id = 17
allow_live = false

initial_capital = 100000.0
isolated_capital = false

http_host = "127.0.0.1"
http_port = 8787
data_dir = "~/.local/share/gapshort"
secrets_path = "~/.config/gapshort/secrets.json"

decision_minutes_before_close = 15
reconcile_minutes_after_close = 15
max_positions = 6
hold_days = 3
cooldown_days = 10
slip_per_side = 0.005

[sizing]
mode = "perbet_house"
static_pct = 0.035
kelly_mult = 0.1667
profit_kelly_mult = 0.3333
min_pct = 0.01
max_pct = 0.06
max_gross = 0.60
model_path = "~/gapshort/trading_system/live/model_perbet.json"

[bwb]
enabled = true
initial_capital = 100000.0
isolated_capital = false
delta_mid = 0.15
w1_sd = 0.28
w_risk_sd = 1.30
sizing_mode = "yearly_house"
base_collat_pct = 0.075
floor_collat_pct = 0.050
max_collat_pct = 0.200
profit_share = 0.50
max_combined_margin_pct = 0.95
symbol = "SPX"
entry_minutes_after_open = 60
min_net_credit_pct = 0.0
entry_timeout_sec = 90
client_id_offset = 1
EOF
    ok "Wrote ${CONFIG_FILE} (Port=${BROKER_PORT}, Mode=Shared \$100k + yearly_house + 95% margin guard)"
  else
    cat > "${CONFIG_FILE}" <<EOF
# Auto-generated by install_pc.sh — Two Independent \$100,000 Paper Ledgers (\$200k Combined)
mode = "paper"
tws_host = "127.0.0.1"
tws_port = ${BROKER_PORT}
client_id = 17
allow_live = false

initial_capital = 100000.0
isolated_capital = true

http_host = "127.0.0.1"
http_port = 8787
data_dir = "~/.local/share/gapshort"
secrets_path = "~/.config/gapshort/secrets.json"

decision_minutes_before_close = 15
reconcile_minutes_after_close = 15
max_positions = 6
hold_days = 3
cooldown_days = 10
slip_per_side = 0.005

[sizing]
mode = "static"
static_pct = 0.035
kelly_mult = 0.1667
profit_kelly_mult = 0.3333
min_pct = 0.01
max_pct = 0.06
max_gross = 0.60
model_path = "~/gapshort/trading_system/live/model_perbet.json"

[bwb]
enabled = true
initial_capital = 100000.0
isolated_capital = true
delta_mid = 0.20
w1_sd = 0.32
w_risk_sd = 1.30
sizing_mode = "earned_ramp"
base_collat_pct = 0.075
floor_collat_pct = 0.050
max_collat_pct = 0.200
profit_share = 0.50
max_combined_margin_pct = 0.95
symbol = "SPX"
entry_minutes_after_open = 60
min_net_credit_pct = 0.0
entry_timeout_sec = 90
client_id_offset = 1
EOF
    ok "Wrote ${CONFIG_FILE} (Port=${BROKER_PORT}, Mode=Two Independent \$100k Paper Ledgers)"
  fi
else
  ok "Kept existing ${CONFIG_FILE}"
fi

# ------------------------------------------------------------------------------
# STEP 5: Web App Password (~/.config/gapshort/secrets.json)
# ------------------------------------------------------------------------------
step "Step 5/7: Checking Web Dashboard Password (${SECRETS_FILE})"

if [[ -f "${SECRETS_FILE}" ]]; then
  ok "Web password already configured in ${SECRETS_FILE}"
  if [[ "$ASSUME_YES" -eq 0 ]]; then
    read -r -p "  Keep existing web password? [Y/n]: " keep_pw
    if [[ "${keep_pw,,}" =~ ^n ]]; then
      (cd "${TARGET_DIR}" && "${TARGET_DIR}/.venv/bin/python" -m trading_system.live.main set-password --config "${CONFIG_FILE}")
    fi
  fi
else
  if [[ "$ASSUME_YES" -eq 0 ]]; then
    echo "  Please set a password (at least 12 characters) for the web/phone app:"
    if (cd "${TARGET_DIR}" && "${TARGET_DIR}/.venv/bin/python" -m trading_system.live.main set-password --config "${CONFIG_FILE}"); then
      ok "Web password saved to ${SECRETS_FILE}"
    else
      warn "Password was not set yet."
      NEXT_STEPS+=("Set your web dashboard password (12+ chars): ~/gapshort/.venv/bin/python -m trading_system.live.main set-password --config ~/.config/gapshort/config.toml")
    fi
  else
    warn "No password file at ${SECRETS_FILE} (ran with --yes)."
    NEXT_STEPS+=("Set your web dashboard password (12+ chars): ~/gapshort/.venv/bin/python -m trading_system.live.main set-password --config ~/.config/gapshort/config.toml && systemctl --user restart gapshort")
  fi
fi

# ------------------------------------------------------------------------------
# STEP 6: Install & Start systemd Background Service (gapshort.service)
# ------------------------------------------------------------------------------
step "Step 6/7: Installing & Starting systemd Background Service"

if command -v systemctl >/dev/null 2>&1 && systemctl --user status >/dev/null 2>&1; then
  mkdir -p "${HOME}/.config/systemd/user"
  cp "${TARGET_DIR}/deploy/gapshort.service" "${HOME}/.config/systemd/user/gapshort.service"
  systemctl --user daemon-reload
  systemctl --user enable gapshort >/dev/null 2>&1 || true

  if [[ -f "${SECRETS_FILE}" ]]; then
    systemctl --user restart gapshort
    sleep 2
    if systemctl --user is-active --quiet gapshort; then
      ok "systemd service 'gapshort' is ACTIVE and running in the background"
    else
      warn "systemd service 'gapshort' did not stay active. Check: journalctl --user -u gapshort -n 50 --no-pager"
    fi
  else
    info "systemd service 'gapshort' installed & enabled (will start as soon as password is set)"
  fi

  if [[ "$SKIP_SUDO" -eq 0 ]] && command -v loginctl >/dev/null 2>&1; then
    sudo loginctl enable-linger "$USER" >/dev/null 2>&1 && \
      ok "Enabled systemd user linger (bot keeps running when logged out)"
  fi
else
  warn "systemd user session not available in this shell; you can run the bot with: ~/gapshort/.venv/bin/python -m trading_system.live.main run --config ~/.config/gapshort/config.toml"
fi

# Check if web dashboard is responding on 127.0.0.1:8787
if port_is_open 8787; then
  ok "Local Web App is live at: http://localhost:8787"
else
  if [[ -f "${SECRETS_FILE}" ]]; then
    warn "Web App port 8787 is not responding yet. Check logs: journalctl --user -u gapshort -n 30 --no-pager"
  fi
fi

# ------------------------------------------------------------------------------
# STEP 7: Live IB Gateway / TWS Check & Tailscale Check
# ------------------------------------------------------------------------------
step "Step 7/7: Testing IB Gateway (Port ${BROKER_PORT}) & Tailscale Phone Access"

if port_is_open "${BROKER_PORT}"; then
  info "Port ${BROKER_PORT} is open! Running live IB Gateway API diagnostic ('check')..."
  CHECK_OUT="$(cd "${TARGET_DIR}" && "${TARGET_DIR}/.venv/bin/python" -m trading_system.live.main check --config "${CONFIG_FILE}" 2>&1)"
  CHECK_RC=$?
  echo "${CHECK_OUT}" | sed 's/^/    /'
  if [[ "$CHECK_RC" -eq 0 ]]; then
    ok "IB Gateway API check passed for both strategies (clientId 17 & 18)!"
  else
    warn "IB Gateway port ${BROKER_PORT} is open, but 'check' reported an issue above."
    NEXT_STEPS+=("Review the IB Gateway check output above and re-run: ~/gapshort/.venv/bin/python -m trading_system.live.main check --config ~/.config/gapshort/config.toml")
  fi
else
  warn "IB Gateway is not listening on 127.0.0.1:${BROKER_PORT} right now."
  NEXT_STEPS+=("Open IB Gateway -> Log into Paper Trading -> Configure -> Settings -> API -> Settings -> Verify 'Socket port' is ${BROKER_PORT}, 'Read-Only API' is UNCHECKED, and under API -> Precautions check all 'Bypass' boxes.")
  NEXT_STEPS+=("Once IB Gateway is open and logged in, verify connection with: ~/gapshort/.venv/bin/python -m trading_system.live.main check --config ~/.config/gapshort/config.toml")
fi

# Check Tailscale
if command -v tailscale >/dev/null 2>&1; then
  if tailscale status >/dev/null 2>&1; then
    ok "Tailscale is installed and connected"
    if [[ "$SKIP_SUDO" -eq 0 ]]; then
      DO_TS="y"
      if [[ "$ASSUME_YES" -eq 0 ]]; then
        read -r -p "  Publish web app privately to your phone via 'sudo tailscale serve --bg 8787'? [Y/n]: " ts_ans
        DO_TS="${ts_ans:-y}"
      fi
      if [[ "${DO_TS,,}" =~ ^y ]]; then
        if sudo tailscale serve --bg 8787 >/dev/null 2>&1; then
          ok "Published port 8787 over Tailscale HTTPS:"
          tailscale serve status 2>/dev/null | sed 's/^/    /'
        else
          warn "Could not enable tailscale serve automatically. Run: sudo tailscale serve --bg 8787"
          NEXT_STEPS+=("Expose the web app to your phone over Tailscale HTTPS: sudo tailscale serve --bg 8787")
        fi
      fi
    fi
  else
    warn "Tailscale is installed but not logged in."
    NEXT_STEPS+=("(Optional for phone app) Log in to Tailscale: sudo tailscale up && sudo tailscale serve --bg 8787")
  fi
else
  info "Tailscale is not installed yet (only needed if you want to open the dashboard on your phone)."
  NEXT_STEPS+=("(Optional for phone app) Install Tailscale: curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up && sudo tailscale serve --bg 8787")
fi

# ------------------------------------------------------------------------------
# FINAL DIAGNOSTIC SUMMARY & NEXT STEPS
# ------------------------------------------------------------------------------
echo ""
echo -e "${BOLD}==============================================================================${NC}"
if [[ "${#ISSUES[@]}" -eq 0 ]]; then
  echo -e "${GREEN}${BOLD} INSTALLATION COMPLETE — 0 CRITICAL ERRORS (${#WARNINGS[@]} warning(s))${NC}"
else
  echo -e "${RED}${BOLD} INSTALLATION FINISHED WITH ${#ISSUES[@]} ISSUE(S) TO FIX${NC}"
fi
echo -e "${BOLD}==============================================================================${NC}"
echo -e "  Bot Directory    : ${TARGET_DIR}"
echo -e "  Python Venv      : ${TARGET_DIR}/.venv/bin/python"
echo -e "  Config File      : ${CONFIG_FILE} (Port ${BROKER_PORT}, Mode: ${CAPITAL_MODE})"
echo -e "  PC Web Dashboard : http://localhost:8787"
echo -e "  Live Service Log : journalctl --user -u gapshort -f"

if [[ "${#ISSUES[@]}" -gt 0 ]]; then
  echo -e "\n${RED}${BOLD}Issues Detected:${NC}"
  for idx in "${!ISSUES[@]}"; do
    echo -e "  $((idx+1)). ${ISSUES[$idx]}"
  done
fi

echo -e "\n${BOLD}What To Do Next:${NC}"
if [[ "${#NEXT_STEPS[@]}" -eq 0 ]]; then
  echo -e "  1. Open ${BOLD}http://localhost:8787${NC} in your browser (or your Tailscale https:// URL on your phone) and sign in."
  echo -e "  2. Keep IB Gateway open and logged into Paper Trading (with Auto-Restart set to 11:45 PM ET)."
  echo -e "  3. The service will automatically trade 0DTE SPX Put BWB at 10:30 AM ET, Gap Short at 15:45 ET, and reconcile both at 16:15 ET."
else
  for idx in "${!NEXT_STEPS[@]}"; do
    echo -e "  $((idx+1)). ${NEXT_STEPS[$idx]}"
  done
  echo -e "  $(( ${#NEXT_STEPS[@]} + 1 )). Open ${BOLD}http://localhost:8787${NC} in your PC browser to view the Dual-Strategy Dashboard (Both | Gap Short | 0DTE BWB)."
fi
echo -e "${BOLD}==============================================================================${NC}"
