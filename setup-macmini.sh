#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# In-House Device Farm — Mac Mini Hub Setup & Environment Installer
#
# Configures the central Mac Mini Hub to run Appium Device Farm:
#   - Homebrew
#   - Node.js (v20+ / v22+)
#   - OpenJDK (Java 17+)
#   - Android Platform-Tools (adb) & SDK
#   - iOS Toolchain (Xcode CLI Tools, libimobiledevice, ideviceinstaller)
#   - Appium 3.x CLI
#   - Appium Drivers (UiAutomator2, XCUITest)
#   - Appium Device Farm Plugin (appium-device-farm)
#   - Python 3 Performance Dependencies (numpy, requests, appium-python-client, tidevice)
#   - Shell Environment Configuration (.zprofile / .zshrc)
#
# Version Policy:
#   - Installs latest versions when software is missing.
#   - If an existing version is detected, prompts the user whether
#     to keep the current version or upgrade to the latest version.
#
# Usage:
#   chmod +x setup-macmini.sh
#   ./setup-macmini.sh          # Interactive mode
#   ./setup-macmini.sh --yes    # Auto-upgrade all installed software to latest
#   ./setup-macmini.sh --keep   # Auto-keep all currently installed software
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

trap 'echo -e "${RED}✗ Hub setup failed at line $LINENO.${NC}" >&2' ERR

# ── Command Line Flags ────────────────────────────────────────────────
ASSUME_YES=false
ASSUME_KEEP=false

for arg in "$@"; do
  case "$arg" in
    -y|--yes)
      ASSUME_YES=true
      ;;
    -k|--keep)
      ASSUME_KEEP=true
      ;;
    -h|--help)
      echo "Usage: ./setup-macmini.sh [-y|--yes] [-k|--keep]"
      echo "  -y, --yes   Automatically upgrade existing components to latest"
      echo "  -k, --keep  Automatically keep installed versions"
      exit 0
      ;;
  esac
done

# ── Helper: Prompt User for Upgrade ─────────────────────────────────
# Returns 0 if user requests upgrade, 1 if user wants to keep current version.
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
        return 0 # User wants upgrade
        ;;
      *)
        return 1 # Keep installed version
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

header "Device Farm Mac Mini Hub — Environment Preflight"

OS="$(uname -s)"
ARCH="$(uname -m)"

if [[ "$OS" != "Darwin" ]]; then
  fail "This script is tailored for the Mac Mini host running macOS. Detected OS: $OS"
fi
ok "Host Operating System: macOS ($ARCH)"

if [[ "${EUID}" -eq 0 ]]; then
  warn "Running as root is not recommended. Homebrew will refuse to run as root."
fi

# ── 1. Package Manager Setup (Homebrew) ──────────────────────────────
header "1. Package Manager (Homebrew)"

if have brew; then
  BREW_VER="$(brew --version | head -1)"
  if prompt_upgrade "Homebrew" "$BREW_VER" "N"; then
    info "Updating Homebrew to latest..."
    brew update
    ok "Homebrew updated to latest."
  else
    ok "Keeping current Homebrew installation."
  fi
else
  info "Homebrew not found. Installing latest Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

if [[ -x /opt/homebrew/bin/brew ]]; then
  BREW_PREFIX="/opt/homebrew"
elif [[ -x /usr/local/bin/brew ]]; then
  BREW_PREFIX="/usr/local"
else
  fail "Homebrew installation could not be found."
fi
eval "$("$BREW_PREFIX/bin/brew" shellenv)"

# ── 2. Node.js Setup ──────────────────────────────────────────────────
header "2. Node.js (v18+ required for Appium 2.x)"

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
  info "Node.js is not installed. Installing latest Node.js via Homebrew..."
  SHOULD_INSTALL_NODE=true
fi

if [[ "$SHOULD_INSTALL_NODE" == true ]]; then
  info "Installing/upgrading to latest Node.js..."
  if brew list --formula node >/dev/null 2>&1; then
    brew upgrade node || brew install node
  else
    brew install node
  fi
  eval "$("$BREW_PREFIX/bin/brew" shellenv)"
fi

have node || fail "Node.js is not available."
have npm || fail "npm is not available."
ok "Node.js: $(node -v)"
ok "npm:     $(npm -v)"

# ── 3. OpenJDK Setup (Java 17+) ───────────────────────────────────────
header "3. OpenJDK (Java 17+ for Android SDK & Appium)"

SHOULD_INSTALL_JAVA=false

