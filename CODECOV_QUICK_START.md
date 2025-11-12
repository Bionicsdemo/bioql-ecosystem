# Codecov Quick Start Guide

Get Codecov up and running in 5 minutes!

## Prerequisites
- GitHub repository with CI/CD workflow
- pytest and pytest-cov installed
- Tests already configured

## Setup Steps

### 1. Get Codecov Token (2 minutes)
1. Go to https://codecov.io
2. Sign in with GitHub
3. Add `Spectrix_BioQL` repository
4. Copy the upload token from Settings > General

### 2. Add GitHub Secret (1 minute)
1. Go to your GitHub repo: Settings > Secrets and variables > Actions
2. Click "New repository secret"
3. Name: `CODECOV_TOKEN`
4. Value: [paste token from step 1]
5. Click "Add secret"

### 3. Push Changes (1 minute)
```bash
git add .codecov.yml .github/workflows/ci.yml
git commit -m "Add Codecov configuration"
git push origin main
```

### 4. Verify Setup (1 minute)
1. Go to GitHub Actions tab
2. Watch CI workflow run
3. Check for "Upload coverage to Codecov" step
4. Verify success in Codecov dashboard

## Quick Commands

### Run tests with coverage locally:
```bash
pytest tests/unit -v --cov --cov-report=xml --cov-report=html
```

### View coverage report:
```bash
open htmlcov/index.html  # macOS
```

### Check coverage threshold:
```bash
pytest tests/ -v --cov --cov-fail-under=70
```

## Configuration Summary

| Setting | Value |
|---------|-------|
| Coverage Target | 70% |
| Project Threshold | 2% |
| Patch Threshold | 5% |
| Python Versions | 3.9, 3.10, 3.11 |
| Flags | unittests, integration |

## Included Components
- Spectrix_framework/
- Quillow/
- QPHAROS/
- Server_bioql/
- BioQL_agents/
- BioQL_Lab_Notebook/
- bioql_quillow_docking/
- Quantum_graph/

## Excluded from Coverage
- tests/ (all test files)
- docs/ (documentation)
- htmlcov/ (coverage reports)
- __pycache__/ (Python cache)
- venv/, .venv/ (virtual environments)
- setup.py, __init__.py (config files)

## Add Badge to README

1. Get badge token from Codecov: Settings > Badge
2. Add to README.md:

```markdown
[![codecov](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graph/badge.svg?token=YOUR_TOKEN)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
```

3. Replace `YOUR_USERNAME` and `YOUR_TOKEN`

## Troubleshooting

### Coverage not uploading?
- Check CODECOV_TOKEN is set in GitHub Secrets
- Verify coverage.xml file exists after tests
- Check GitHub Actions logs for errors

### CI failing on coverage?
- Run tests locally: `pytest --cov --cov-fail-under=70`
- Check which files have low coverage
- Add more tests or adjust threshold in .codecov.yml

### Badge not showing?
- Get badge token from Codecov (different from upload token)
- Ensure badge URL matches your GitHub username
- Wait a few minutes after first push

## Next Steps

1. Review detailed setup: [CODECOV_SETUP.md](CODECOV_SETUP.md)
2. Add badge to README: [README_BADGES.md](README_BADGES.md)
3. Check configuration: [CODECOV_CONFIGURATION_SUMMARY.md](CODECOV_CONFIGURATION_SUMMARY.md)
4. Monitor coverage in Codecov dashboard
5. Set up PR comments and status checks

## Support

- Full Documentation: [CODECOV_SETUP.md](CODECOV_SETUP.md)
- Badge Guide: [README_BADGES.md](README_BADGES.md)
- Codecov Docs: https://docs.codecov.com/
- Coverage.py: https://coverage.readthedocs.io/

---

Configuration complete! Start pushing code to see coverage tracking in action.
