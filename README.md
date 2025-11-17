# rest2-ons

ML generalization of the REST2 radiation with learnable parameters for using with the ECMWF CAMS forecasts, COD forecasts and in-site measured data.

## Installation

This CLI application can be installed system-wide or for the current user only.

### System-wide Installation (Recommended)

Installs to `/opt/rest2-ons` with a symlink in `/usr/local/bin`. Requires sudo privileges.

```bash
sudo ./setup.sh
```

### User Installation

Installs to `~/.local/rest2-ons` with a symlink in `~/.local/bin`. No sudo required.

```bash
./setup.sh --user
```

If `~/.local/bin` is not in your PATH, add it to your shell profile:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Installation Options

- `-u, --user`: Install for current user only (no sudo required)
- `-f, --force`: Force reinstallation (removes existing installation)
- `-q, --quiet`: Minimal output
- `--uninstall`: Remove the installation
- `-h, --help`: Show help

### Examples

```bash
# System-wide installation
sudo ./setup.sh

# User-only installation
./setup.sh --user

# Force reinstallation
sudo ./setup.sh --force

# Uninstall system installation
sudo ./setup.sh --uninstall

# Uninstall user installation
./setup.sh --user --uninstall
```

### Requirements

- Python >= 3.11
- pip, setuptools, wheel (automatically upgraded during installation)

### Using Makefile (Alternative)

For convenience, you can also use the provided Makefile:

```bash
make install         # System-wide installation
make install-user    # User installation
make reinstall       # Force reinstall
make uninstall       # Remove system installation
make uninstall-user  # Remove user installation
make clean          # Clean build artifacts
```

## Usage

After installation, you can run the application from anywhere:

```bash
rest2-ons --help
rest2-ons --config config.example.jsonc
```
