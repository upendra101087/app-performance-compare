#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# In-House Device Farm — Remote Contributor Node Setup
#
# Configures a remote developer/QA machine to share its locally attached
# Android and/or iOS physical devices with the central Mac Mini Hub.
#
# Supported Operating Systems:
#   - macOS (Android & iOS devices)
#   - Linux (Android devices)
#
# Version Policy:
#   - Installs latest versions when software is missing.
#   - If an existing version is detected, prompts the user whether
#     to keep the current version or upgrade to the latest version.
#
# Usage:
#   chmod +x setup-remote-node.sh
#   ./setup-remote-node.sh [HUB_IP]               # Interactive mode
#   ./setup-remote-node.sh 192.168.1.100 --yes   # Auto-upgrade all
#   ./setup-remote-node.sh 192.168.1.100 --keep  # Auto-keep all
# ─────────────────────────────────────────────────────────────────────

set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ANSI Color formatting
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

info()   { echo -e "${CYAN}▶${NC} $*"; }
ok()     { echo -e "${GREEN}✓${NC} $*"; }
warn()   { echo -e "${YELLOW}!${NC} $*"; }
fail()   { echo -e "${RED}✗${NC} $*" >&2; exit 1; }
header() {
  echo
  echo -e "${BOLD}════════════════════════════════════════════════════════════${NC}"
  echo -e "${BOLD}$*${NC}"
  echo -e "${BOLD}════════════════════════════════════════════════════════════${NC}"
}
have() { command -v "$1" >/dev/null 2>&1; }

trap 'echo -e "${RED}✗ Remote node setup failed at line $LINENO.${NC}" >&2' ERR

# ── Command Line Flags & Arguments ────────────────────────────────────
ASSUME_YES=false
ASSUME_KEEP=false
HUB_HOST=""

for arg in "$@"; do
  case "$arg" in
    -y|--yes)
      ASSUME_YES=true
      ;;
    -k|--keep)
      ASSUME_KEEP=true
      ;;
    -h|--help)
      echo "Usage: ./setup-remote-node.sh [HUB_IP] [-y|--yes] [-k|--keep]"
      echo "  HUB_IP      IP address or hostname of the central Mac Mini Hub"
      echo "  -y, --yes   Automatically upgrade existing components to latest"
      echo "  -k, --keep  Automatically keep installed versions"
      exit 0
      ;;
    *)
      if [[ -z "$HUB_HOST" && "$arg" != -* ]]; then
        HUB_HOST="$arg"
      fi
      ;;
  esac
done

# ── Helper: Prompt User for Upgrade ─────────────────────────────────
prompt_upgrade() {
  local name="$1"
  local current_ver="$2"
  local default_choice="${3:-N}" # N = keep existing, Y = upgrade

  if [[ "$ASSUME_YES" == true ]]; then
    info "Auto-upgrading ${name} (${current_ver}) to latest due to --yes flag."
    return 0
  fi
  if [[ "$ASSUME_KEEP" == true ]]; then
    ok "Auto-keeping installed ${name} (${current_ver}) due to --keep flag."
    return 1
  fi

  local prompt_hint=""
  if [[ "$default_choice" == "Y" || "$default_choice" == "y" ]]; then
    prompt_hint="[Y/n]"
  else
    prompt_hint="[y/N]"
  fi

  echo -e "${YELLOW}! Detected ${name}: ${current_ver}${NC}"

  if [[ -t 0 ]] || [[ -c /dev/tty ]]; then
    local choice=""
    read -r -p "$(echo -e "${CYAN}? Keep installed ${name} (${current_ver}) or upgrade to latest? Upgrade? ${prompt_hint}: ${NC}")" choice </dev/tty || choice=""

    if [[ -z "$choice" ]]; then
      choice="$default_choice"
    fi

    case "$choice" in
      [yY][eE][sS]|[yY])
        return 0
        ;;
      *)
        return 1
        ;;
    esac
  else
    if [[ "$default_choice" == "Y" || "$default_choice" == "y" ]]; then
      return 0
    else
      info "Non-interactive session: keeping installed ${name} (${current_ver})."
      return 1
    fi
  fi
}

header "Remote Contributor Node — Environment Preflight"

OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Darwin)
    ok "Operating System: macOS ($ARCH) — Android and iOS devices supported"
    ;;
  Linux)
    ok "Operating System: Linux ($ARCH) — Android devices supported"
    ;;
  *)
    fail "Unsupported Operating System: $OS"
    ;;
esac

# ── Hub Host Resolution ───────────────────────────────────────────────
if [[ -z "$HUB_HOST" ]]; then
  if [[ -t 0 ]] || [[ -c /dev/tty ]]; then
    read -r -p "$(echo -e "${CYAN}? Enter the Central Mac Mini Hub IP address or Hostname: ${NC}")" HUB_HOST </dev/tty || HUB_HOST=""
  fi
fi

