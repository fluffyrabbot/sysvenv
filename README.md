# pyctl - Two-Tier Python Package System

**Make `pip install` just work.** No sudo, no activation, no ceremony.

## What is this?

A two-tier Python package architecture that gives you:

1. **System venv** (`/opt/system-python/`) - Root-locked, for OS components only
2. **User venv** (`~/.local/python-packages/`) - Your personal packages, no sudo needed

**Core principle:** When you run `pip install`, it should "just work" and go to your personal venv. Zero friction.

## Features

- **Zero-friction installs** - `pip install` automatically goes to your user venv
- **Automatic snapshots** - Every install/uninstall is tracked
- **Easy undo** - Roll back mistakes with `pyctl undo`
- **Named snapshots** - Save and restore package sets
- **Complete isolation** - User packages can't break system
- **Composable** - Works alongside project-local venvs

## Quick Start

### Install

```bash
# Clone and install
git clone <repo-url>
cd sysvenv
./install.sh
```

This will:
1. Install `pyctl` to `~/.local/bin`
2. Initialize your user venv
3. Add PATH to your shell config

### Reload your shell

```bash
source ~/.bashrc  # or ~/.zshrc
```

### Verify

```bash
pyctl status
```

### Use it

```bash
# Just install packages like normal
pip install requests black pytest

# See what changed
pyctl diff

# View history
pyctl history

# Undo last install
pyctl undo
```

## Commands

### Setup

- `pyctl init` - Initialize user venv (done by installer)
- `pyctl status` - Show current status
- `pyctl doctor [--fix]` - Health check and repair

### History & Undo

- `pyctl history [--limit N]` - Show operation history
- `pyctl diff [N]` - Show changes from operation N (default: last)
- `pyctl undo [N]` - Rollback last N operations (default: 1)

### Snapshots

- `pyctl snapshot <name>` - Save current package set
- `pyctl restore <name>` - Restore named snapshot
- `pyctl list-snapshots` - List available snapshots

### Maintenance

- `pyctl clean` - Nuke and recreate venv
- `pyctl clean --keep-baseline` - Restore to initial state

## How It Works

### PATH Precedence

```
Project venv (if activated)  ← Highest priority
    ↓
User venv (~/.local/python-packages/venv)
    ↓
System venv (/opt/system-python/venv)  ← System services only
```

When you type `python3` or `pip`, your shell finds the first one in PATH.

### User Setup

After installation, your `~/.bashrc` has:

```bash
export PATH="$HOME/.local/python-packages/venv/bin:$PATH"
```

This makes your user venv's Python and pip take precedence.

### System Setup (Optional)

System administrators can install system-wide:

```bash
sudo ./install.sh --system
```

This installs:
- `pyctl` to `/usr/local/bin/`
- pip wrapper to `/usr/local/bin/pip`
- Optionally creates `/opt/system-python/venv`

## Examples

### Install packages

```bash
pip install requests black pytest
# Automatically snapshotted, shows diff
```

### Undo a mistake

```bash
pip install some-bad-package
# Oh no, this broke things!

pyctl undo
# Back to previous state
```

### Save your dev environment

```bash
# Install your tools
pip install pytest black mypy ruff httpie

# Save it
pyctl snapshot dev-tools

# Later, after messing around...
pyctl restore dev-tools
# Back to your saved state
```

### Switch between different package sets

```bash
# ML work
pyctl restore ml-stack  # numpy, pandas, scikit-learn, etc.

# Web dev work
pyctl restore webdev    # flask, requests, etc.
```

### Start completely fresh

```bash
pyctl clean
# Venv deleted and recreated, empty slate
```

## Project Venvs Still Work

This doesn't replace project-local venvs. They work exactly as before:

```bash
# Create project venv
python3 -m venv myproject/venv

# Activate it
source myproject/venv/bin/activate

# Now pip uses project venv (highest priority in PATH)
pip install -r requirements.txt
```

When you deactivate, you're back to your user venv.

## Directory Structure

```
~/.local/python-packages/
├── venv/                    # Your Python packages
├── history/                 # Automatic snapshots
│   ├── 001_before.json
│   ├── 001_after.json
│   └── ...
├── snapshots/               # Named snapshots
│   ├── baseline.txt
│   ├── dev-tools.txt
│   └── ...
└── config.toml              # Configuration
```

## Configuration

Edit `~/.local/python-packages/config.toml`:

```toml
[history]
max_entries = 100              # Keep last 100 operations
auto_snapshot = true           # Snapshot before installs
show_diff_after_install = true # Show diff after install

[snapshots]
auto_baseline = true           # Create baseline on init

[ui]
color = true
verbose = false
```

## Troubleshooting

### pyctl: command not found

Your PATH doesn't include `~/.local/bin`. Add to `~/.bashrc`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then: `source ~/.bashrc`

### pip still asks for sudo

You're using the system pip. Make sure:

1. User venv is initialized: `pyctl status`
2. User venv is in PATH: `which pip` should show `~/.local/python-packages/venv/bin/pip`

### Want to use system Python temporarily

```bash
# Use full path to bypass user venv
/usr/bin/python3
```

Or remove user venv from PATH temporarily:

```bash
export PATH=${PATH#*:}  # Remove first entry (user venv)
```

## Uninstall

```bash
# Remove tools
rm ~/.local/bin/pyctl

# Remove user venv
rm -rf ~/.local/python-packages

# Remove PATH line from ~/.bashrc
# (edit manually)
```

## Philosophy

> "The right defaults should be invisible. Users should never think about where their packages go. They should just go to the right place."

This is not a security tool. This is not a production tool. This is a tool to make Python packaging suck less for everyday development.

## See Also

- [NORTHSTAR2.md](NORTHSTAR2.md) - Full vision and architecture
- `pyctl --help` - Command help
- `pyctl <command> --help` - Command-specific help

## License

MIT
