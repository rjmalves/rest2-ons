# Contributing to rest2-ons

Thank you for your interest in contributing! This document provides guidelines for contributions to the project.

## 📋 Table of Contents

- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)

---

## 🤝 How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/rjmalves/rest2-ons/issues)
2. If not found, create a new issue using the bug report template
3. Include:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs. observed behavior
   - Python version and package version
   - Error logs (if applicable)

### Suggesting Improvements

1. Open an issue using the feature request template
2. Describe:
   - The problem the improvement solves
   - The proposed solution
   - Alternatives considered

### Contributing Code

1. Fork the repository
2. Create a branch for your feature (`git checkout -b feature/my-feature`)
3. Make atomic commits with descriptive messages
4. Write/update tests for your changes
5. Ensure all tests pass
6. Open a Pull Request

---

## 🛠️ Development Setup

### Prerequisites

- Python >= 3.11
- Git
- Visual Studio Code (recommended) or other IDE

### Initial Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/rest2-ons.git
cd rest2-ons

# Add upstream remote
git remote add upstream https://github.com/rjmalves/rest2-ons.git

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in editable mode with dev dependencies
pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"

# Or install dev dependencies manually
pip install -e .
pip install pytest pytest-cov ruff mypy
```

### Verifying Installation

```bash
# Run the application
rest2-ons --help

# Run tests
pytest

# Run linter
ruff check .
```

### Development vs Production Installation

| Aspect       | Development (`pip install -e .`)       | Production (`./setup.sh`)                |
| ------------ | -------------------------------------- | ---------------------------------------- |
| Installation | Editable - changes reflect immediately | Standard - code is copied                |
| Location     | Local `venv/` directory                | `/opt/rest2-ons` or `~/.local/rest2-ons` |
| Use case     | Development, testing, debugging        | End-users, production                    |

---

## 📐 Code Standards

### Style

We follow [PEP 8](https://peps.python.org/pep-0008/) with configurations in `pyproject.toml`:

```toml
# Main settings:
# - Max line length: 80 characters
# - Imports: sorted by isort rules
# - Formatting: ruff format
```

### Style Verification

```bash
# Run linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Check formatting without changes
ruff format --check .
```

### Python Best Practices

#### 1. Small, Pure Functions

```python
# ✅ Good: focused function, no side effects
def calculate_rmse(observed: np.ndarray, predicted: np.ndarray) -> float:
    """Calculate Root Mean Square Error."""
    if len(observed) != len(predicted):
        raise ValueError("Arrays must have same length")
    return np.sqrt(np.mean((observed - predicted) ** 2))

# ❌ Avoid: large functions with multiple responsibilities
```

#### 2. Input Validation

```python
# ✅ Good: validate types and dimensions
def process_data(df: pl.DataFrame, column: str) -> pl.DataFrame:
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame")
    # ...
```

#### 3. Type Hints

```python
# ✅ Good: use type hints for public APIs
def train_model(
    data: pl.DataFrame,
    target_column: str,
    learning_rate: float = 0.01,
) -> dict[str, float]:
    """Train model and return metrics."""
    ...
```

#### 4. Error Handling

```python
# ✅ Good: informative error messages
if data.is_empty():
    raise ValueError(
        f"No data found for plant '{plant_id}' "
        f"in period {start_date} to {end_date}"
    )
```

---

## 🧪 Testing

### Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── fixtures/            # Test data files
├── test_readers.py
├── test_train.py
├── test_inference.py
└── test_utils.py
```

### Writing Tests

```python
def test_calculate_rmse_returns_expected_value():
    # Arrange: prepare data
    observed = np.array([1.0, 2.0, 3.0])
    predicted = np.array([1.1, 2.1, 3.1])

    # Act: execute function
    result = calculate_rmse(observed, predicted)

    # Assert: verify result
    assert result == pytest.approx(0.1, rel=1e-6)


def test_calculate_rmse_raises_on_mismatched_arrays():
    with pytest.raises(ValueError, match="same length"):
        calculate_rmse(np.array([1, 2]), np.array([1, 2, 3]))
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_train.py

# With coverage
pytest --cov=app --cov-report=html

# Verbose output
pytest -v
```

### Coverage Requirements

- New public functions must have tests
- Edge cases (None, empty, wrong types) should be tested
- Tests must be independent and reproducible

---

## 📝 Documentation

### Docstrings

All public functions and classes must have complete documentation:

```python
def train_plant(
    plant_id: str,
    data: pl.DataFrame,
    config: TrainConfig,
) -> TrainResult:
    """Train REST2 model parameters for a single plant.

    Optimizes mu0 and g parameters using BFGS minimization
    to minimize RMSE against measured irradiance data.

    Args:
        plant_id: Unique identifier for the plant.
        data: DataFrame with atmospheric parameters and measured values.
        config: Training configuration including time windows.

    Returns:
        TrainResult containing optimized parameters and metrics.

    Raises:
        ValueError: If plant_id not found in data.
        OptimizationError: If BFGS optimization fails to converge.

    Example:
        >>> result = train_plant("BAFJS7", data, config)
        >>> print(f"RMSE: {result.metrics['train']['RMSE']}")
    """
```

### Updating Documentation

```bash
# After changing public APIs, update relevant docs:
# - README.md for user-facing changes
# - METHODOLOGY.md for algorithm changes
# - TROUBLESHOOTING.md for new error cases
```

---

## 🔄 Pull Request Process

### Before Opening PR

1. **Sync with upstream**

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run local checks**

   ```bash
   ruff check .           # Linting passes
   ruff format --check .  # Formatting correct
   pytest                 # Tests pass
   mypy app/              # Type checking (if enabled)
   ```

3. **Organized commits**
   - Descriptive messages in English
   - One commit per logical change
   - Format: `type: short description`
     - `feat:` new functionality
     - `fix:` bug fix
     - `docs:` documentation
     - `test:` tests
     - `refactor:` refactoring

### PR Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation

## Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] `ruff check .` passes
- [ ] Code follows project standards

## Related Issues

Closes #123
```

### Review

- PRs require at least 1 approval
- CI must pass (tests, lint)
- Discussions must be resolved before merge

---

## 🏷️ Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: incompatible API changes
- **MINOR**: new backwards-compatible functionality
- **PATCH**: backwards-compatible bug fixes

Update `app/__init__.py` and `CHANGELOG.md` when releasing versions.

---

## ❓ Questions?

- Open a [Discussion](https://github.com/rjmalves/rest2-ons/discussions) for general questions
- Use [Issues](https://github.com/rjmalves/rest2-ons/issues) for bugs and features
- Consult existing documentation

Thank you for contributing! 🎉