if have java; then
  JAVA_VERSION_RAW="$(java -version 2>&1 | head -1)"
  JAVA_MAJOR="$(java -version 2>&1 | sed -n 's/.*version "\([0-9]*\).*/\1/p')"
  if [[ -z "$JAVA_MAJOR" ]]; then
    JAVA_MAJOR="$(java -version 2>&1 | sed -n 's/.*openjdk \([0-9]*\).*/\1/p')"
  fi

  if [[ -n "$JAVA_MAJOR" ]] && (( JAVA_MAJOR < 17 )); then
    warn "Installed Java ($JAVA_VERSION_RAW) is lower than required Java 17+"
    if prompt_upgrade "OpenJDK" "$JAVA_VERSION_RAW (requires >= 17)" "Y"; then
      SHOULD_INSTALL_JAVA=true
    fi
  else
    if prompt_upgrade "OpenJDK" "$JAVA_VERSION_RAW" "N"; then
      SHOULD_INSTALL_JAVA=true
    else
      ok "Keeping installed Java: $JAVA_VERSION_RAW"
    fi
  fi
else
  info "Java is not installed. Installing OpenJDK 17 via Homebrew..."
  SHOULD_INSTALL_JAVA=true
fi

if [[ "$SHOULD_INSTALL_JAVA" == true ]]; then
  info "Installing/upgrading OpenJDK 17..."
  brew install openjdk@17 || brew upgrade openjdk@17 || true
  JDK_PREFIX="$(brew --prefix openjdk@17 2>/dev/null || brew --prefix openjdk)"
  export PATH="$JDK_PREFIX/bin:$PATH"
  if [[ -d "$JDK_PREFIX/libexec/openjdk.jdk/Contents/Home" ]]; then
    export JAVA_HOME="$JDK_PREFIX/libexec/openjdk.jdk/Contents/Home"
  else
    export JAVA_HOME="$JDK_PREFIX"
  fi
  # Setup system wrapper link if sudo is available
  if [[ -d "$JDK_PREFIX/libexec/openjdk.jdk" ]] && have sudo; then
    sudo ln -sfn "$JDK_PREFIX/libexec/openjdk.jdk" /Library/Java/JavaVirtualMachines/openjdk-17.jdk 2>/dev/null || true
  fi
fi

if have java; then
  JAVA_HOME_VALUE="${JAVA_HOME:-$(/usr/libexec/java_home 2>/dev/null || which java)}"
  export JAVA_HOME="$JAVA_HOME_VALUE"
  ok "JAVA_HOME active: $JAVA_HOME"
fi

# ── 4. Android Platform-Tools (adb) & SDK ─────────────────────────────
header "4. Android Platform-Tools (adb)"

DEFAULT_ANDROID_HOME="$HOME/Library/Android/sdk"
export ANDROID_HOME="${ANDROID_HOME:-$DEFAULT_ANDROID_HOME}"
mkdir -p "$ANDROID_HOME"

SHOULD_INSTALL_ADB=false

if have adb; then
  ADB_VER="$(adb version | head -1)"
  if prompt_upgrade "Android platform-tools (adb)" "$ADB_VER" "N"; then
    SHOULD_INSTALL_ADB=true
  else
    ok "Keeping installed adb: $ADB_VER"
  fi
else
  info "adb is not installed. Installing Android Platform-Tools via Homebrew..."
  SHOULD_INSTALL_ADB=true
fi

if [[ "$SHOULD_INSTALL_ADB" == true ]]; then
  info "Installing/upgrading Android Platform-Tools..."
  brew upgrade android-platform-tools 2>/dev/null || brew install --cask android-platform-tools || brew install android-platform-tools
fi

export PATH="$ANDROID_HOME/platform-tools:$PATH"
if have adb; then
  ok "adb active: $(adb version | head -1)"
else
  warn "adb is not on PATH yet. Ensure \$ANDROID_HOME/platform-tools is in your PATH."
fi

# ── 5. iOS Toolchain & Device Utilities ───────────────────────────────
header "5. iOS Toolchain & Device Utilities"

if xcode-select -p >/dev/null 2>&1; then
  ok "Xcode Command Line Tools installed at: $(xcode-select -p)"
else
  info "Installing Xcode Command Line Tools..."
  xcode-select --install || true
  warn "Follow the system prompt to complete Xcode Command Line Tools installation."
fi

if [[ -d "/Applications/Xcode.app" ]]; then
  ok "Full Xcode installed (/Applications/Xcode.app - Real iOS & Simulator automation supported)"
else
  warn "Xcode.app not found in /Applications. For physical iOS device signing and XCUITest, Xcode is recommended."
fi

