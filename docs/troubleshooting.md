# When Things Go Wrong

Even the best-laid plans of mice and sysadmins go awry.

## Common Issues

### `sysvenv: command not found`
Your PATH doesn't include `~/.local/bin`. Add this to your shell config:
```bash
export PATH="$HOME/.local/bin:$PATH"
```
Then run `source ~/.bashrc`.

### `pip` still asks for sudo
You're likely using the system pip. Check:
1. `sysvenv status` - Is the user venv initialized?
2. `which pip` - Should point to `~/.local/python-packages/venv/bin/pip`.

### I want to use system Python temporarily
Just use the full path: `/usr/bin/python3`. Or temporarily remove the user venv from your PATH:
```bash
export PATH=${PATH#*:}
```

## Uninstalling

If you've decided that Python packaging was meant to be painful and you'd like to return to that state:

1. **Remove tools:** `rm ~/.local/bin/sysvenv`
2. **Nuke the venv:** `rm -rf ~/.local/python-packages`
3. **Clean your shell:** Manually remove the PATH line from your `~/.bashrc` or `~/.zshrc`.

We'll miss you. (Not really, we're just scripts.)