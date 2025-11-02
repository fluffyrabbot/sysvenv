# NORTHSTAR2: Two-Tier Python Package System

## Vision Statement

Linux distributions should ship with a **two-tier Python package architecture**:

1. **System venv** (`/opt/system-python/`) - Root-locked, for OS components only
2. **User venv** (`~/.local/python-packages/`) - Default target for `pip install`, no sudo needed

**Core Principle:** When a user runs `pip install`, it should "just work" and go to their personal venv. Zero ceremony. Zero configuration. Zero sudo.

---

## The Problem We're Solving

### Current State (Broken)
- Users run `pip install` → pollutes system Python
- Or: `pip install --user` → weird PATH issues, inconsistent behavior
- Or: Must manually create venvs for every project → friction, forgotten activation
- Or: Use `sudo pip install` → security nightmare

### Desired State (Fixed)
- **User runs `pip install`** → Goes to `~/.local/python-packages/venv` automatically
- **Root runs `pip install`** → Goes to `/opt/system-python/venv` (distro packages only)
- **Projects can still use local venvs** → Nothing changes, just better defaults
- **Zero magic** → Users can see exactly where packages go

---

## Architecture

### Two Isolated Layers

```
┌─────────────────────────────────────────┐
│  System Layer (root-locked)             │
│  /opt/system-python/venv/               │
│                                         │
│  - Only touched by root/package manager │
│  - OS components, distro-shipped tools  │
│  - Immutable for regular users          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  User Layer (default target)            │
│  ~/.local/python-packages/venv/         │
│                                         │
│  - Default for `pip install`            │
│  - No sudo needed                       │
│  - User owns it completely              │
│  - Easy to nuke and rebuild             │
└─────────────────────────────────────────┘
```

### Directory Structure

**System (shared, read-only for users):**
```
/opt/system-python/
└── venv/                    # Standard Python venv
    ├── bin/
    ├── lib/
    └── ...
```

**User (per-user, full control):**
```
~/.local/python-packages/
├── venv/                    # User's global venv
│   ├── bin/
│   ├── lib/
│   └── ...
├── history/                 # Automatic snapshots
│   ├── 001_before.json      # Metadata + pip freeze before op
│   ├── 001_after.json       # Metadata + pip freeze after op
│   ├── 002_before.json
│   ├── 002_after.json
│   └── ...
├── snapshots/               # Named snapshots
│   ├── baseline.txt         # pip freeze of clean install
│   ├── ml-stack.txt         # Named snapshot: ML packages
│   └── webdev.txt           # Named snapshot: web dev packages
└── config.toml              # User preferences
```

---

## User Experience

### First-Time Setup

**One-line install:**
```bash
curl -sSL https://install.pyenv.sh | sh
```

**What it does:**
1. Creates `~/.local/python-packages/venv/`
2. Adds to `~/.bashrc` (or `~/.zshrc`):
   ```bash
   export PATH="$HOME/.local/python-packages/venv/bin:$PATH"
   ```
3. Wraps `pip` to auto-snapshot before installs
4. Done. Forever.

### Daily Usage

**Installing packages (just works):**
```bash
# No thinking required
pip install requests black pytest
```

**Behind the scenes:**
1. Snapshot current state → `history/042_before.json`
2. Run `pip install requests black pytest`
3. Snapshot new state → `history/042_after.json`
4. Show diff of what changed
5. User sees it, moves on

**Viewing history:**
```bash
pyctl history
# Output:
# #42  2025-11-01 10:30  pip install requests black pytest
# #41  2025-10-30 14:22  pip install numpy pandas
# #40  2025-10-29 09:15  pip uninstall click
```

**Seeing what changed:**
```bash
pyctl diff
# Shows last operation's diff

pyctl diff 41
# Shows what operation #41 changed
```

**Undoing mistakes:**
```bash
pyctl undo
# Rolls back operation #42

pyctl undo 3
# Rolls back last 3 operations
```

