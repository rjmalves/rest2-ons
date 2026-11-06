#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="python3"
ENTRYPOINT_NAME="rest2-ons"  # as defined in pyproject [project.scripts]
APP_NAME="rest2-ons"

# git expands this at fetch time, so the script never reads the token itself.
# shellcheck disable=SC2016
readonly CREDENTIAL_HELPER='!f() { [ "$1" = get ] || exit 0; echo username=x-access-token; printf "password=%s\n" "$(cat "$NWP_CORE_READ_TOKEN_FILE")"; }; f'

SYSTEM_INSTALL_DIR="/opt/$APP_NAME"
SYSTEM_BIN_DIR="/usr/local/bin"
USER_INSTALL_DIR="$HOME/.local/$APP_NAME"
USER_BIN_DIR="$HOME/.local/bin"

# Default to system-wide installation
INSTALL_DIR="$SYSTEM_INSTALL_DIR"
BIN_DIR="$SYSTEM_BIN_DIR"
USE_SUDO=1

FORCE=0
QUIET=0
USER_MODE=0
UNINSTALL=0

usage() {
	cat <<EOF
Usage: sudo ./setup.sh [options]

Install $APP_NAME CLI application.

Options:
	-u, --user      Install for current user only (no sudo required).
	                Installs to: $USER_INSTALL_DIR
	                Symlink to: $USER_BIN_DIR
	
	-f, --force     Force reinstallation (remove existing installation).
	-q, --quiet     Minimal output.
	--uninstall     Remove the installation.
	-h, --help      Show this help.

Environment:
	NWP_CORE_READ_TOKEN_FILE
	                Required. Path of a 0600 file holding the nwp-core read
	                token on one line. Under sudo, keep it with:
	                sudo --preserve-env=NWP_CORE_READ_TOKEN_FILE ./setup.sh

	uv              Required on PATH, at the [tool.uv] required-version of
	                pyproject.toml or later. Under sudo, PATH is sudo's
	                secure_path: put uv in /usr/local/bin.

System Installation (default, requires sudo):
	Installation directory: $SYSTEM_INSTALL_DIR
	Symlink directory: $SYSTEM_BIN_DIR

Examples:
	sudo --preserve-env=NWP_CORE_READ_TOKEN_FILE ./setup.sh
	                                   # System-wide installation
	./setup.sh --user                  # User-only installation
	sudo ./setup.sh --uninstall        # Remove system installation
	./setup.sh --user --uninstall      # Remove user installation
EOF
}

log() { [ "$QUIET" -eq 1 ] || echo -e "$*"; }

error() {
	printf 'Error: %b\n' "$*" >&2
	exit 1
}

run_quietly_or_show_output() {
	local output
	if ! output=$("$@" 2>&1); then
		printf '%s\n' "$output" >&2
		return 1
	fi
}

while [[ $# -gt 0 ]]; do
	case "$1" in
		-u|--user) USER_MODE=1; shift ;;
		-f|--force) FORCE=1; shift ;;
		-q|--quiet) QUIET=1; shift ;;
		--uninstall) UNINSTALL=1; shift ;;
		-h|--help) usage; exit 0 ;;
		*) echo "Unknown option: $1" >&2; usage; exit 1 ;;
	esac
done

if [[ $USER_MODE -eq 1 ]]; then
	INSTALL_DIR="$USER_INSTALL_DIR"
	BIN_DIR="$USER_BIN_DIR"
	USE_SUDO=0
	log "User mode: Installing to $INSTALL_DIR"
else
	log "System mode: Installing to $INSTALL_DIR (requires sudo)"
fi

if [[ $USE_SUDO -eq 1 && $EUID -ne 0 ]]; then
	error "System installation requires sudo. Run: sudo ./setup.sh"
fi

uninstall() {
	log "Uninstalling $APP_NAME..."
	
	local symlink="$BIN_DIR/$ENTRYPOINT_NAME"
	
	if [[ -L "$symlink" ]]; then
		rm -f "$symlink"
		log "Removed symlink: $symlink"
	fi
	
	if [[ -d "$INSTALL_DIR" ]]; then
		rm -rf "$INSTALL_DIR"
		log "Removed installation directory: $INSTALL_DIR"
	fi
	
	log "Uninstallation complete."
	exit 0
}

if [[ $UNINSTALL -eq 1 ]]; then
	uninstall
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
	error "$PYTHON_BIN not found in PATH."
fi

VENV_DIR="$INSTALL_DIR/venv"

if [[ -d "$INSTALL_DIR" && $FORCE -eq 0 ]]; then
	error "Installation directory already exists: $INSTALL_DIR\nUse --force to reinstall or --uninstall to remove."
fi

UV_MIN_VERSION="$(sed -n 's/^required-version = ">=\([0-9][0-9.]*\)".*/\1/p' "$PROJECT_ROOT/pyproject.toml" || true)"
if [[ -z "$UV_MIN_VERSION" ]]; then
	error "Cannot read the uv floor: no [tool.uv] required-version = \">=X.Y.Z\" line in $PROJECT_ROOT/pyproject.toml."
fi

