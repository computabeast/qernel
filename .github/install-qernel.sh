
#!/usr/bin/env bash
set -Eeuo pipefail

# Qernel nightly installer script
# Always downloads from: https://github.com/computabeast/qernel/releases/download/nightly/

# Colors (optional) with TTY and NO_COLOR respect
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
CYAN='\033[0;36m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; RED='\033[0;31m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'
else
CYAN=''; GREEN=''; BLUE=''; RED=''; BOLD=''; DIM=''; NC=''
fi
hr(){ printf "%s\n" "${DIM}────────────────────────────────────────────────────────${NC}"; }
step(){ printf "%b %s\n" "${BLUE}>${NC}" "$1"; }
ok(){ printf "%b %s\n" "${GREEN}[OK]${NC}" "$1"; }
err(){ printf "%b %s\n" "${RED}[ERROR]${NC}" "$1"; }

# Config (override via env if you ever fork this)
OWNER="${QERNEL_GH_OWNER:-computabeast}"
REPO="${QERNEL_GH_REPO:-qernel}"
APP_NAME="${QERNEL_APP_NAME:-qernel}"
INSTALL_ROOT="${QERNEL_INSTALL_ROOT:-$HOME/.local/share/$APP_NAME}"
BIN_DIR="${QERNEL_BIN_DIR:-$HOME/.local/bin}"
CHANNEL_TAG="${QERNEL_CHANNEL_TAG:-nightly}"   # always "nightly" for this script
USE_CARGO_FALLBACK="${QERNEL_USE_CARGO_FALLBACK:-0}"  # 1 to try cargo if download fails

echo
echo -e "${BOLD}${CYAN}Installing qernel...${NC}"
echo

# 1) OS / Arch detection
step "Detecting system architecture..."
OS="$(uname -s)"
case "$OS" in
  Darwin*) OS="darwin" ;;
  Linux*)  OS="linux" ;;
  *) err "Unsupported OS: $(uname -s)"; exit 1 ;;
 esac

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64)  ARCH="x64" ;;
  arm64|aarch64) ARCH="arm64" ;;
  *) err "Unsupported arch: $(uname -m)"; exit 1 ;;
 esac
ok "Detected ${OS}/${ARCH}"

# 2) Asset URLs
BASE="https://github.com/${OWNER}/${REPO}/releases/download/${CHANNEL_TAG}"
ASSET="${APP_NAME}-${OS}-${ARCH}.tar.gz"
SUMS="SHA256SUMS"

# 3) Download
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
step "Downloading ${ASSET} from nightly..."
echo -e "${DIM}  ${BASE}/${ASSET}${NC}"
if ! curl -fSL --progress-bar "${BASE}/${ASSET}" -o "${TMP}/${ASSET}"; then
  err "Nightly asset not found for ${OS}/${ARCH}."

  if [ "$USE_CARGO_FALLBACK" = "1" ]; then
    step "Trying cargo install fallback..."
    if ! command -v cargo >/dev/null 2>&1; then
      echo "  cargo not found. Install Rust (rustup) and re-run, or set QERNEL_USE_CARGO_FALLBACK=0."
      exit 1
    fi
    cargo install --git "https://github.com/${OWNER}/${REPO}" --tag "${CHANNEL_TAG}" --locked || cargo install --git "https://github.com/${OWNER}/${REPO}" --locked
    mkdir -p "$BIN_DIR"
    rm -f "$BIN_DIR/$APP_NAME"
    ln -s "$HOME/.cargo/bin/$APP_NAME" "$BIN_DIR/$APP_NAME"
    ok "Installed via cargo -> $BIN_DIR/$APP_NAME"
    exit 0
  fi

  exit 1
fi
ok "Downloaded package"

# 4) Optional checksum verification
if curl -fsSL "${BASE}/${SUMS}" -o "${TMP}/${SUMS}"; then
  step "Verifying checksum"
  EXPECTED="$(grep " ${ASSET}$" "${TMP}/${SUMS}" | awk '{print $1}' || true)"
  if [ -n "${EXPECTED:-}" ]; then
    if command -v sha256sum >/dev/null 2>&1; then
      echo "$EXPECTED  ${TMP}/${ASSET}" | sha256sum -c -
    elif command -v shasum >/dev/null 2>&1; then
      echo "$EXPECTED  ${TMP}/${ASSET}" | shasum -a 256 -c -
    else
      echo "  (no sha256 tool; skipping verification)"
    fi
  fi
fi

# 5) Extract to a versioned dir labelled 'nightly'
step "Installing..."
TS="$(date +%s)"
TEMP_EXTRACT_DIR="$INSTALL_ROOT/versions/.tmp-${CHANNEL_TAG}-${TS}"
FINAL_DIR="$INSTALL_ROOT/versions/${CHANNEL_TAG}"
mkdir -p "$TEMP_EXTRACT_DIR"

tar -xzf "${TMP}/${ASSET}" -C "$TEMP_EXTRACT_DIR" --strip-components=0
# macOS quarantine (best-effort)
if [ "$OS" = "darwin" ] && command -v xattr >/dev/null 2>&1; then
  xattr -dr com.apple.quarantine "$TEMP_EXTRACT_DIR" || true
fi

rm -rf "$FINAL_DIR"
mv "$TEMP_EXTRACT_DIR" "$FINAL_DIR"

# 6) Symlink into ~/.local/bin
mkdir -p "$BIN_DIR"
chmod +x "$FINAL_DIR/$APP_NAME" || true
rm -f "$BIN_DIR/$APP_NAME"
ln -s "$FINAL_DIR/$APP_NAME" "$BIN_DIR/$APP_NAME"
ok "Installed ${APP_NAME} (nightly) -> $BIN_DIR/$APP_NAME"

# 7) PATH hint
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo -e "${CYAN}INFO${NC} Add to PATH (e.g.):\n   echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.zshrc && source ~/.zshrc" ;;
 esac

echo
echo
echo -e "${BOLD}${CYAN}Done.${NC}"
echo
