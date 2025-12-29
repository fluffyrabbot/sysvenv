# sysvenv

**Make `pip install` just work.** No sudo, no activation, no ceremony. No dignity left to lose.

## The Pitch

You want to install a package. The OS says "externally managed environment." You consider sudo. You realize you've already broken three distros this year doing that. 

`sysvenv` fixes this by giving you a personal playground that your shell loves more than the system defaults.

- **Zero-friction installs:** `pip install` just goes where it should.
- **Automatic snapshots:** Every mistake is recorded for future embarrassment.
- **Undo button:** Pretend that last install never happened.
- **Isolation:** Your "experimental" ML stack won't break your terminal's ability to render text.

## Quick Start

### 1. Install
```bash
git clone https://github.com/fluffyrabbot/sysvenv
cd sysvenv
./install.sh
source ~/.bashrc  # or ~/.zshrc
```

### 2. Live your life
```bash
# Just install things.
pip install requests black pytest

# Did it break?
sysvenv undo

# Want to see the damage?
sysvenv history
```

## Documentation

For people who actually read instructions:

- [Usage & Examples](docs/usage.md) - How to actually use the thing.
- [Internals](docs/internals.md) - How we mess with your PATH.
- [Troubleshooting](docs/troubleshooting.md) - When things inevitably go wrong.
- [NORTHSTAR2.md](NORTHSTAR2.md) - The grand architectural vision (for the brave).

## Philosophy

> "The right defaults should be invisible. Users should never think about where their packages go. They should just go to the right place."

This is not a security tool. This is not a production tool. This is a tool to make Python packaging suck slightly less for everyday development.

## License

MIT