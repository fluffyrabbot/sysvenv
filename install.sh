#!/bin/bash
#
# install.sh - Install two-tier Python package system
#
# Usage:
#   ./install.sh           # Install for current user
#   ./install.sh --system  # Install system-wide (requires root)
#

set -e

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYCTL_SCRIPT="$SCRIPT_DIR/pyctl"
PIP_WRAPPER="$SCRIPT_DIR/pip-wrapper"

# Colors
RED='\033[91m'
GREEN='\033[92m'
YELLOW='\033[93m'
BLUE='\033[94m'
CYAN='\033[96m'
BOLD='\033[1m'
RESET='\033[0m'

# ============================================================================
# Helper functions
# ============================================================================

info() {
    echo -e "${BLUE}ℹ${RESET} $1"
}

success() {
    echo -e "${GREEN}✓${RESET} $1"
}

warning() {
    echo -e "${YELLOW}⚠${RESET} $1"
}

error() {
    echo -e "${RED}✗${RESET} $1" >&2
}

heading() {
    echo -e "\n${CYAN}${BOLD}$1${RESET}"
}

# ============================================================================
# Check prerequisites
# ============================================================================

check_prereqs() {
    # Check for Python 3
    if ! command -v python3 >/dev/null 2>&1; then
        error "python3 not found. Please install Python 3.8+"
        exit 1
    fi

    # Check Python version
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    info "Found Python $PYTHON_VERSION"

    # Check for required scripts
    if [ ! -f "$PYCTL_SCRIPT" ]; then
        error "pyctl script not found at $PYCTL_SCRIPT"
        exit 1
    fi

    if [ ! -f "$PIP_WRAPPER" ]; then
        error "pip-wrapper not found at $PIP_WRAPPER"
        exit 1
    fi
}

# ============================================================================
# User installation
# ============================================================================

install_user() {
    heading "Installing for current user"

    # Create local bin if it doesn't exist
    LOCAL_BIN="$HOME/.local/bin"
    mkdir -p "$LOCAL_BIN"

    # Install pyctl
    info "Installing pyctl to $LOCAL_BIN..."
    cp "$PYCTL_SCRIPT" "$LOCAL_BIN/pyctl"
    chmod +x "$LOCAL_BIN/pyctl"
    success "Installed pyctl"

    # Note: We don't install pip wrapper for user-only install
    # It would conflict with system pip
    warning "Skipping pip wrapper (use --system for pip integration)"

    # Detect shell
    SHELL_NAME=$(basename "$SHELL")
    case "$SHELL_NAME" in
        bash)
            SHELL_RC="$HOME/.bashrc"
            ;;
        zsh)
            SHELL_RC="$HOME/.zshrc"
            ;;
        *)
            SHELL_RC="$HOME/.profile"
            warning "Unknown shell ($SHELL_NAME), using .profile"
            ;;
    esac

    # Add PATH to shell config if not already there
    SHELL_CONFIG_LINE='export PATH="$HOME/.local/bin:$PATH"  # pyctl'

    if [ -f "$SHELL_RC" ] && grep -q "\.local/bin" "$SHELL_RC"; then
        info "$SHELL_RC already has .local/bin in PATH"
    else
        info "Adding .local/bin to PATH in $SHELL_RC..."
        echo "" >> "$SHELL_RC"
        echo "# Added by pyctl installer" >> "$SHELL_RC"
        echo "$SHELL_CONFIG_LINE" >> "$SHELL_RC"
        success "Updated $SHELL_RC"
    fi

    # Initialize user venv
    heading "Initializing user venv"

    # Source the shell config to get pyctl in PATH for this script
    export PATH="$LOCAL_BIN:$PATH"

    pyctl init

    heading "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Reload your shell:"
    echo "     source $SHELL_RC"
    echo ""
    echo "  2. Verify installation:"
    echo "     pyctl status"
    echo ""
    echo "  3. Install packages:"
    echo "     pip install <package>"
    echo ""

    return 0
}

# ============================================================================
# System installation
# ============================================================================

install_system() {
    heading "Installing system-wide"

    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        error "System installation requires root. Run with sudo."
        exit 1
    fi

    # Install pyctl
    info "Installing pyctl to /usr/local/bin..."
    cp "$PYCTL_SCRIPT" /usr/local/bin/pyctl
    chmod +x /usr/local/bin/pyctl
    success "Installed pyctl"

    # Install pip wrapper
    # We'll create symlinks for pip, pip3, etc.
    info "Installing pip wrapper..."

    # First, find the real pip
    REAL_PIP=$(which pip3 2>/dev/null || which pip 2>/dev/null || echo "")

    if [ -z "$REAL_PIP" ]; then
        warning "Could not find system pip, skipping wrapper installation"
    else
        # Install wrapper
        cp "$PIP_WRAPPER" /usr/local/bin/pip-wrapper
        chmod +x /usr/local/bin/pip-wrapper

        # Create symlinks (these will shadow system pip via PATH precedence)
        # Only if /usr/local/bin is in PATH before /usr/bin
        ln -sf pip-wrapper /usr/local/bin/pip
        ln -sf pip-wrapper /usr/local/bin/pip3

        success "Installed pip wrapper"
        info "The wrapper will intercept pip commands when /usr/local/bin is in PATH"
    fi

    # Create system venv if requested
    read -p "Create system venv at /opt/system-python? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -d "/opt/system-python/venv" ]; then
            warning "/opt/system-python/venv already exists, skipping"
        else
            info "Creating system venv..."
            mkdir -p /opt/system-python
            python3 -m venv /opt/system-python/venv
            /opt/system-python/venv/bin/pip install --upgrade pip -q

            # Symlink from /usr/bin if requested
            read -p "Symlink /usr/bin/python3 to system venv? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                # Backup existing python3
                if [ -f "/usr/bin/python3" ] && [ ! -L "/usr/bin/python3" ]; then
                    mv /usr/bin/python3 /usr/bin/python3.bak
                    info "Backed up /usr/bin/python3 to /usr/bin/python3.bak"
                fi

                ln -sf /opt/system-python/venv/bin/python3 /usr/bin/python3
                ln -sf /opt/system-python/venv/bin/pip3 /usr/bin/pip3
                success "Symlinked /usr/bin/python3"
            fi

            success "Created system venv"
        fi
    fi

    heading "System installation complete!"
    echo ""
    echo "Users can now run:"
    echo "  pyctl init    # Initialize their user venv"
    echo ""

    return 0
}

# ============================================================================
# Main
# ============================================================================

main() {
    heading "Two-Tier Python Package System Installer"

    check_prereqs

    # Parse arguments
    if [ "${1:-}" = "--system" ]; then
        install_system
    else
        install_user
    fi
}

main "$@"
