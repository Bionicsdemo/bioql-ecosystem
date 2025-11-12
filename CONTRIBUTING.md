# Contributing to BioQL Ecosystem

Thank you for your interest in contributing to the BioQL Ecosystem! This guide will help you set up your development environment and understand our development workflow.

## Table of Contents

- [Development Setup](#development-setup)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Code Style](#code-style)
- [Testing](#testing)
- [Security](#security)
- [Submitting Changes](#submitting-changes)
- [Troubleshooting](#troubleshooting)

## Development Setup

### Prerequisites

- Python 3.9 or later
- pip or conda for package management
- Git for version control

### Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/SpectrixRD/Spectrix_BioQL.git
cd Spectrix_BioQL
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

4. Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

## Pre-commit Hooks

Pre-commit hooks automatically check and fix issues before you commit code. They run the following checks:

### Automatic Fixes

The following hooks will automatically fix issues:

- **black**: Formats Python code to PEP 8 standards
- **isort**: Organizes and sorts imports
- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with a newline
- **mixed-line-ending**: Normalizes line endings to LF

### Verification Hooks

These hooks check but don't automatically fix:

- **flake8**: Style and error checking
- **mypy**: Static type checking
- **pytest**: Unit tests (fast tests only, excludes `@pytest.mark.slow`)
- **bandit**: Security vulnerability scanning
- **safety**: Dependency vulnerability checking
- **check-yaml**: YAML syntax validation
- **check-json**: JSON syntax validation

### Running Hooks Manually

Run all hooks on all files:
```bash
pre-commit run --all-files
```

Run specific hook:
```bash
pre-commit run black --all-files
```

Update hooks to latest versions:
```bash
pre-commit autoupdate
```

## Code Style

We follow PEP 8 and use the following tools for code quality:

### Python Formatting

Code is formatted with **black** (100 character line limit):
```bash
black .
```

### Import Ordering

Imports are sorted with **isort** (black-compatible profile):
```bash
isort --profile black .
```

### Linting

Check code style with **flake8**:
```bash
flake8 .
```

### Type Checking

Check type hints with **mypy**:
```bash
mypy Spectrix_framework Quillow QPHAROS
```

### Configuration

Code style configuration is in `.pre-commit-config.yaml`:
- Black: 100 character line limit
- isort: Black-compatible profile
- flake8: Excludes venv, env, node_modules, docs
- mypy: Ignores missing imports, no implicit optional

## Testing

### Running Tests

Run all unit tests:
```bash
pytest tests/unit -v
```

Run specific test file:
```bash
pytest tests/unit/test_specific.py -v
```

Run tests with coverage:
```bash
pytest tests/unit --cov=Spectrix_framework --cov=Quillow --cov=QPHAROS --cov-report=html
```

View HTML coverage report:
```bash
open htmlcov/index.html  # Or use your preferred browser
```

### Test Organization

- **Unit tests**: `tests/unit/` - Fast, isolated tests (should pass in pre-commit)
- **Integration tests**: `tests/integration/` - Tests with external dependencies
- **E2E tests**: `tests/e2e/` - End-to-end tests

### Test Markers

Mark tests with pytest markers:

```python
import pytest

@pytest.mark.slow
def test_slow_operation():
    """This test takes > 5 seconds"""
    pass

@pytest.mark.integration
def test_with_external_service():
    """Integration test"""
    pass

@pytest.mark.requires_ibm
def test_ibm_quantum():
    """Requires IBM Quantum access"""
    pass
```

### Coverage Requirements

Pre-commit hooks enforce a **minimum 70% code coverage** for unit tests. This ensures code quality and reliability.

If coverage drops below 70%:
1. Write additional unit tests for untested code
2. Use `pytest --cov-report=html` to identify gaps
3. Check the `htmlcov/index.html` report

## Security

### Dependency Security

We check dependencies for known vulnerabilities with **safety**:
```bash
safety check
```

### Code Security

We scan code for security issues with **bandit**:
```bash
bandit -r Spectrix_framework Quillow QPHAROS
```

### Secrets Management

Never commit sensitive information:
- API keys
- Passwords
- Database credentials
- Private tokens

Use `.env` files (excluded from git) or environment variables.

## Submitting Changes

### Workflow

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make changes and commit (pre-commit hooks will run automatically):
```bash
git add .
git commit -m "Descriptive commit message"
```

3. If pre-commit hooks fail:
   - Review the error messages
   - Make fixes (many are automatic)
   - Stage and commit again
   - See [Troubleshooting](#troubleshooting) for help

4. Push branch and create pull request:
```bash
git push origin feature/your-feature-name
```

### Commit Messages

Write clear, descriptive commit messages:

```
Brief summary (50 characters or less)

More detailed explanation of the changes. Explain the why, not just the what.
Keep lines under 72 characters.

- Bullet point for additional context
- Another important detail
```

### Pull Request Checklist

Before submitting a PR:

- [ ] Code passes all pre-commit hooks
- [ ] Unit tests pass locally: `pytest tests/unit -v`
- [ ] Code coverage doesn't drop below 70%
- [ ] Type hints are correct: `mypy Spectrix_framework Quillow QPHAROS`
- [ ] Security scan passes: `bandit -r .`
- [ ] Commit messages are clear and descriptive
- [ ] No hardcoded secrets or credentials
- [ ] Documentation is updated if needed

## Troubleshooting

### Pre-commit Hook Failures

#### Black formatting issues

Auto-fix with:
```bash
black .
```

Then stage and commit changes.

#### isort import issues

Auto-fix with:
```bash
isort --profile black .
```

Then stage and commit changes.

#### Flake8 errors

Review the error output:
```bash
flake8 .
```

Common issues:
- Line too long: Use black to format
- Unused imports: Remove or use `# noqa: F401`
- Undefined names: Import the module

#### Mypy type errors

Review type hints in your code:
```bash
mypy Spectrix_framework Quillow QPHAROS
```

Add type hints or use `# type: ignore` when appropriate.

#### Test failures

Run tests locally and fix:
```bash
pytest tests/unit -v
```

Skip slow tests to speed up pre-commit:
```bash
pytest tests/unit -m "not slow" -v
```

#### Coverage too low

Run with coverage report:
```bash
pytest tests/unit --cov=Spectrix_framework --cov=Quillow --cov=QPHAROS --cov-report=html
open htmlcov/index.html
```

Write tests for uncovered lines.

#### Bandit security warnings

Review the warning:
```bash
bandit -r Spectrix_framework Quillow QPHAROS
```

Fix security issues or suppress false positives:
```python
def risky_function():
    eval(input())  # noqa: S307
```

### Disabling Hooks Temporarily

Skip pre-commit hooks (NOT RECOMMENDED):
```bash
git commit --no-verify
```

Use only when absolutely necessary, then run hooks manually:
```bash
pre-commit run --all-files
```

### Debugging Hook Issues

Run a specific hook with debug output:
```bash
pre-commit run mypy --all-files -v
```

Check hook configuration:
```bash
cat .pre-commit-config.yaml
```

### Common Issues

**Issue**: `ModuleNotFoundError` when running pytest

**Solution**: Install all dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install pytest pytest-cov
```

---

**Issue**: Pre-commit hooks slow on large commits

**Solution**: Hooks run in parallel by default. For very large changes, you can:
1. Commit in smaller chunks
2. Run `pre-commit run --all-files` on non-commit stages

---

**Issue**: Type checking fails with "has no attribute"

**Solution**: Add type stubs or use `# type: ignore`:
```python
from some_library import function
result = function()  # type: ignore
```

## Getting Help

- Check existing [issues](https://github.com/SpectrixRD/Spectrix_BioQL/issues)
- Review [documentation](https://github.com/SpectrixRD/Spectrix_BioQL/tree/main/docs)
- Ask questions in pull requests
- Create a new issue for bugs or suggestions

## Code of Conduct

Be respectful and inclusive. We're all here to improve the BioQL Ecosystem together!

---

**Last Updated**: November 2024
**Python Version**: 3.9+
**License**: Apache License 2.0
