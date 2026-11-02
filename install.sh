#!/bin/sh
# Saral installer — v0.3.0
#
# Installs Saral (the interpreter + its libraries) so `saral` works
# from any directory, like Python's `python` command.
#
# MODES (pick one):
#   LOCAL mode (works TODAY, for testing):
#     ./install.sh --local /path/to/saral-release
#     ./install.sh --local .            # from inside the Saral repo folder
#
#   GITHUB mode (NOT LIVE YET — do not expect it to work today):
#     curl -fsSL https://raw.githubusercontent.com/Die-Another-Day/Saral/main/install.sh | sh -s -- --github
#     This mode downloads from https://raw.githubusercontent.com/Die-Another-Day/Saral/main/
#     That repository has NOT been created/pushed yet (as of v0.3.0
#     preparation). Until it is pushed, GITHUB mode will fail with a
#     404, and that failure means "repo not published yet" — it does
#     not mean Saral is broken. LOCAL mode is the working mode today.
#
# DESTINATIONS:
#   Default (no sudo required):  PREFIX=$HOME/.local
#     binary:  $HOME/.local/bin/saral   (a small launcher script)
#     code:    $HOME/.local/lib/saral/saral.py
#     libs:    $HOME/.local/lib/saral/libs/
#   System install (needs root/sudo):  ./install.sh --local DIR --system
#     binary:  /usr/local/bin/saral
#     code:    /usr/local/lib/saral/saral.py
#     libs:    /usr/local/lib/saral/libs/
#   Or pick any prefix:  ./install.sh --local DIR --prefix /opt/saral-prefix
#
# After install it verifies itself by running `saral version`.
# If ~/.local/bin is not on your PATH, it prints the exact line to add.
#
# Uninstall: remove the two paths for your prefix, e.g.
#   rm -rf ~/.local/bin/saral ~/.local/lib/saral
#   (or /usr/local/bin/saral and /usr/local/lib/saral for --system)
#
# Requirements: python3, and curl or wget for GITHUB mode only.
# No network access is used in LOCAL mode. No credentials are
# collected, stored, or sent anywhere by this script.
set -eu

MODE=""
SRC=""
PREFIX=""
SYSTEM=0

usage() {
    echo "Usage:"
    echo "  $0 --local <source-dir> [--prefix <dir>]"
    echo "  $0 --local <source-dir> --system"
    echo "  $0 --github [--prefix <dir>]"
    echo "  $0 --github --system"
    echo ""
    echo "NOTE: --github is NOT LIVE YET. The Die-Another-Day/Saral repo"
    echo "has not been pushed yet, so --github will fail with a 404 until"
    echo "it is. Use --local to install today."
    exit "${1:-0}"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --local) SRC="$2"; MODE="local"; shift 2 ;;
        --github) MODE="github"; shift ;;
        --prefix) PREFIX="$2"; shift 2 ;;
        --system) SYSTEM=1; shift ;;
        -h|--help) usage 0 ;;
        *) echo "Unknown option: $1" >&2; usage 1 ;;
    esac
done

if [ -z "$MODE" ]; then
    echo "Error: pick a mode: --local <dir> or --github" >&2
    usage 1
fi

if [ "$SYSTEM" -eq 1 ]; then
    PREFIX="/usr/local"
elif [ -z "$PREFIX" ]; then
    PREFIX="$HOME/.local"
fi

command -v python3 >/dev/null 2>&1 || {
    echo "Error: python3 is required but not found. Install Python 3 first." >&2
    exit 1
}

BIN_DIR="$PREFIX/bin"
LIB_DIR="$PREFIX/lib/saral"
TMP_DIR=""

cleanup() {
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}
trap cleanup EXIT

if [ "$MODE" = "local" ]; then
    if [ -z "$SRC" ] || [ ! -f "$SRC/saral.py" ] || [ ! -d "$SRC/libs" ]; then
        echo "Error: --local source must be a Saral folder containing saral.py and libs/." >&2
        echo "Got: ${SRC:-<none>}" >&2
        exit 1
    fi
    SRC_ABS=$(cd "$SRC" && pwd)
elif [ "$MODE" = "github" ]; then
    echo "GITHUB mode: downloading Saral v0.3.0 from raw.githubusercontent.com ..."
    echo "If this fails with 404, the Saral repo has not been published yet (expected before push)."
    BASE_URL="https://raw.githubusercontent.com/Die-Another-Day/Saral/main"
    TMP_DIR=$(mktemp -d)
    SRC_ABS="$TMP_DIR"
    download() {
        # $1 = remote path, $2 = local path
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL "$BASE_URL/$1" -o "$2"
        elif command -v wget >/dev/null 2>&1; then
            wget -q "$BASE_URL/$1" -O "$2"
        else
            echo "Error: curl or wget is required for --github mode." >&2
            exit 1
        fi
    }
    download "saral.py" "$TMP_DIR/saral.py"
    mkdir -p "$TMP_DIR/libs/greet_bridge"
    for f in data.py file.py log_rules.py logs.py net.py report.py system.py; do
        download "libs/$f" "$TMP_DIR/libs/$f"
    done
    download "libs/greet_bridge/greet.js" "$TMP_DIR/libs/greet_bridge/greet.js"
    download "libs/greet_bridge/lib.json" "$TMP_DIR/libs/greet_bridge/lib.json"
fi

# Install: need write access to PREFIX. For --system as a non-root user,
# use sudo for the mkdir/cp/chmod steps only.
SUDO=""
if [ "$SYSTEM" -eq 1 ] && [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    else
        echo "Error: --system needs root or sudo, and neither is available." >&2
        echo "Use the default user-local install instead (no --system)." >&2
        exit 1
    fi
fi

$SUDO mkdir -p "$BIN_DIR" "$LIB_DIR/libs"
$SUDO cp "$SRC_ABS/saral.py" "$LIB_DIR/saral.py"
$SUDO cp -r "$SRC_ABS/libs/." "$LIB_DIR/libs/"
$SUDO chmod 755 "$LIB_DIR/saral.py" 2>/dev/null || true
# Remove any stale __pycache__ copied from a dev folder.
$SUDO rm -rf "$LIB_DIR/libs/__pycache__" 2>/dev/null || true

# Launcher: a tiny shell script, so `saral` works from any directory.
# The interpreter resolves its libs from its own folder (see saral.py
# _resolve_lib_dir), so the launcher only needs the lib path.
LAUNCHER_TMP=$(mktemp)
cat > "$LAUNCHER_TMP" <<EOF
#!/bin/sh
# Saral launcher (installed by install.sh). Do not edit by hand;
# re-run install.sh to update.
exec python3 "$LIB_DIR/saral.py" "\$@"
EOF
$SUDO cp "$LAUNCHER_TMP" "$BIN_DIR/saral"
$SUDO chmod 755 "$BIN_DIR/saral"
rm -f "$LAUNCHER_TMP"

echo "Installed Saral to:"
echo "  binary: $BIN_DIR/saral"
echo "  code:   $LIB_DIR/saral.py"
echo "  libs:   $LIB_DIR/libs/"
echo ""
echo "Verifying:"
"$BIN_DIR/saral" version

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo ""
        echo "NOTE: $BIN_DIR is not on your PATH yet. Add it with:"
        echo "  export PATH=\"$BIN_DIR:\$PATH\""
        echo "Or run Saral directly: $BIN_DIR/saral script.srl"
        ;;
esac
echo ""
echo "Try: $BIN_DIR/saral examples/hello.srl  (from a Saral checkout)"
echo "Uninstall: rm -rf $BIN_DIR/saral $LIB_DIR"