if [[ -z "$HUB_HOST" ]]; then
  warn "No Hub IP specified. Defaulting to 'localhost'."
  HUB_HOST="localhost"
fi

HUB_PORT="31337"
HUB_URL="http://${HUB_HOST}:${HUB_PORT}"
info "Central Hub Target: ${BOLD}${HUB_URL}${NC}"

# Update node-config.json with Hub URL
NODE_CONFIG_FILE="$ROOT/node-config.json"
if [[ -f "$NODE_CONFIG_FILE" ]]; then
  if [[ "$OS" == "Darwin" ]]; then
    sed -i '' "s|\"hub\": \"http://[^\"]*\"|\"hub\": \"${HUB_URL}\"|g" "$NODE_CONFIG_FILE" || true
    sed -i '' "s|\"hub\": \"http://<[^>]*>\"|\"hub\": \"${HUB_URL}\"|g" "$NODE_CONFIG_FILE" || true
  else
    sed -i "s|\"hub\": \"http://[^\"]*\"|\"hub\": \"${HUB_URL}\"|g" "$NODE_CONFIG_FILE" || true
    sed -i "s|\"hub\": \"http://<[^>]*>\"|\"hub\": \"${HUB_URL}\"|g" "$NODE_CONFIG_FILE" || true
  fi
  ok "Updated node-config.json to route to ${HUB_URL}"
fi

# ── 1. Package Manager Setup ─────────────────────────────────────────
header "1. Package Manager"

if [[ "$OS" == "Darwin" ]]; then
  if have brew; then
    BREW_VER="$(brew --version | head -1)"
    if prompt_upgrade "Homebrew" "$BREW_VER" "N"; then
      info "Updating Homebrew..."
      brew update
    else
      ok "Keeping current Homebrew."
    fi
  else
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
elif [[ "$OS" == "Linux" ]]; then
  if have apt-get; then
    info "Updating apt package index..."
    sudo apt-get update -y || true
  elif have dnf; then
    info "dnf package manager detected."
  fi
fi

# ── 2. Node.js Setup ──────────────────────────────────────────────────
header "2. Node.js (v18+ for Appium 2.x)"

MIN_NODE_MAJOR=18
SHOULD_INSTALL_NODE=false

if have node; then
  NODE_VERSION="$(node -v | sed 's/^v//')"
  NODE_MAJOR="${NODE_VERSION%%.*}"

  if (( NODE_MAJOR < MIN_NODE_MAJOR )); then
    warn "Installed Node.js (v$NODE_VERSION) is lower than recommended Node.js v$MIN_NODE_MAJOR+"
    if prompt_upgrade "Node.js" "v$NODE_VERSION (requires >= v$MIN_NODE_MAJOR)" "Y"; then
      SHOULD_INSTALL_NODE=true
    else
      warn "Proceeding with current Node.js v$NODE_VERSION."
    fi
  else
    if prompt_upgrade "Node.js" "v$NODE_VERSION" "N"; then
      SHOULD_INSTALL_NODE=true
    else
      ok "Keeping installed Node.js v$NODE_VERSION."
    fi
  fi
else
  info "Node.js not found. Installing latest Node.js..."
  SHOULD_INSTALL_NODE=true
fi

if [[ "$SHOULD_INSTALL_NODE" == true ]]; then
  if [[ "$OS" == "Darwin" ]]; then
    brew upgrade node 2>/dev/null || brew install node
    eval "$("$BREW_PREFIX/bin/brew" shellenv)"
  elif [[ "$OS" == "Linux" ]]; then
    if have apt-get; then
      curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
      sudo apt-get install -y nodejs
    else
      fail "Please install Node.js 18+ manually on this Linux distribution."
    fi
  fi
fi

have node || fail "Node.js is not available."
have npm || fail "npm is not available."
ok "Node.js: $(node -v)"
ok "npm:     $(npm -v)"

# ── 3. Android Platform-Tools (adb) ───────────────────────────────────
header "3. Android Platform-Tools (adb)"

SHOULD_INSTALL_ADB=false

if have adb; then
  ADB_VER="$(adb version | head -1)"
  if prompt_upgrade "Android platform-tools (adb)" "$ADB_VER" "N"; then
    SHOULD_INSTALL_ADB=true
  else
    ok "Keeping installed adb: $ADB_VER"
  fi
else
  info "adb is not installed. Installing Android Platform-Tools..."
  SHOULD_INSTALL_ADB=true
fi

if [[ "$SHOULD_INSTALL_ADB" == true ]]; then
  if [[ "$OS" == "Darwin" ]]; then
    brew upgrade android-platform-tools 2>/dev/null || brew install --cask android-platform-tools || brew install android-platform-tools
  elif [[ "$OS" == "Linux" ]]; then
    if have apt-get; then
      sudo apt-get install -y android-tools-adb android-tools-fastboot
    fi
  fi
fi

if have adb; then
  ok "adb active: $(adb version | head -1)"
