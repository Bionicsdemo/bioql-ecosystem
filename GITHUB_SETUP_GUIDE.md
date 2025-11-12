# GitHub Setup Guide for BioQL Ecosystem

**Version:** 1.0
**Last Updated:** November 2025
**Project:** BioQL Ecosystem - Quantum Computing for Drug Discovery
**Current Status:** No remote configured, CI/CD workflow ready

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Part 1: Initial GitHub Setup](#part-1-initial-github-setup)
3. [Part 2: Configure Git Remote](#part-2-configure-git-remote)
4. [Part 3: Activate CI/CD](#part-3-activate-cicd)
5. [Part 4: Set Up GitHub Features](#part-4-set-up-github-features)
6. [Part 5: Team Setup](#part-5-team-setup)
7. [Part 6: Integration with External Services](#part-6-integration-with-external-services)
8. [Troubleshooting](#troubleshooting)
9. [Quick Reference Commands](#quick-reference-commands)

---

## 1. Prerequisites

Before starting, ensure you have:

- [ ] GitHub account (personal or organization)
- [ ] Git installed and configured locally
- [ ] Repository admin/owner permissions
- [ ] IBM Quantum token (for CI/CD)
- [ ] Terminal/command line access

### Check Your Git Configuration

```bash
# Verify Git is installed
git --version

# Check current configuration
git config --list

# Set your identity (if not already set)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### Current Project Status

```bash
cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL

# Check current branch
git branch
# Output: * master

# Check remote status
git remote -v
# Output: (empty - no remote configured)

# Check repository status
git status
```

---

## Part 1: Initial GitHub Setup

### Step 1.1: Decide on Organization vs Personal Repository

**Option A: Organization Repository (Recommended for Enterprise)**

**Advantages:**
- Professional appearance
- Team management features
- Unlimited collaborators on public repos
- Better for company/project branding
- Advanced security features

**When to use:** Multi-person teams, enterprise projects, open-source community projects

**Option B: Personal Repository**

**Advantages:**
- Quick setup
- Good for individual projects
- Can transfer to organization later

**When to use:** Solo developers, personal projects, proof of concepts

### Step 1.2: Create GitHub Organization (Optional)

If choosing Organization:

1. Go to [https://github.com/organizations/plan](https://github.com/organizations/plan)
2. Click "Create organization"
3. Choose plan:
   - **Free:** Unlimited public/private repos, 2,000 CI/CD minutes/month
   - **Team ($4/user/month):** 3,000 CI/CD minutes, required reviewers, code owners
   - **Enterprise:** Contact sales for advanced features
4. Fill in organization details:
   - **Organization name:** `bioql-ecosystem` or `spectrix-bioql`
   - **Contact email:** Your primary email
   - **This organization belongs to:** Choose appropriate option
5. Invite initial members (can do later)
6. Complete setup wizard

**Screenshot Reference:** `github-org-creation.png`

### Step 1.3: Create Main Repository

#### Via GitHub Web Interface:

1. Navigate to:
   - Organization: `https://github.com/organizations/YOUR-ORG/repositories/new`
   - Personal: `https://github.com/new`

2. Configure repository settings:
   ```
   Repository name: bioql-ecosystem
   Description: Quantum Computing Platform for Drug Discovery and Bioinformatics

   Visibility:
     ○ Public (recommended for open-source)
     ○ Private (for proprietary code)

   Initialize repository:
     ☐ DO NOT check "Add a README file"
     ☐ DO NOT add .gitignore
     ☐ DO NOT add license

   (We already have these files in the local repository)
   ```

3. Click "Create repository"

#### Via GitHub CLI (Alternative):

```bash
# Install GitHub CLI if not already installed
# macOS:
brew install gh

# Login to GitHub
gh auth login

# Create organization repository
gh repo create bioql-ecosystem/bioql-ecosystem --public --description "Quantum Computing Platform for Drug Discovery and Bioinformatics"

# OR create personal repository
gh repo create bioql-ecosystem --public --description "Quantum Computing Platform for Drug Discovery and Bioinformatics"
```

**Screenshot Reference:** `github-repo-creation.png`

### Step 1.4: Configure Repository Settings

Navigate to repository settings: `https://github.com/YOUR-ORG/bioql-ecosystem/settings`

#### General Settings

1. **Features** - Enable/disable features:
   ```
   ☑ Wikis (for documentation)
   ☑ Issues (for bug tracking)
   ☑ Sponsorships (if accepting donations)
   ☑ Projects (for project management)
   ☑ Preserve this repository (archive important data)
   ☑ Discussions (for community Q&A)
   ```

2. **Pull Requests:**
   ```
   ☑ Allow squash merging
   ☑ Allow merge commits
   ☑ Allow rebase merging
   ☑ Always suggest updating pull request branches
   ☑ Allow auto-merge
   ☑ Automatically delete head branches
   ```

3. **Archives:**
   ```
   ☑ Include Git LFS objects in archives
   ```

**Screenshot Reference:** `github-repo-settings.png`

### Step 1.5: Set Up Branch Protection Rules

Critical for maintaining code quality and preventing direct commits to main branches.

1. Go to: Settings → Branches → Add rule
2. Branch name pattern: `main`
3. Configure protection rules:

```yaml
Branch Protection Settings:

Protect matching branches:
  ☑ Require a pull request before merging
    ☑ Require approvals: 1 (or more for sensitive code)
    ☑ Dismiss stale pull request approvals when new commits are pushed
    ☑ Require review from Code Owners

  ☑ Require status checks to pass before merging
    ☑ Require branches to be up to date before merging
    Required status checks:
      - lint
      - test (Python 3.9)
      - test (Python 3.10)
      - test (Python 3.11)
      - build-packages
      - security-scan

  ☑ Require conversation resolution before merging

  ☑ Require signed commits (optional but recommended)

  ☑ Require linear history

  ☑ Include administrators (enforce rules for admins too)

  ☐ Allow force pushes (keep disabled)

  ☐ Allow deletions (keep disabled)
```

4. Click "Create" or "Save changes"

**Repeat for `develop` branch** with similar settings (possibly less strict).

**Screenshot Reference:** `github-branch-protection.png`

### Step 1.6: Set Up Repository Topics

Add topics to help others discover your repository:

1. Go to repository main page
2. Click gear icon next to "About"
3. Add topics:
   ```
   quantum-computing
   drug-discovery
   bioinformatics
   qiskit
   ibm-quantum
   computational-biology
   python
   pharmaceutical-research
   quantum-algorithms
   molecular-docking
   bioql
   ```

**Screenshot Reference:** `github-topics.png`

---

## Part 2: Configure Git Remote

Now connect your local repository to the GitHub remote.

### Step 2.1: Get Repository URL

From your GitHub repository page, click the green "Code" button and copy the URL:

- **HTTPS:** `https://github.com/YOUR-USERNAME/bioql-ecosystem.git`
- **SSH:** `git@github.com:YOUR-USERNAME/bioql-ecosystem.git`

**SSH is recommended** for better security and no password prompts.

#### Set Up SSH Keys (if using SSH):

```bash
# Check for existing SSH keys
ls -al ~/.ssh

# Generate new SSH key (if needed)
ssh-keygen -t ed25519 -C "your.email@example.com"

# Start SSH agent
eval "$(ssh-agent -s)"

# Add SSH key to agent
ssh-add ~/.ssh/id_ed25519

# Copy public key to clipboard
# macOS:
pbcopy < ~/.ssh/id_ed25519.pub
# Linux:
cat ~/.ssh/id_ed25519.pub

# Add key to GitHub:
# 1. Go to GitHub Settings → SSH and GPG keys
# 2. Click "New SSH key"
# 3. Paste key and save
```

### Step 2.2: Add Remote to Local Repository

```bash
# Navigate to project directory
cd /Users/heinzjungbluth/Desktop/Spectrix_BioQL

# Add remote (choose HTTPS or SSH)
# Option 1: HTTPS
git remote add origin https://github.com/YOUR-USERNAME/bioql-ecosystem.git

# Option 2: SSH (recommended)
git remote add origin git@github.com:YOUR-USERNAME/bioql-ecosystem.git

# Verify remote was added
git remote -v
# Output:
# origin  git@github.com:YOUR-USERNAME/bioql-ecosystem.git (fetch)
# origin  git@github.com:YOUR-USERNAME/bioql-ecosystem.git (push)
```

### Step 2.3: Rename Branch (Optional)

GitHub now uses `main` as the default branch name. Your local repo uses `master`.

**Option A: Keep `master`**
```bash
# No action needed, push as-is
git push -u origin master
```

**Option B: Rename to `main` (recommended)**
```bash
# Rename local branch
git branch -M main

# Verify branch name
git branch
# Output: * main
```

### Step 2.4: Push Code to GitHub

```bash
# Push code (first time)
# If you kept 'master':
git push -u origin master

# If you renamed to 'main':
git push -u origin main

# Enter credentials if using HTTPS
# (No prompt if using SSH keys)
```

**Expected output:**
```
Enumerating objects: 1523, done.
Counting objects: 100% (1523/1523), done.
Delta compression using up to 8 threads
Compressing objects: 100% (845/845), done.
Writing objects: 100% (1523/1523), 2.45 MiB | 3.21 MiB/s, done.
Total 1523 (delta 612), reused 1402 (delta 534)
remote: Resolving deltas: 100% (612/612), done.
To github.com:YOUR-USERNAME/bioql-ecosystem.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

### Step 2.5: Verify Upload

```bash
# Check remote tracking
git branch -vv

# Verify all files are on GitHub
# Visit: https://github.com/YOUR-USERNAME/bioql-ecosystem
```

**Screenshot Reference:** `github-first-push.png`

### Step 2.6: Create `develop` Branch (Optional)

For GitFlow workflow:

```bash
# Create develop branch
git checkout -b develop

# Push to remote
git push -u origin develop

# Switch back to main
git checkout main
```

---

## Part 3: Activate CI/CD

Your project already has a CI/CD workflow at `.github/workflows/ci.yml`. Let's activate it.

### Step 3.1: Understanding the Existing Workflow

Your workflow includes:

1. **Lint Job:** Code quality checks (black, flake8, isort)
2. **Test Job:** Unit tests across Python 3.9, 3.10, 3.11
3. **Build Packages:** Builds distribution packages
4. **Security Scan:** Bandit and Safety checks
5. **Integration Tests:** End-to-end testing

**File location:** `/Users/heinzjungbluth/Desktop/Spectrix_BioQL/.github/workflows/ci.yml`

### Step 3.2: Configure GitHub Secrets

GitHub Actions needs secrets for IBM Quantum and other services.

#### Add Secrets:

1. Go to: Settings → Secrets and variables → Actions
2. Click "New repository secret"

**Required Secrets:**

```yaml
Name: IBM_QUANTUM_TOKEN
Value: YOUR_IBM_QUANTUM_API_TOKEN
Description: IBM Quantum Platform API token for quantum circuit execution

---

Name: CODECOV_TOKEN (if using Codecov)
Value: YOUR_CODECOV_TOKEN
Description: Token for uploading code coverage reports

---

Name: SENTRY_DSN (if using Sentry)
Value: YOUR_SENTRY_DSN
Description: Sentry DSN for error tracking

---

Name: PYPI_TOKEN (for package publishing)
Value: YOUR_PYPI_TOKEN
Description: PyPI API token for publishing packages
```

#### Get IBM Quantum Token:

```bash
# 1. Log in to IBM Quantum Platform
#    https://quantum-computing.ibm.com/

# 2. Go to Account → API Token
# 3. Copy token
# 4. Add to GitHub Secrets as IBM_QUANTUM_TOKEN
```

**Screenshot Reference:** `github-secrets-config.png`

### Step 3.3: Configure Environment Variables (Optional)

For non-sensitive configuration:

1. Go to: Settings → Secrets and variables → Actions → Variables
2. Add variables:

```yaml
Name: PYTHON_VERSION
Value: 3.10

Name: NODE_VERSION
Value: 18

Name: ENABLE_QUANTUM_TESTS
Value: true
```

### Step 3.4: Test Workflow Manually

Trigger a workflow run to verify everything works:

```bash
# Make a small change and push
echo "# GitHub Actions enabled" >> README.md
git add README.md
git commit -m "test: Trigger CI/CD workflow"
git push

# OR trigger via GitHub UI:
# Go to Actions tab → Select workflow → Run workflow
```

### Step 3.5: View Workflow Runs

1. Navigate to: `https://github.com/YOUR-USERNAME/bioql-ecosystem/actions`
2. Click on the latest workflow run
3. Expand jobs to see details
4. Check logs for any errors

**Workflow should show:**
- Green checkmark for successful jobs
- Red X for failed jobs (fix issues and re-run)

**Screenshot Reference:** `github-actions-run.png`

### Step 3.6: Add Status Badge to README

Show CI/CD status in your README:

```markdown
# Add to top of README.md

[![CI/CD Status](https://github.com/YOUR-USERNAME/bioql-ecosystem/workflows/BioQL%20Ecosystem%20CI%2FCD/badge.svg)](https://github.com/YOUR-USERNAME/bioql-ecosystem/actions)
[![codecov](https://codecov.io/gh/YOUR-USERNAME/bioql-ecosystem/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR-USERNAME/bioql-ecosystem)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
```

### Step 3.7: Configure Codecov Integration

1. Go to [https://codecov.io](https://codecov.io)
2. Sign in with GitHub
3. Add repository
4. Copy Codecov token
5. Add to GitHub Secrets as `CODECOV_TOKEN`
6. Workflow already configured to upload coverage

**Screenshot Reference:** `codecov-integration.png`

---

## Part 4: Set Up GitHub Features

### 4.1: Issue Templates

Create templates for consistent bug reports and feature requests.

#### Create Issue Templates Directory:

```bash
mkdir -p .github/ISSUE_TEMPLATE
```

#### Bug Report Template:

Create `.github/ISSUE_TEMPLATE/bug_report.md`:

```markdown
---
name: Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

## Bug Description
A clear and concise description of the bug.

## To Reproduce
Steps to reproduce the behavior:
1. Import module '...'
2. Execute code '...'
3. See error

## Expected Behavior
What you expected to happen.

## Actual Behavior
What actually happened.

## Code Sample
```python
# Minimal code to reproduce
from bioql import ...
```

## Environment
- **BioQL Version:** [e.g., 6.0.1]
- **Python Version:** [e.g., 3.10]
- **OS:** [e.g., macOS 13.0]
- **Quantum Backend:** [e.g., ibm_brisbane]

## Error Message
```
Paste full error traceback here
```

## Additional Context
Any other relevant information.

## Screenshots
If applicable, add screenshots.
```

#### Feature Request Template:

Create `.github/ISSUE_TEMPLATE/feature_request.md`:

```markdown
---
name: Feature Request
about: Suggest a new feature or enhancement
title: '[FEATURE] '
labels: enhancement
assignees: ''
---

## Feature Description
Clear description of the proposed feature.

## Motivation
Why is this feature needed? What problem does it solve?

## Proposed Solution
How should this feature work?

## Example Usage
```python
# Example of how the feature would be used
from bioql import new_feature
result = new_feature.do_something()
```

## Alternatives Considered
Other approaches you've considered.

## Additional Context
Any other relevant information, mockups, or references.

## Scope
- [ ] Core framework
- [ ] Quillow docking
- [ ] QPHAROS error correction
- [ ] Documentation
- [ ] Tests
```

#### Question Template:

Create `.github/ISSUE_TEMPLATE/question.md`:

```markdown
---
name: Question
about: Ask a question about BioQL
title: '[QUESTION] '
labels: question
assignees: ''
---

## Question
Your question here.

## Context
What are you trying to achieve?

## What I've Tried
Research or solutions you've already attempted.

## Related Documentation
Links to relevant documentation you've consulted.
```

#### Commit Templates:

```bash
# Add to repository
git add .github/ISSUE_TEMPLATE/
git commit -m "docs: Add issue templates"
git push
```

**Screenshot Reference:** `github-issue-templates.png`

### 4.2: Pull Request Template

Create `.github/pull_request_template.md`:

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Test improvements

## Related Issues
Closes #(issue_number)

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
Describe the tests you ran:
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing
- [ ] Quantum circuit validation

### Test Commands
```bash
pytest tests/unit -v
pytest tests/integration -v
```

## Code Coverage
- [ ] Code coverage maintained or improved
- [ ] Coverage report: XX%

## Documentation
- [ ] Updated docstrings
- [ ] Updated README/guides
- [ ] Added/updated examples
- [ ] Updated CHANGELOG

## Checklist
- [ ] Code follows project style guidelines (black, flake8, isort)
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings introduced
- [ ] Tests pass locally
- [ ] Dependent changes merged

## Screenshots (if applicable)
Add screenshots for UI changes.

## Additional Notes
Any additional context or notes for reviewers.
```

```bash
git add .github/pull_request_template.md
git commit -m "docs: Add pull request template"
git push
```

### 4.3: Code Owners

Define who reviews specific parts of the codebase.

Create `.github/CODEOWNERS`:

```plaintext
# BioQL Ecosystem Code Owners
# These owners will be requested for review when PRs modify these files

# Default owner for everything
* @YOUR-USERNAME

# Core framework
/Spectrix_framework/ @YOUR-USERNAME @quantum-team
/Spectrix_framework/bioql/quantum/ @quantum-lead

# Docking module
/Quillow/ @YOUR-USERNAME @docking-team
/bioql_quillow_docking/ @docking-lead

# Error correction
/QPHAROS/ @YOUR-USERNAME @error-correction-team

# Documentation
/docs/ @YOUR-USERNAME @docs-team
*.md @docs-team

# CI/CD and workflows
/.github/ @YOUR-USERNAME @devops-team
/.github/workflows/ @devops-lead

# Tests
/tests/ @YOUR-USERNAME @qa-team

# Configuration files
requirements.txt @YOUR-USERNAME @devops-team
pyproject.toml @YOUR-USERNAME
setup.py @YOUR-USERNAME
```

```bash
git add .github/CODEOWNERS
git commit -m "docs: Add CODEOWNERS file"
git push
```

**Note:** Code owners must have write access to the repository.

### 4.4: GitHub Pages for Documentation

Host your documentation on GitHub Pages.

#### Option A: Using docs/ folder

1. Go to: Settings → Pages
2. Configure:
   ```
   Source: Deploy from a branch
   Branch: main
   Folder: /docs
   ```
3. Click Save
4. Site will be published at: `https://YOUR-USERNAME.github.io/bioql-ecosystem/`

#### Option B: Using gh-pages branch

```bash
# Install required packages
pip install sphinx sphinx-rtd-theme

# Build documentation
cd docs
make html

# Install ghp-import
pip install ghp-import

# Deploy to gh-pages branch
ghp-import -n -p -f _build/html
```

#### Option C: Using MkDocs

```bash
# Install MkDocs
pip install mkdocs mkdocs-material

# Create mkdocs.yml configuration
cat > mkdocs.yml << 'EOF'
site_name: BioQL Ecosystem Documentation
site_url: https://YOUR-USERNAME.github.io/bioql-ecosystem
theme:
  name: material
  palette:
    primary: indigo
    accent: indigo
nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - User Guide: user-guide.md
  - API Reference: api-reference.md
  - Examples: examples.md
EOF

# Deploy
mkdocs gh-deploy
```

**Screenshot Reference:** `github-pages-config.png`

### 4.5: GitHub Packages for Python Packages

Publish your Python packages to GitHub Packages.

#### Configure Package Publishing:

Create `.github/workflows/publish.yml`:

```yaml
name: Publish Python Packages

on:
  release:
    types: [created]

jobs:
  publish-github:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build packages
        run: |
          cd Spectrix_framework
          python -m build

      - name: Publish to GitHub Packages
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.GITHUB_TOKEN }}
        run: |
          twine upload --repository-url https://upload.pypi.org/legacy/ Spectrix_framework/dist/*

  publish-pypi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build packages
        run: |
          cd Spectrix_framework
          python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: |
          twine upload Spectrix_framework/dist/*
```

### 4.6: GitHub Releases

Create releases for version tags.

#### Create a Release:

```bash
# Tag a version
git tag -a v6.0.1 -m "BioQL Framework v6.0.1"
git push origin v6.0.1

# OR use GitHub CLI
gh release create v6.0.1 \
  --title "BioQL v6.0.1" \
  --notes "Release notes here" \
  Spectrix_framework/dist/*
```

#### Via GitHub UI:

1. Go to: Releases → Draft a new release
2. Fill in:
   ```
   Tag version: v6.0.1
   Release title: BioQL Framework v6.0.1
   Description:
     ## What's New
     - Feature 1
     - Feature 2

     ## Bug Fixes
     - Fix 1
     - Fix 2

     ## Breaking Changes
     - Change 1

   Attach binaries: (drag and drop .whl and .tar.gz files)
   ```
3. Click "Publish release"

**Screenshot Reference:** `github-releases.png`

---

## Part 5: Team Setup

### 5.1: Add Collaborators

#### For Organization Repository:

1. Go to: Settings → Collaborators and teams
2. Click "Add teams" or "Add people"
3. Search for GitHub username or email
4. Select permission level:
   - **Read:** View and clone only
   - **Triage:** Read + manage issues/PRs
   - **Write:** Triage + push to branches
   - **Maintain:** Write + manage settings (no deletion)
   - **Admin:** Full access

#### For Personal Repository:

1. Go to: Settings → Collaborators
2. Click "Add people"
3. Search for GitHub username
4. Send invitation

### 5.2: Set Up Teams (Organization Only)

1. Go to organization settings: `https://github.com/orgs/YOUR-ORG/teams`
2. Click "New team"

**Example Teams:**

```yaml
Team: Core Developers
Description: Core framework maintainers
Privacy: Visible
Members: @user1, @user2, @user3
Repositories: bioql-ecosystem (Maintain)

---

Team: Quantum Research
Description: Quantum algorithm researchers
Privacy: Visible
Members: @user4, @user5
Repositories: bioql-ecosystem (Write)

---

Team: Documentation
Description: Documentation team
Privacy: Visible
Members: @user6, @user7
Repositories: bioql-ecosystem (Write)
Repository access: docs/ folder only

---

Team: Quality Assurance
Description: Testing and QA team
Privacy: Visible
Members: @user8, @user9
Repositories: bioql-ecosystem (Triage)
```

### 5.3: Configure Permissions

#### Repository Permissions:

1. Settings → Collaborators and teams
2. Configure base permissions:
   ```
   Base permissions: Read
   (Requires explicit permission for write access)
   ```

#### Team Permissions:

For each team, configure:
- Repository access level
- Branch restrictions
- Protected branches access

### 5.4: Set Up Code Review Requirements

1. Settings → Branches → Edit protection rule
2. Configure:
   ```
   Required approvals: 2 (for critical branches)

   Required reviewers from:
     - Code Owners
     - Team: Core Developers

   Dismiss stale reviews: Yes

   Require review from Code Owners: Yes
   ```

**Screenshot Reference:** `github-team-setup.png`

---

## Part 6: Integration with External Services

### 6.1: Codecov for Code Coverage

#### Setup Steps:

1. **Sign up for Codecov:**
   - Go to [https://codecov.io](https://codecov.io)
   - Sign in with GitHub
   - Authorize Codecov

2. **Add Repository:**
   - Click "Add repository"
   - Select `bioql-ecosystem`
   - Copy repository token

3. **Add Token to GitHub:**
   ```
   GitHub Settings → Secrets → New secret
   Name: CODECOV_TOKEN
   Value: (paste token)
   ```

4. **Verify Integration:**
   - Your CI workflow already uploads coverage
   - Push a commit and check Codecov dashboard
   - Visit: `https://codecov.io/gh/YOUR-USERNAME/bioql-ecosystem`

5. **Configure Codecov:**

   Create `codecov.yml` in repository root:

   ```yaml
   coverage:
     status:
       project:
         default:
           target: 80%
           threshold: 2%
       patch:
         default:
           target: 70%

   comment:
     layout: "reach, diff, flags, files"
     behavior: default
     require_changes: false

   ignore:
     - "tests/"
     - "docs/"
     - "**/__pycache__/"
     - "*.pyc"
   ```

6. **Add Badge to README:**
   ```markdown
   [![codecov](https://codecov.io/gh/YOUR-USERNAME/bioql-ecosystem/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR-USERNAME/bioql-ecosystem)
   ```

**Screenshot Reference:** `codecov-dashboard.png`

### 6.2: Sentry for Error Tracking

#### Setup Steps:

1. **Create Sentry Account:**
   - Go to [https://sentry.io](https://sentry.io)
   - Sign up (free tier available)
   - Create new project: Python

2. **Get DSN:**
   - Copy DSN from project settings
   - Format: `https://xxxxx@sentry.io/xxxxx`

3. **Add to GitHub Secrets:**
   ```
   Name: SENTRY_DSN
   Value: (paste DSN)
   ```

4. **Integrate into Code:**

   Add to `Spectrix_framework/bioql/__init__.py`:

   ```python
   import os
   import sentry_sdk

   # Initialize Sentry
   sentry_dsn = os.getenv("SENTRY_DSN")
   if sentry_dsn:
       sentry_sdk.init(
           dsn=sentry_dsn,
           environment=os.getenv("ENVIRONMENT", "production"),
           traces_sample_rate=1.0,
           release=f"bioql@{__version__}",
       )
   ```

5. **Add to Requirements:**
   ```bash
   echo "sentry-sdk>=1.40.0" >> requirements.txt
   ```

6. **Test Error Tracking:**
   ```python
   # Test error
   from sentry_sdk import capture_exception

   try:
       1 / 0
   except Exception as e:
       capture_exception(e)
   ```

**Screenshot Reference:** `sentry-integration.png`

### 6.3: ReadTheDocs for Documentation

#### Setup Steps:

1. **Sign up for ReadTheDocs:**
   - Go to [https://readthedocs.org](https://readthedocs.org)
   - Sign in with GitHub
   - Import a Project

2. **Import Repository:**
   - Click "Import a Project"
   - Select `bioql-ecosystem`
   - Click "Next"

3. **Configure Project:**
   ```
   Name: BioQL Ecosystem
   Repository URL: (auto-filled)
   Default branch: main
   Documentation type: Sphinx
   Language: English
   Programming language: Python
   ```

4. **Create `.readthedocs.yml`:**

   ```yaml
   version: 2

   build:
     os: ubuntu-22.04
     tools:
       python: "3.10"

   sphinx:
     configuration: docs/conf.py
     builder: html
     fail_on_warning: false

   python:
     install:
       - requirements: requirements.txt
       - requirements: docs/requirements.txt
       - method: pip
         path: Spectrix_framework

   formats:
     - pdf
     - epub
   ```

5. **Create `docs/requirements.txt`:**
   ```
   sphinx>=5.0
   sphinx-rtd-theme>=1.2.0
   sphinx-autodoc-typehints>=1.23.0
   myst-parser>=1.0.0
   ```

6. **Build Documentation:**
   - ReadTheDocs will build automatically
   - Visit: `https://bioql-ecosystem.readthedocs.io`

7. **Add Badge:**
   ```markdown
   [![Documentation Status](https://readthedocs.org/projects/bioql-ecosystem/badge/?version=latest)](https://bioql-ecosystem.readthedocs.io/en/latest/)
   ```

**Screenshot Reference:** `readthedocs-config.png`

### 6.4: Additional Integrations

#### Dependabot for Dependency Updates

1. Create `.github/dependabot.yml`:

   ```yaml
   version: 2
   updates:
     - package-ecosystem: "pip"
       directory: "/"
       schedule:
         interval: "weekly"
       open-pull-requests-limit: 10
       reviewers:
         - "YOUR-USERNAME"
       labels:
         - "dependencies"
         - "python"

     - package-ecosystem: "github-actions"
       directory: "/"
       schedule:
         interval: "weekly"
       open-pull-requests-limit: 5
   ```

#### Code Climate for Code Quality

1. Go to [https://codeclimate.com](https://codeclimate.com)
2. Sign in with GitHub
3. Add repository
4. Configure quality checks
5. Add badge:
   ```markdown
   [![Maintainability](https://api.codeclimate.com/v1/badges/YOUR-BADGE-ID/maintainability)](https://codeclimate.com/github/YOUR-USERNAME/bioql-ecosystem)
   ```

#### Snyk for Security Scanning

1. Go to [https://snyk.io](https://snyk.io)
2. Sign up with GitHub
3. Import project
4. Enable automatic PR checks
5. Add badge:
   ```markdown
   [![Known Vulnerabilities](https://snyk.io/test/github/YOUR-USERNAME/bioql-ecosystem/badge.svg)](https://snyk.io/test/github/YOUR-USERNAME/bioql-ecosystem)
   ```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: Remote Already Exists

**Error:**
```
fatal: remote origin already exists
```

**Solution:**
```bash
# Remove existing remote
git remote remove origin

# Add new remote
git remote add origin git@github.com:YOUR-USERNAME/bioql-ecosystem.git
```

#### Issue 2: Push Rejected

**Error:**
```
! [rejected]        main -> main (fetch first)
```

**Solution:**
```bash
# If GitHub repo is empty, force push
git push -u origin main --force

# If there are changes on remote, pull first
git pull origin main --rebase
git push -u origin main
```

#### Issue 3: Authentication Failed (HTTPS)

**Error:**
```
remote: Support for password authentication was removed
```

**Solution:**
```bash
# Switch to SSH or use Personal Access Token
# Option 1: Switch to SSH
git remote set-url origin git@github.com:YOUR-USERNAME/bioql-ecosystem.git

# Option 2: Use Personal Access Token
# 1. Generate token: GitHub Settings → Developer settings → Personal access tokens
# 2. Use token as password when prompted
```

#### Issue 4: CI/CD Workflow Fails

**Common Causes:**
- Missing secrets (IBM_QUANTUM_TOKEN, etc.)
- Python version mismatch
- Missing dependencies
- Test failures

**Solution:**
```bash
# Check workflow logs in GitHub Actions tab
# Add missing secrets in Settings → Secrets
# Update workflow file if needed

# Test locally first
pytest tests/ -v
black --check .
flake8 .
```

#### Issue 5: Large Files Not Uploading

**Error:**
```
remote: error: File xxx is 100.00 MB; this exceeds GitHub's file size limit of 100 MB
```

**Solution:**
```bash
# Use Git LFS for large files
git lfs install
git lfs track "*.whl"
git lfs track "*.tar.gz"
git add .gitattributes
git commit -m "Add Git LFS tracking"
git push
```

#### Issue 6: Submodule Issues

**Error:**
```
fatal: No url found for submodule path 'xxx' in .gitmodules
```

**Solution:**
```bash
# Update submodule URLs
git submodule sync
git submodule update --init --recursive

# Or remove and re-add submodules
git submodule deinit -f submodule-name
git rm -f submodule-name
git submodule add <url> submodule-name
```

#### Issue 7: Branch Protection Blocking Push

**Error:**
```
remote: error: GH006: Protected branch update failed
```

**Solution:**
- Create a pull request instead of pushing directly
- OR temporarily disable branch protection (not recommended)
- OR configure exception for specific users

### Getting Help

- **GitHub Community:** [https://github.community](https://github.community)
- **GitHub Support:** [https://support.github.com](https://support.github.com)
- **GitHub Docs:** [https://docs.github.com](https://docs.github.com)

---

## Quick Reference Commands

### Daily Workflow

```bash
# Check status
git status

# Create feature branch
git checkout -b feature/my-feature

# Make changes, commit
git add .
git commit -m "feat: Add new feature"

# Push to remote
git push -u origin feature/my-feature

# Create pull request (via GitHub UI or gh CLI)
gh pr create --title "Add new feature" --body "Description"

# After PR approval, merge and delete branch
gh pr merge 123 --squash --delete-branch
```

### Repository Management

```bash
# Clone repository
git clone git@github.com:YOUR-USERNAME/bioql-ecosystem.git

# Add remote
git remote add origin git@github.com:YOUR-USERNAME/bioql-ecosystem.git

# Change remote URL
git remote set-url origin git@github.com:YOUR-USERNAME/bioql-ecosystem.git

# View remotes
git remote -v

# Fetch all branches
git fetch --all

# Pull latest changes
git pull origin main

# Push to remote
git push origin main

# Force push (dangerous!)
git push origin main --force-with-lease
```

### Branch Management

```bash
# List branches
git branch -a

# Create branch
git checkout -b new-branch

# Switch branch
git checkout main

# Delete local branch
git branch -d branch-name

# Delete remote branch
git push origin --delete branch-name

# Rename branch
git branch -m old-name new-name
```

### Tag Management

```bash
# Create tag
git tag -a v1.0.0 -m "Version 1.0.0"

# Push tag
git push origin v1.0.0

# Push all tags
git push origin --tags

# Delete tag
git tag -d v1.0.0
git push origin --delete v1.0.0
```

### GitHub CLI Commands

```bash
# View issues
gh issue list

# Create issue
gh issue create --title "Bug report" --body "Description"

# View pull requests
gh pr list

# Create pull request
gh pr create

# Merge pull request
gh pr merge 123

# View workflow runs
gh run list

# Trigger workflow
gh workflow run ci.yml

# Clone repository
gh repo clone YOUR-USERNAME/bioql-ecosystem
```

---

## Appendix: GitHub Actions Workflow Examples

### Example: Deploy on Release

```yaml
name: Deploy Release

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to PyPI
        run: |
          pip install build twine
          cd Spectrix_framework
          python -m build
          twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

### Example: Nightly Tests

```yaml
name: Nightly Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Run at 2 AM daily
  workflow_dispatch:

jobs:
  extended-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Run extended test suite
        run: |
          pip install -r requirements.txt
          pytest tests/ -v --runslow
        env:
          IBM_QUANTUM_TOKEN: ${{ secrets.IBM_QUANTUM_TOKEN }}
```

### Example: Auto-label Issues

```yaml
name: Auto Label Issues

on:
  issues:
    types: [opened]

jobs:
  auto-label:
    runs-on: ubuntu-latest
    steps:
      - name: Label bug reports
        if: contains(github.event.issue.title, '[BUG]')
        run: |
          gh issue edit ${{ github.event.issue.number }} --add-label "bug"
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Next Steps

After completing this setup:

1. [ ] Configure all required secrets
2. [ ] Create initial issue templates
3. [ ] Set up team structure
4. [ ] Enable branch protection
5. [ ] Integrate external services (Codecov, Sentry)
6. [ ] Create first release
7. [ ] Update documentation
8. [ ] Announce repository to team
9. [ ] Set up project board for roadmap
10. [ ] Configure notifications

---

## Additional Resources

### Documentation
- [GitHub Docs](https://docs.github.com)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub CLI Manual](https://cli.github.com/manual)
- [Git Documentation](https://git-scm.com/doc)

### Tools
- [GitHub Desktop](https://desktop.github.com)
- [GitHub CLI](https://cli.github.com)
- [Git LFS](https://git-lfs.github.com)

### Best Practices
- [Git Commit Message Conventions](https://www.conventionalcommits.org)
- [GitHub Flow](https://guides.github.com/introduction/flow)
- [Semantic Versioning](https://semver.org)

---

**Document Version:** 1.0
**Last Updated:** November 2025
**Maintained By:** BioQL Development Team
**Contact:** github@bioql.io (example)

---

**End of GitHub Setup Guide**