**Nuclear option (start fresh):**
```bash
pyctl clean
# Deletes ~/.local/python-packages/venv
# Recreates from scratch
# Optionally: pyctl clean --keep-baseline (restore to baseline snapshot)
```

**Snapshots for different workflows:**
```bash
# Save current state
pyctl snapshot ml-stack

# Later... switch to web dev packages
pyctl clean
pyctl restore webdev

# Back to ML work
pyctl restore ml-stack
```

---

## Implementation Strategy

### Components

#### 1. `pip` Wrapper (`/usr/local/bin/pip`)

**Smart routing logic:**
```bash
#!/bin/bash
if [ "$EUID" -eq 0 ]; then
    # Root → system venv
    TARGET_VENV="/opt/system-python/venv"
else
    # User → user venv
    TARGET_VENV="$HOME/.local/python-packages/venv"

    # Take snapshot before write operations
    if [[ "$1" =~ ^(install|uninstall|upgrade)$ ]]; then
        pyctl _snapshot-before "$@"
    fi
fi

# Run actual pip
"$TARGET_VENV/bin/pip" "$@"
EXITCODE=$?

# Record changes after write operations
if [ "$EUID" -ne 0 ] && [[ "$1" =~ ^(install|uninstall|upgrade)$ ]]; then
    pyctl _snapshot-after "$@"
fi

exit $EXITCODE
```

#### 2. `pyctl` Management CLI

**Commands:**
```bash
pyctl init                      # Initialize user venv
pyctl status                    # Show current state
pyctl history [--limit N]       # List operations
pyctl diff [N]                  # Show changes from operation N (default: last)
pyctl undo [N]                  # Rollback last N operations (default: 1)
pyctl clean [--keep-baseline]   # Nuke and recreate venv
pyctl snapshot <name>           # Save named snapshot
pyctl restore <name>            # Restore named snapshot
pyctl list-snapshots            # List available snapshots
pyctl doctor                    # Health check and repair
pyctl config <key> <value>      # Configure behavior
```

**Implementation:** Single Python script (~400-600 LOC)

#### 3. Shell Integration

**Auto-added to `~/.bashrc` / `~/.zshrc`:**
```bash
# Python User Venv
export PATH="$HOME/.local/python-packages/venv/bin:$PATH"
export PYTHONUSERBASE="$HOME/.local/python-packages"

# Optional: alias for quick access
alias pyclean='pyctl clean'
alias pyundo='pyctl undo'
```

---

## Data Structures

### History Entry (`history/042_before.json`)

```json
{
  "id": 42,
  "timestamp": "2025-11-01T10:30:00Z",
  "user": "ktw3000",
  "command": "pip install requests black pytest",
  "pip_args": ["install", "requests", "black", "pytest"],
  "freeze": "certifi==2023.11.17\ncharset-normalizer==3.3.2\n..."
}
```

### History Entry (`history/042_after.json`)

```json
{
  "id": 42,
  "timestamp": "2025-11-01T10:30:15Z",
  "user": "ktw3000",
  "command": "pip install requests black pytest",
  "pip_args": ["install", "requests", "black", "pytest"],
  "freeze": "black==23.12.1\ncertifi==2023.11.17\ncharset-normalizer==3.3.2\n...",
  "changes": {
    "added": ["requests==2.31.0", "black==23.12.1", "pytest==7.4.3", "urllib3==2.1.0", ...],
    "removed": [],
    "modified": []
  },
  "exit_code": 0
}
```

### Config File (`config.toml`)

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

---

## Snapshot & Undo Mechanics

### Taking a Snapshot (Automatic)

**Before `pip install`:**
1. Get current packages: `pip freeze`
2. Save to `history/N_before.json` with metadata
3. Run pip command
4. Get new packages: `pip freeze`
5. Calculate diff (added/removed/modified)
6. Save to `history/N_after.json`
7. Show diff to user

### Undoing an Operation