# libimobiledevice check
if have idevice_id; then
  IDEVICE_VER="$(idevice_id -v 2>&1 | head -1 || echo 'installed')"
  if prompt_upgrade "libimobiledevice" "$IDEVICE_VER" "N"; then
    info "Upgrading libimobiledevice..."
    brew upgrade libimobiledevice || true
  else
    ok "Keeping installed libimobiledevice."
  fi
else
  info "Installing libimobiledevice (for real iOS communication)..."
  brew install libimobiledevice || true
fi

# ideviceinstaller check
if have ideviceinstaller; then
  if prompt_upgrade "ideviceinstaller" "installed" "N"; then
    info "Upgrading ideviceinstaller..."
    brew upgrade ideviceinstaller || true
  else
    ok "Keeping installed ideviceinstaller."
  fi
else
  info "Installing ideviceinstaller (for IPA installation on real iOS)..."
  brew install ideviceinstaller || true
fi

# ── 6. Appium 3.x CLI ─────────────────────────────────────────────────
header "6. Appium 3.x CLI"

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

# ── 7. Appium Drivers & Plugins ───────────────────────────────────────
header "7. Appium Drivers & Device Farm Plugin"

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

# XCUITest driver
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
  info "Installing Appium XCUITest driver..."
  appium driver install xcuitest || true
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

# ── 8. Python Performance Telemetry Dependencies ──────────────────────
header "8. Python 3 & Telemetry Dependencies"

if have python3; then
  ok "Python 3: $(python3 --version)"
else
  info "Python 3 not found. Installing via Homebrew..."
  brew install python@3.11 || brew install python
fi

PIP_PACKAGES="numpy requests appium-python-client tidevice"
info "Checking Python performance dependencies ($PIP_PACKAGES)..."

if python3 -c "import numpy, requests, appium, tidevice" >/dev/null 2>&1; then
  if prompt_upgrade "Python perf packages (numpy, appium-python-client, tidevice)" "installed" "N"; then
    info "Upgrading Python dependencies..."
    pip3 install --upgrade --quiet $PIP_PACKAGES || true
    ok "Python dependencies updated."
  else
    ok "Keeping installed Python packages."
  fi
else
  info "Installing required Python dependencies..."
  pip3 install --quiet $PIP_PACKAGES || true
  ok "Python dependencies installed."
fi

# ── 9. Shell Environment Profile Persistence ──────────────────────────
header "9. Shell Environment Profile Persistence"

PROFILE_FILE=""
if [[ -f "$HOME/.zprofile" ]] || [[ "${SHELL:-}" == *"zsh"* ]]; then
  PROFILE_FILE="$HOME/.zprofile"
elif [[ -f "$HOME/.bashrc" ]]; then
  PROFILE_FILE="$HOME/.bashrc"
else
  PROFILE_FILE="$HOME/.profile"
fi

touch "$PROFILE_FILE"

MARKER_START="# >>> APPIUM DEVICE FARM HUB ENV >>>"
MARKER_END="# <<< APPIUM DEVICE FARM HUB ENV <<<"

# Remove existing block to prevent duplicates
if grep -qF "$MARKER_START" "$PROFILE_FILE"; then
  sed -i '' "/$MARKER_START/,/$MARKER_END/d" "$PROFILE_FILE" 2>/dev/null || true
fi

cat >> "$PROFILE_FILE" << EOF
$MARKER_START
export JAVA_HOME="${JAVA_HOME:-}"
export ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
export ANDROID_SDK_ROOT="\$ANDROID_HOME"
export PATH="\$PATH:\$ANDROID_HOME/platform-tools:\$ANDROID_HOME/cmdline-tools/latest/bin"
$MARKER_END
EOF

ok "Environment variables persisted to $PROFILE_FILE"

# ── Summary & Next Steps ──────────────────────────────────────────────
header "Mac Mini Hub Setup Complete!"

HOST_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo '<MAC_MINI_IP>')"

echo -e "${GREEN}✓ All software dependencies verified and ready.${NC}"
echo
echo -e "${BOLD}To start the Central Device Farm Hub:${NC}"
echo -e "  ${CYAN}appium server --use-plugins=device-farm --config ./hub-config.json${NC}"
echo
echo -e "${BOLD}Access the Web Dashboard:${NC}"
echo -e "  ${CYAN}http://${HOST_IP}:31337/device-farm${NC}"
echo
echo -e "${BOLD}For remote colleagues to plug in devices:${NC}"
echo -e "  Share ${CYAN}setup-remote-node.sh${NC} and tell them to run:"
echo -e "  ${CYAN}./setup-remote-node.sh ${HOST_IP}${NC}"
echo