else
  warn "adb is not on PATH. Please ensure adb is accessible to detect connected Android devices."
fi

# ── 4. Appium 3.x CLI ─────────────────────────────────────────────────
header "4. Appium 3.x CLI"

SHOULD_INSTALL_APPIUM=false

if have appium; then
  APPIUM_VER="$(appium -v 2>/dev/null || echo 'unknown')"
  MAJOR_VER="${APPIUM_VER%%.*}"
  if [[ "$MAJOR_VER" != "3" ]]; then
    warn "Installed Appium is v$APPIUM_VER. 'appium-device-farm' requires Appium ^3.0.0 (v3.x)."
    if prompt_upgrade "Appium (switch to compatible v3.x)" "v$APPIUM_VER" "Y"; then
      SHOULD_INSTALL_APPIUM=true
    else
      warn "Proceeding with installed Appium v$APPIUM_VER (device-farm plugin installation may fail)."
    fi
  elif prompt_upgrade "Appium (global)" "v$APPIUM_VER" "N"; then
    SHOULD_INSTALL_APPIUM=true
  else
    ok "Keeping installed Appium v$APPIUM_VER"
  fi
else
  info "Appium CLI not found. Installing Appium 3.x globally via npm..."
  SHOULD_INSTALL_APPIUM=true
fi

if [[ "$SHOULD_INSTALL_APPIUM" == true ]]; then
  info "Installing Appium 3.x globally via npm (appium@3)..."
  npm install -g appium@3
fi

ok "Appium CLI: $(appium -v)"

# ── 5. Appium Drivers & Device Farm Plugin ────────────────────────────
header "5. Appium Drivers & Device Farm Plugin"

INSTALLED_DRIVERS="$(appium driver list --installed 2>&1 || true)"

# UiAutomator2 driver
if printf '%s\n' "$INSTALLED_DRIVERS" | grep -Eiq 'uiautomator2'; then
  if prompt_upgrade "Appium UiAutomator2 driver" "installed" "N"; then
    info "Upgrading UiAutomator2 driver..."
    if ! appium driver update uiautomator2 --unsafe; then
      info "Update failed. Reinstalling UiAutomator2 driver cleanly..."
      appium driver uninstall uiautomator2 >/dev/null 2>&1 || true
      appium driver install uiautomator2 || true
    fi
  else
    ok "Keeping installed UiAutomator2 driver."
  fi
else
  info "Installing Appium UiAutomator2 driver..."
  appium driver install uiautomator2 || true
fi

# XCUITest driver (macOS only)
if [[ "$OS" == "Darwin" ]]; then
  if printf '%s\n' "$INSTALLED_DRIVERS" | grep -Eiq 'xcuitest'; then
    if prompt_upgrade "Appium XCUITest driver" "installed" "N"; then
      info "Upgrading XCUITest driver..."
      if ! appium driver update xcuitest --unsafe; then
        info "Update failed. Reinstalling XCUITest driver cleanly..."
        appium driver uninstall xcuitest >/dev/null 2>&1 || true
        appium driver install xcuitest || true
      fi
    else
      ok "Keeping installed XCUITest driver."
    fi
  else
    if [[ -d "/Applications/Xcode.app" ]]; then
      info "Installing Appium XCUITest driver..."
      appium driver install xcuitest || true
    fi
  fi
fi

# Appium Device Farm plugin check
INSTALLED_PLUGINS="$(appium plugin list --installed 2>&1 || true)"

if printf '%s\n' "$INSTALLED_PLUGINS" | grep -Eiq 'device-farm'; then
  if prompt_upgrade "Appium Device Farm plugin (appium-device-farm)" "installed" "N"; then
    info "Upgrading appium-device-farm plugin..."
    if ! appium plugin update device-farm --unsafe; then
      info "Update failed. Reinstalling device-farm plugin cleanly..."
      appium plugin uninstall device-farm >/dev/null 2>&1 || true
      appium plugin install --source=npm appium-device-farm || true
    fi
  else
    ok "Keeping installed appium-device-farm plugin."
  fi
else
  info "Installing Appium Device Farm plugin..."
  appium plugin install --source=npm appium-device-farm || true
fi

# ── Summary & Next Steps ──────────────────────────────────────────────
header "Remote Node Setup Complete!"

echo -e "${GREEN}✓ Node environment verified and ready.${NC}"
echo -e "Central Hub: ${BOLD}${HUB_URL}${NC}"
echo
echo -e "${BOLD}To start sharing devices connected to this machine:${NC}"
echo -e "  1. Plug in your Android (with USB Debugging enabled) or iOS device."
echo -e "  2. Start the Appium Node:"
echo -e "     ${CYAN}appium server --use-plugins=device-farm --config ./node-config.json${NC}"
echo
echo -e "${BOLD}Your connected devices will automatically register to:${NC}"
echo -e "  ${CYAN}${HUB_URL}/device-farm${NC}"
echo