**Simple approach (fast enough):**
1. Read `history/N_before.json`
2. Extract `freeze` field (pip freeze before operation N)
3. Nuke current venv: `rm -rf ~/.local/python-packages/venv`
4. Create fresh venv: `python3 -m venv ~/.local/python-packages/venv`
5. Restore packages: `pip install -r <(echo "$freeze")`
6. Done

**Advanced approach (cached wheels):**
- Optionally cache wheels in `history/N_wheels/`
- Reinstall from cache instead of re-downloading
- Faster but uses more disk

### Named Snapshots

**Creating:**
```bash
pyctl snapshot ml-stack
# Saves current `pip freeze` to snapshots/ml-stack.txt
```

**Restoring:**
```bash
pyctl restore ml-stack
# Nukes venv, recreates, installs from snapshots/ml-stack.txt
```

---

## Ergonomics & Philosophy

### Design Principles

1. **Zero friction** - `pip install` just works, no activation, no flags
2. **Transparent** - Users can see where packages go (`~/.local/python-packages/`)
3. **Recoverable** - Every operation can be undone
4. **Auditable** - Full history of what was installed when
5. **Composable** - Works alongside project-local venvs
6. **Predictable** - Same behavior every time

### What This Doesn't Do

- **Not a project venv manager** - Use `python -m venv` for projects
- **Not a Python version manager** - Use `pyenv` or `mise` for that
- **Not a package resolver** - That's pip's job
- **Not security-focused** - User owns their venv, no locks

### What Problem Does This Actually Solve?

**Before:**
```bash
# User wants to install a tool
pip install httpie
# ERROR: externally-managed-environment
# WTF do I do now?

# User googles, finds stackoverflow
pip install --user httpie
# Works, but now PATH is weird and inconsistent

# Or: User gives up and uses pipx
pipx install httpie
# OK but now where are my libraries? Different tool for CLI vs libraries?
```

**After:**
```bash
pip install httpie
# Just works. Goes to ~/.local/python-packages/venv
# Done.
```

---

## Implementation Roadmap

### Phase 1: Core Functionality (MVP)
- [ ] `pyctl init` - Initialize user venv
- [ ] `pip` wrapper - Route to correct venv
- [ ] Basic history recording (before/after snapshots)
- [ ] `pyctl history` - View operations
- [ ] `pyctl diff` - View changes
- [ ] `pyctl undo` - Rollback operations
- [ ] Shell integration installer

### Phase 2: Quality of Life
- [ ] `pyctl clean` - Nuke and rebuild
- [ ] Named snapshots (save/restore)
- [ ] Baseline snapshot on init
- [ ] Config file support
- [ ] Pretty diff output with colors
- [ ] `pyctl doctor` - Health check

### Phase 3: Advanced Features
- [ ] Wheel caching for faster undo
- [ ] `pyctl search <pkg>` - Search for packages
- [ ] `pyctl info <pkg>` - Show package info
- [ ] `pyctl export` - Export history as requirements.txt
- [ ] Integration with system package manager (detect conflicts)

### Phase 4: Distribution
- [ ] Package for Debian/Ubuntu (`.deb`)
- [ ] Package for Fedora/RHEL (`.rpm`)
- [ ] Package for Arch (AUR)
- [ ] Homebrew formula (macOS)
- [ ] Docker image for testing
- [ ] CI/CD for releases

---

## Technical Decisions

### Why Python for `pyctl`?

- Users already have Python installed
- Easy to parse JSON, run pip freeze, manipulate venvs
- Single-file script possible (~500 LOC)
- Standard library has everything we need

### Why Bash for `pip` wrapper?

- Fast (no Python startup time)
- Simple routing logic
- Just calls `pyctl` for heavy lifting

### Why JSON for history?

- Easy to parse in Python
- Human-readable (ish)
- Can include pip freeze as a string field
- Machine-readable for future tooling

### Why not SQLite?

- Overkill for append-only log
- Files are easier to debug
- Can still build queries with `jq`

### Why separate `_before.json` and `_after.json`?

- Crash safety: If pip fails, we still have before state
- Easier to detect interrupted operations
- Can show "in progress" status

