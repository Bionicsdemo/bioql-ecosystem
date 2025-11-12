# Codecov Setup Guide for BioQL Ecosystem

This guide explains how to set up and use Codecov for code coverage tracking in the BioQL project.

## Table of Contents

1. [Overview](#overview)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [GitHub Integration](#github-integration)
5. [Viewing Coverage Reports](#viewing-coverage-reports)
6. [Local Coverage Testing](#local-coverage-testing)
7. [Troubleshooting](#troubleshooting)

## Overview

Codecov is integrated into the BioQL CI/CD pipeline to track code coverage across the ecosystem. The configuration ensures:

- **Minimum coverage target**: 70% for the project
- **Patch coverage**: 70% for new code in pull requests
- **Automated reporting**: Coverage reports generated on every push and pull request
- **Multi-flag tracking**: Separate tracking for unit tests and integration tests

## Initial Setup

### Step 1: Create Codecov Account

1. Go to [codecov.io](https://codecov.io)
2. Sign in with your GitHub account
3. Authorize Codecov to access your repositories

### Step 2: Add BioQL Repository

1. In Codecov dashboard, click "Add new repository"
2. Find and select `Spectrix_BioQL` repository
3. Codecov will provide you with a repository upload token

### Step 3: Get Codecov Token

1. Navigate to your repository settings in Codecov
2. Go to **Settings > General**
3. Find the **Repository Upload Token** section
4. Copy the token (it looks like: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

**Important**: Keep this token secure. Never commit it to your repository.

## GitHub Integration

### Add Codecov Token to GitHub Secrets

1. Go to your GitHub repository: `https://github.com/YOUR_USERNAME/Spectrix_BioQL`
2. Navigate to **Settings > Secrets and variables > Actions**
3. Click **New repository secret**
4. Add the following secret:
   - **Name**: `CODECOV_TOKEN`
   - **Value**: Paste the token you copied from Codecov
5. Click **Add secret**

### Verify CI Integration

The CI workflow (`.github/workflows/ci.yml`) is already configured to upload coverage:

```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    files: ./coverage.xml
    flags: unittests
    name: codecov-${{ matrix.python-version }}
    fail_ci_if_error: false
    verbose: true
```

## Configuration

The `.codecov.yml` file in the repository root controls Codecov behavior:

### Coverage Targets

```yaml
coverage:
  status:
    project:
      default:
        target: 70%        # Overall project coverage target
        threshold: 2%      # Allow 2% drop before failing
    patch:
      default:
        target: 70%        # New code coverage target
        threshold: 5%      # Allow 5% variance for patches
```

### Included Paths

Coverage is tracked for these main components:
- `Spectrix_framework/` - Core BioQL framework
- `Quillow/` - Quantum error correction
- `QPHAROS/` - Quantum pharmacology
- `Server_bioql/` - BioQL server
- `BioQL_agents/` - Agent systems
- `BioQL_Lab_Notebook/` - Lab notebook functionality
- `bioql_quillow_docking/` - Molecular docking
- `Quantum_graph/` - Quantum graph structures

### Excluded Paths

The following are excluded from coverage:
- Test files (`tests/`, `*_test.py`, `test_*.py`)
- Documentation (`docs/`, `documentation/`)
- Generated files (`htmlcov/`, `__pycache__/`)
- Virtual environments (`venv/`, `.venv/`, `env/`)
- Configuration files (`setup.py`, `__init__.py`, `conftest.py`)
- Scripts and deployment files

### Coverage Flags

Two flags track different test types:

1. **unittests**: Core component unit tests
2. **integration**: Cross-component integration tests

## Viewing Coverage Reports

### On GitHub

1. **Pull Request Comments**: Codecov automatically comments on PRs with coverage changes
2. **Status Checks**: PR status checks show if coverage targets are met
3. **Commit Status**: Coverage badges appear on commits

### On Codecov Dashboard

1. Go to [codecov.io](https://codecov.io) and sign in
2. Select the `Spectrix_BioQL` repository
3. View detailed coverage information:
   - **Overview**: Overall coverage percentage and trends
   - **Commits**: Coverage for each commit
   - **Branches**: Coverage per branch
   - **Pulls**: Coverage changes in pull requests
   - **Files**: Line-by-line coverage for each file
   - **Flags**: Separate coverage for unit and integration tests

### Understanding Coverage Metrics

- **Project Coverage**: Overall percentage of lines covered
- **Patch Coverage**: Percentage of new/modified lines covered in a PR
- **Diff**: Coverage change compared to base branch
- **Complexity**: Code complexity metrics

### Coverage Badge

Add this badge to your README to display current coverage:

```markdown
[![codecov](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graph/badge.svg?token=YOUR_TOKEN)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
```

Replace `YOUR_USERNAME` with your GitHub username and `YOUR_TOKEN` with your badge token (found in Codecov settings).

## Local Coverage Testing

### Generate Coverage Locally

```bash
# Install dependencies
pip install pytest pytest-cov

# Run tests with coverage
pytest tests/unit -v --cov --cov-report=xml --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Run Complete Test Suite

```bash
# Run all tests with coverage
pytest tests/ -v --cov --cov-report=xml --cov-report=html --cov-report=term

# Run with coverage threshold check
pytest tests/ -v --cov --cov-fail-under=70
```

### Coverage by Module

```bash
# Coverage for specific module
pytest tests/unit/test_spectrix.py -v --cov=Spectrix_framework --cov-report=term-missing
```

## Troubleshooting

### Coverage Not Uploading

**Problem**: Coverage reports not appearing in Codecov

**Solutions**:
1. Verify `CODECOV_TOKEN` is set in GitHub Secrets
2. Check CI workflow logs for upload errors
3. Ensure `coverage.xml` file is generated
4. Verify Codecov action has correct token reference

```yaml
# Correct configuration
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    files: ./coverage.xml
```

### Coverage Failing CI

**Problem**: CI fails due to coverage below threshold

**Solutions**:
1. Check which files have low coverage: `pytest --cov --cov-report=term-missing`
2. Add tests for uncovered code paths
3. Adjust threshold in `.codecov.yml` if target is unrealistic
4. Use `fail_ci_if_error: false` for non-blocking coverage (already configured)

### Missing Coverage for Files

**Problem**: Some files not showing in coverage reports

**Solutions**:
1. Ensure files are imported in tests
2. Check if files are in excluded paths (`.codecov.yml` ignore list)
3. Verify files have `.py` extension
4. Check if `__init__.py` files are properly configured

### Token Issues

**Problem**: Invalid or expired token errors

**Solutions**:
1. Regenerate token in Codecov settings
2. Update `CODECOV_TOKEN` in GitHub Secrets
3. Verify token has no extra spaces or characters
4. Check token scope and permissions

### Multiple Python Versions

**Problem**: Duplicate or conflicting coverage from matrix builds

**Solutions**:
- Coverage from all Python versions (3.9, 3.10, 3.11) is uploaded separately
- Codecov automatically merges coverage from multiple uploads
- Each upload is named: `codecov-3.9`, `codecov-3.10`, `codecov-3.11`

### Pull Request Coverage

**Problem**: PR shows incorrect coverage changes

**Solutions**:
1. Ensure base branch has recent coverage data
2. Wait for all CI jobs to complete
3. Check if `require_base: false` in `.codecov.yml` (already configured)
4. Verify PR is targeting correct base branch (main or develop)

## Best Practices

### Writing Testable Code

1. **Keep functions small**: Easier to test and achieve full coverage
2. **Avoid complex conditionals**: Each branch needs testing
3. **Use dependency injection**: Makes mocking easier in tests
4. **Separate concerns**: Pure functions are easier to test

### Improving Coverage

1. **Test edge cases**: Not just happy paths
2. **Test error handling**: Exception paths matter
3. **Mock external dependencies**: Tests shouldn't require live services
4. **Use parametrized tests**: Cover multiple inputs efficiently

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert double(input) == expected
```

### Coverage Goals

- **Critical components**: Aim for 90%+ coverage
- **Business logic**: 80%+ coverage
- **Integration points**: 70%+ coverage
- **UI/Presentation**: 60%+ coverage (focus on logic)

### Maintaining Coverage

1. **Review coverage in PRs**: Check coverage comments before merging
2. **Add tests with new code**: Don't lower coverage percentage
3. **Regular coverage audits**: Identify untested critical paths
4. **Update exclusions**: Keep `.codecov.yml` ignore list current

## Additional Resources

- [Codecov Documentation](https://docs.codecov.com/)
- [Codecov GitHub Action](https://github.com/codecov/codecov-action)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Pytest Coverage Plugin](https://pytest-cov.readthedocs.io/)

## Support

For issues with Codecov integration:

1. Check [Codecov Community](https://community.codecov.com/)
2. Review [GitHub Actions Logs](https://github.com/YOUR_USERNAME/Spectrix_BioQL/actions)
3. Contact repository maintainers
4. Open an issue in the repository

---

**Last Updated**: 2025-11-12
**Codecov Version**: codecov-action@v3
**Minimum Coverage Target**: 70%