if ! command -v uv >/dev/null 2>&1; then
	error "uv not found in PATH. Install uv $UV_MIN_VERSION or later.\nUnder sudo, PATH is sudo's secure_path, which includes /usr/local/bin and not ~/.local/bin: put uv in /usr/local/bin."
fi

UV_VERSION="$(uv --version | awk '{ print $2 }')"
if [[ "$(printf '%s\n%s\n' "$UV_MIN_VERSION" "$UV_VERSION" | sort -V | sed -n 1p)" != "$UV_MIN_VERSION" ]]; then
	error "uv $UV_VERSION is older than $UV_MIN_VERSION, the [tool.uv] required-version in pyproject.toml."
fi

if [[ -z "${NWP_CORE_READ_TOKEN_FILE:-}" ]]; then
	error "NWP_CORE_READ_TOKEN_FILE is not set. Set it to the path of a 0600 file holding the nwp-core read token on one line.\nUnder sudo, run: sudo --preserve-env=NWP_CORE_READ_TOKEN_FILE ./setup.sh"
fi
if [[ ! -f "$NWP_CORE_READ_TOKEN_FILE" ]]; then
	error "NWP_CORE_READ_TOKEN_FILE=$NWP_CORE_READ_TOKEN_FILE is not a regular file."
fi
TOKEN_FILE_MODE="$(stat -L -c %a "$NWP_CORE_READ_TOKEN_FILE")"
if (( 8#$TOKEN_FILE_MODE & 044 )); then
	error "NWP_CORE_READ_TOKEN_FILE=$NWP_CORE_READ_TOKEN_FILE is readable by group or others.\nRun: chmod 600 \"$NWP_CORE_READ_TOKEN_FILE\""
fi
if [[ "$(awk 'END { print NR }' "$NWP_CORE_READ_TOKEN_FILE")" != 1 ]] || ! grep -q . "$NWP_CORE_READ_TOKEN_FILE"; then
	error "NWP_CORE_READ_TOKEN_FILE=$NWP_CORE_READ_TOKEN_FILE must hold exactly one non-empty line."
fi
if grep -q $'\r' "$NWP_CORE_READ_TOKEN_FILE"; then
	error "NWP_CORE_READ_TOKEN_FILE=$NWP_CORE_READ_TOKEN_FILE must not contain a carriage return."
fi
# The helper's cat runs in git's working directory, not in this one.
NWP_CORE_READ_TOKEN_FILE="$(realpath -- "$NWP_CORE_READ_TOKEN_FILE")"
export NWP_CORE_READ_TOKEN_FILE

if [[ -d "$INSTALL_DIR" ]]; then
	log "Removing existing installation (--force requested)..."
	rm -rf "$INSTALL_DIR"
fi

log "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
# Leave no half-built installation behind if a later step fails.
trap 'rm -rf "$INSTALL_DIR"' EXIT

# uv enforces requires-python and the lock; the credential helper lives in the
# environment of this one command only.
log "Installing $APP_NAME..."
cd "$PROJECT_ROOT"
run_quietly_or_show_output env \
	UV_PROJECT_ENVIRONMENT="$VENV_DIR" \
	UV_PYTHON_DOWNLOADS=never \
	GIT_TERMINAL_PROMPT=0 \
	GIT_CONFIG_COUNT=2 \
	GIT_CONFIG_KEY_0=credential.https://github.com.helper \
	GIT_CONFIG_VALUE_0= \
	GIT_CONFIG_KEY_1=credential.https://github.com.helper \
	GIT_CONFIG_VALUE_1="$CREDENTIAL_HELPER" \
	uv sync --locked --no-dev --no-editable --compile-bytecode --python "$PYTHON_BIN" ||
	error "Installing $APP_NAME failed; uv's output is above."

mkdir -p "$BIN_DIR"

SYMLINK_PATH="$BIN_DIR/$ENTRYPOINT_NAME"
if [[ -L "$SYMLINK_PATH" || -f "$SYMLINK_PATH" ]]; then
	rm -f "$SYMLINK_PATH"
fi

ln -s "$VENV_DIR/bin/$ENTRYPOINT_NAME" "$SYMLINK_PATH"
log "Created symlink: $SYMLINK_PATH -> $VENV_DIR/bin/$ENTRYPOINT_NAME"

if [[ $USE_SUDO -eq 1 ]]; then
	# For system install, make it readable by all but writable only by root
	chmod -R a+rX,go-w "$INSTALL_DIR"
fi

trap - EXIT
log "\n✓ Installation complete!"

case ":$PATH:" in
	*":$BIN_DIR:"*)
		log "Run '$ENTRYPOINT_NAME --help' to get started."
		;;
	*)
		log "Note: $BIN_DIR is not in your PATH."
		log "Add it by adding this line to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
		log "  export PATH=\"$BIN_DIR:\$PATH\""
		log "\nThen reload your shell or run: source ~/.bashrc"
		;;
esac

if [[ $USER_MODE -eq 1 ]]; then
	log "\nUser installation location: $INSTALL_DIR"
else
	log "\nSystem installation location: $INSTALL_DIR"
	log "To uninstall, run: sudo ./setup.sh --uninstall"
fi