---

## Edge Cases & Questions

### What if user has existing `~/.local/`?

- Check on `pyctl init`, warn if conflicts detected
- Offer to migrate existing `~/.local/bin` entries

### What if user activates a project venv?

- Project venv PATH takes precedence (comes first)
- Wrapper detects `$VIRTUAL_ENV` and uses that
- User venv is fallback

### What if user wants to use system Python packages?

- User venv created with `--system-site-packages`?
- Or: Don't use this tool, use regular venv
- Config option: `inherit_system_packages = true`

### What about Windows/macOS?

- **macOS:** Same approach, works fine
- **Windows:** Different paths, but concept is identical
- `%USERPROFILE%\.local\python-packages\venv\`

### What about multiple Python versions?

- One user venv per Python version
- `~/.local/python-packages/py39/venv/`
- `~/.local/python-packages/py311/venv/`
- Wrapper detects `python3.11` vs `python3.9`

### How do we handle `pip` vs `pip3` vs `pip3.11`?

- Wrapper installed for all variants
- Or: Single wrapper, detects which Python was called

---

## Success Metrics

### User Experience
- [ ] New user can install packages in <30 seconds (including setup)
- [ ] Zero documentation needed for basic usage
- [ ] Undo works 100% of the time (excluding network failures)

### Technical
- [ ] Wrapper adds <50ms overhead to pip commands
- [ ] History storage uses <10MB per 100 operations
- [ ] Works on Python 3.8+

### Adoption
- [ ] Packaged in at least one major distro
- [ ] 1000+ GitHub stars
- [ ] Recommended in Python packaging docs

---

## FAQ

**Q: Why not just use `pipx`?**
A: `pipx` is for CLI tools only. This is for libraries AND tools. Different use case.

**Q: Why not just use `venv` manually?**
A: You can! This is just better defaults for the 80% case. Project venvs still work.

**Q: Isn't this similar to `--user` installs?**
A: Yes, but with a real venv, better isolation, and undo/history built-in.

**Q: What about Poetry/PDM/Hatch?**
A: Those are project dependency managers. This is for global packages. Complementary.

**Q: Why not integrate this into pip directly?**
A: Political/governance issues. Easier to ship as a distro default.

**Q: Does this break existing workflows?**
A: No. If you activate a project venv, it takes precedence. This is just a better fallback.

**Q: Can I disable the auto-snapshots?**
A: Yes. `pyctl config auto_snapshot false`

**Q: How do I migrate my existing packages?**
A: `pip freeze > old.txt && pyctl init && pip install -r old.txt`

---

## Comparison to Original sysvenv

| Aspect | sysvenv (v1) | This Design (v2) |
|--------|--------------|------------------|
| **Target** | Production servers | Dev machines |
| **Philosophy** | Security & audit | Ergonomics & undo |
| **Lock model** | Locked by default, sudo to unlock | No locks, user owns venv |
| **Audit** | Full enterprise audit log | Simple history for undo |
| **Complexity** | ~900 LOC Rust + systemd | ~500 LOC Python + bash wrapper |
| **User friction** | Lock/unlock ceremony | Zero - just works |
| **Undo** | Via snapshots | Built-in, automatic |
| **Use case** | "Don't touch prod" | "Iterate fast" |

**Verdict:** v1 was a misinterpretation. This is what was actually needed.

---

## Next Steps

1. **Build MVP** - Get core working in a weekend
2. **Dogfood** - Use it ourselves for a month
3. **Iterate** - Fix rough edges
4. **Package** - Ship for Debian/Ubuntu first
5. **Document** - Write clear docs
6. **Promote** - Get the word out

---

## License & Philosophy

**License:** MIT (maximum permissiveness)

**Philosophy:**
> "The right defaults should be invisible. Users should never think about where their packages go. They should just go to the right place."

This is not a security tool. This is not a production tool. This is a tool to make Python packaging suck less for everyday development.

---

**Let's build it.**
