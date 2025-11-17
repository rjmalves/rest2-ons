# Contributing to rest2-ons

## Development Setup

If you're contributing to rest2-ons, you'll want to set up a development environment rather than installing the application system-wide.

### Development Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/rjmalves/rest2-ons.git
   cd rest2-ons
   ```

2. **Create a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install in editable mode:**

   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -e .
   ```

4. **Configure environment:**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run from development environment:**
   ```bash
   rest2-ons --config config.example.jsonc
   ```

### Development vs Production Installation

**Development** (`pip install -e .`):

- Editable installation - changes to code are immediately reflected
- Installed in local `venv/` directory
- Use for development, testing, debugging
- Easy to modify and experiment

**Production** (`./setup.sh`):

- Standard installation - code is copied to installation directory
- Installed in `/opt/rest2-ons` or `~/.local/rest2-ons`
- Use for end-users and production deployments
- Isolated from source code

### Running Tests

```bash
# Activate your development environment
source venv/bin/activate

# Run tests (when available)
pytest

# Run with coverage
pytest --cov=app
```

### Code Quality

Before submitting a pull request:

1. **Format your code:**

   ```bash
   # The project uses ruff for linting
   ruff check .
   ruff format .
   ```

2. **Check types (if using type hints):**

   ```bash
   mypy app/
   ```

3. **Run tests:**
   ```bash
   pytest
   ```

### Testing the Installation Script

If you're modifying `setup.sh`, test both installation modes:

1. **Test user installation:**

   ```bash
   ./setup.sh --user
   rest2-ons --help
   ./setup.sh --user --uninstall
   ```

2. **Test system installation (in a VM or container recommended):**
   ```bash
   sudo ./setup.sh
   rest2-ons --help
   sudo ./setup.sh --uninstall
   ```

### Project Structure

```
rest2-ons/
├── app/                    # Main application package
│   ├── internal/          # Internal configuration and constants
│   ├── services/          # Service modules
│   └── utils/             # Utility functions
├── data/                  # Data files
│   ├── artifacts/         # Generated artifacts
│   ├── input/            # Input data
│   └── output/           # Output results
├── scripts/               # Utility scripts
├── main.py               # Application entry point
├── pyproject.toml        # Project configuration
├── setup.sh              # Installation script
└── README.md             # Documentation
```

### Making Changes

1. **Create a feature branch:**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and commit:**

   ```bash
   git add .
   git commit -m "Description of your changes"
   ```

3. **Push and create a pull request:**
   ```bash
   git push origin feature/your-feature-name
   ```

### Release Process

For maintainers preparing a new release:

1. **Update version in `app/__init__.py`**
2. **Update CHANGELOG.md**
3. **Tag the release:**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```
4. **Test installation from the tag**
5. **Create GitHub release**

## Questions?

If you have questions about development setup or contributing, please open an issue on GitHub.
