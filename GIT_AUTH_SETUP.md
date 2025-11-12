# Git Authentication Setup Guide

## Issue
The git push failed with: `Permission denied (publickey)`

This means your Git client cannot authenticate with GitHub.

## Solution Options

### Option 1: SSH Key Setup (Recommended)

1. **Check for existing SSH keys:**
   ```bash
   ls -la ~/.ssh
   ```
   Look for files like `id_rsa.pub`, `id_ed25519.pub`, etc.

2. **Generate new SSH key (if needed):**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```
   Press Enter to accept default location, optionally set passphrase

3. **Add SSH key to ssh-agent:**
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```

4. **Copy SSH public key:**
   ```bash
   cat ~/.ssh/id_ed25519.pub | pbcopy
   ```

5. **Add to GitHub:**
   - Go to: https://github.com/settings/keys
   - Click "New SSH key"
   - Paste your public key
   - Give it a meaningful title
   - Click "Add SSH key"

6. **Test connection:**
   ```bash
   ssh -T git@github.com
   ```
   Should see: "Hi username! You've successfully authenticated..."

### Option 2: HTTPS with Personal Access Token

1. **Generate Personal Access Token:**
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token" → "Generate new token (classic)"
   - Set scopes: `repo` (full control of private repositories)
   - Click "Generate token"
   - **COPY THE TOKEN** (you won't see it again!)

2. **Update Git remote to use HTTPS:**
   ```bash
   git remote set-url origin https://github.com/YOUR_USERNAME/Spectrix_BioQL.git
   ```

3. **Configure credential helper (macOS):**
   ```bash
   git config --global credential.helper osxkeychain
   ```

4. **Next git push will prompt for credentials:**
   - Username: your GitHub username
   - Password: **paste your Personal Access Token** (not your GitHub password!)

### Option 3: GitHub CLI (gh)

1. **Install gh (if not installed):**
   ```bash
   brew install gh
   ```

2. **Authenticate:**
   ```bash
   gh auth login
   ```
   Follow the prompts to authenticate

3. **Test:**
   ```bash
   gh auth status
   ```

## Current Remote Configuration

Check your current remote:
```bash
git remote -v
```

If it shows `git@github.com:...`, you're using SSH (Option 1)
If it shows `https://github.com/...`, you're using HTTPS (Option 2)

## Quick Fix

If you need to push immediately, the fastest option is Option 2 (HTTPS with PAT):

```bash
# 1. Generate token at https://github.com/settings/tokens
# 2. Update remote
git remote set-url origin https://github.com/YOUR_USERNAME/Spectrix_BioQL.git
# 3. Try push again - it will prompt for username and token
git push origin main
```

## After Authentication is Fixed

Once you've configured authentication, return to the commit/push workflow:

```bash
# Stage all changes
git add .

# Commit (pre-commit hooks will run automatically)
git commit -m "feat: comprehensive testing infrastructure and CI/CD setup

- Add 510 tests (unit, integration, e2e) increasing coverage from 5%
- Implement complete mock infrastructure for external APIs
- Configure pre-commit hooks (15 hooks)
- Set up GitHub Actions CI/CD pipeline
- Add Apache 2.0 license and third-party notices
- Fix GPL licensing incompatibility (remove OpenBabel)
- Migrate Pydantic V1 to V2
- Add copyright headers to 515 Python files
- Create comprehensive documentation and guides

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to GitHub
git push origin main
```

## Troubleshooting

### "Could not resolve hostname"
Check internet connection and DNS settings

### "Repository not found"
Verify you have access to the repository and the URL is correct

### "403 Forbidden" with HTTPS
Your token may have expired or lacks necessary permissions

### Still having issues?
Contact your repository administrator or GitHub support
