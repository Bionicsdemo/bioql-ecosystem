# BioQL Ecosystem - Git Submodules Setup Guide

## Overview

This guide explains how to manage git submodules in the BioQL Ecosystem. The project uses submodules to manage multiple interconnected repositories as a cohesive system.

## Current Submodule Status

### Identified Separate Repositories (Active Submodules)

The following directories are already separate git repositories and can be configured as submodules:

1. **BioQL_agents** - Agent-based quantum computing system
2. **Server_bioql** - Backend server infrastructure
3. **bioql_website** - Frontend web interface (Remote: https://github.com/Bionicsdemo/spectrix.git)
4. **bioql_quillow_docking** - Quantum-classical docking integration

### Regular Directories (Potential Future Submodules)

These directories are currently regular folders within the main repository:

1. **Spectrix_framework** - Core BioQL Framework with quantum computing primitives
2. **Quillow** - Quantum Error Correction (QEC) system
3. **QPHAROS** - Quantum-Powered Hierarchical Adaptive Reinforcement for Drug Discovery
4. **Quantum_graph** - Graph visualization and analysis system

## Getting Started with Submodules

### First-Time Clone (Recommended Method)

When cloning the BioQL repository for the first time, use the `--recurse-submodules` flag:

```bash
git clone --recurse-submodules <BIOQL_MAIN_REPO_URL>
cd Spectrix_BioQL
```

This automatically initializes and updates all submodules during the clone.

### Alternative: Clone Then Initialize Submodules

If you already cloned without `--recurse-submodules`:

```bash
# Initialize submodule configuration
git submodule init

# Fetch and checkout all submodule content
git submodule update
```

Or do both in one command:

```bash
git submodule update --init --recursive
```

## Working with Submodules

### Updating All Submodules to Latest

To update all submodules to their latest commits on the tracked branch:

```bash
# Update all submodules to latest remote commits
git submodule update --remote --recursive

# Stage the changes
git add .

# Commit the submodule updates
git commit -m "Update submodules to latest versions"
```

### Updating a Specific Submodule

```bash
# Navigate to the submodule directory
cd BioQL_agents

# Pull latest changes
git pull origin main

# Go back to main repository
cd ..

# Commit the submodule update
git add BioQL_agents
git commit -m "Update BioQL_agents submodule"
```

### Making Changes Within a Submodule

```bash
# Navigate to the submodule
cd Server_bioql

# Create a new branch
git checkout -b feature/new-endpoint

# Make your changes
# ... edit files ...

# Commit changes
git add .
git commit -m "Add new API endpoint"

# Push to the submodule's remote
git push origin feature/new-endpoint

# Return to main repository
cd ..

# The main repo will detect the submodule change
git status
git add Server_bioql
git commit -m "Update Server_bioql submodule with new endpoint"
```

### Checking Submodule Status

```bash
# View status of all submodules
git submodule status

# View detailed information
git submodule foreach git status

# Check if submodules are up to date
git submodule foreach git fetch
git submodule foreach 'git log --oneline HEAD..origin/main'
```

## Adding New Submodules

### Adding an Existing Repository as a Submodule

```bash
# Add a new submodule
git submodule add <repository-url> <path>

# Example:
git submodule add https://github.com/your-org/bioql-analytics.git analytics

# Commit the .gitmodules changes
git commit -m "Add analytics submodule"

# Push to remote
git push
```

### Converting an Existing Directory to a Submodule

If you want to convert one of the regular directories (like Spectrix_framework) into a submodule:

1. **Create a new repository on GitHub/GitLab**

2. **Initialize and push the directory as a separate repo:**

```bash
# Navigate to the directory
cd Spectrix_framework

# Initialize git (if not already done)
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Extract Spectrix_framework as separate repository"

# Add remote
git remote add origin <NEW_REPO_URL>

# Push to remote
git push -u origin main

# Return to main repo
cd ..
```

3. **Remove the directory from the main repository:**

```bash
# Remove from git tracking but keep files temporarily
git rm -r --cached Spectrix_framework

# Commit the removal
git commit -m "Remove Spectrix_framework directory before converting to submodule"

# Delete the local directory
rm -rf Spectrix_framework
```

4. **Add it back as a submodule:**

```bash
# Add as submodule
git submodule add <NEW_REPO_URL> Spectrix_framework

# Commit the submodule addition
git commit -m "Add Spectrix_framework as submodule"

# Push changes
git push
```

## Best Practices

### 1. Always Update Before Making Changes

```bash
# Update main repository
git pull

# Update all submodules
git submodule update --recursive
```

### 2. Pin Submodules to Specific Commits

By default, submodules are pinned to specific commits. This ensures reproducibility:

```bash
# When you want to update a submodule to a newer commit:
cd <submodule-directory>
git checkout main
git pull
cd ..
git add <submodule-directory>
git commit -m "Update <submodule-name> to latest"
```

### 3. Use Branch Tracking (Optional)

You can configure submodules to track a specific branch:

```bash
# Set a submodule to track a branch
git config -f .gitmodules submodule.BioQL_agents.branch main

# Update to latest on that branch
git submodule update --remote BioQL_agents
```

### 4. Work on Feature Branches

Always create feature branches within submodules:

```bash
cd Server_bioql
git checkout -b feature/my-feature
# Make changes
git commit -am "Implement feature"
git push origin feature/my-feature
```

### 5. Keep .gitmodules in Version Control

The `.gitmodules` file should always be committed and tracked:

```bash
git add .gitmodules
git commit -m "Update submodule configuration"
```

### 6. Document Submodule URLs

Before configuring `.gitmodules`, ensure you have the correct repository URLs:

```bash
# Check current remote URLs for existing repos
cd BioQL_agents && git remote -v && cd ..
cd Server_bioql && git remote -v && cd ..
cd bioql_website && git remote -v && cd ..
cd bioql_quillow_docking && git remote -v && cd ..
```

## Troubleshooting

### Submodule Directory is Empty

```bash
git submodule update --init --recursive
```

### Submodule Shows Modified When Nothing Changed

```bash
# This can happen with different line endings or permissions
cd <submodule>
git status
git diff

# If it's a line ending issue:
git config core.autocrlf false
```

### Detached HEAD State in Submodule

Submodules are checked out to specific commits (detached HEAD). To work on them:

```bash
cd <submodule>
git checkout main  # or your preferred branch
```

### Removing a Submodule

```bash
# 1. Delete the relevant section from .gitmodules
# 2. Stage the .gitmodules changes
git add .gitmodules

# 3. Delete the relevant section from .git/config
# 4. Remove the submodule files
git rm --cached <submodule-path>
rm -rf .git/modules/<submodule-path>
rm -rf <submodule-path>

# 5. Commit the changes
git commit -m "Remove <submodule-name> submodule"
```

### Sync Submodule URLs

If submodule URLs have changed:

```bash
# Update .gitmodules with new URLs, then:
git submodule sync --recursive
git submodule update --init --recursive
```

## Advanced Workflows

### Parallel Development Across Submodules

When working on features that span multiple submodules:

```bash
# 1. Create feature branches in each affected submodule
cd BioQL_agents
git checkout -b feature/integration
cd ../Server_bioql
git checkout -b feature/integration

# 2. Make changes and commit in each submodule
# 3. In the main repository, update references
cd ..
git add BioQL_agents Server_bioql
git commit -m "WIP: Integration feature across submodules"

# 4. Push each submodule's branch
cd BioQL_agents && git push origin feature/integration && cd ..
cd Server_bioql && git push origin feature/integration && cd ..

# 5. Push main repository
git push
```

### Testing with Different Submodule Versions

```bash
# Check out a specific commit in a submodule
cd QPHAROS
git checkout <commit-hash>
cd ..

# Test your changes

# If successful, commit the submodule reference
git add QPHAROS
git commit -m "Use QPHAROS version <commit-hash> for stability"
```

### Automated Submodule Updates (CI/CD)

For continuous integration, add this to your CI script:

```bash
#!/bin/bash
# Update all submodules to latest
git submodule update --init --recursive --remote

# Run tests
./run_tests.sh

# If tests pass, commit updates
if [ $? -eq 0 ]; then
    git add .
    git commit -m "chore: Update submodules to latest" || echo "No changes"
    git push
fi
```

## Repository URLs Reference

Before finalizing the `.gitmodules` file, collect the repository URLs:

| Submodule | Path | Repository URL | Status |
|-----------|------|----------------|--------|
| BioQL_agents | `BioQL_agents` | `<TO_BE_CONFIGURED>` | Active repo, needs URL |
| Server_bioql | `Server_bioql` | `<TO_BE_CONFIGURED>` | Active repo, needs URL |
| bioql_website | `bioql_website` | `https://github.com/Bionicsdemo/spectrix.git` | Configured |
| bioql_quillow_docking | `bioql_quillow_docking` | `<TO_BE_CONFIGURED>` | Active repo, needs URL |
| Spectrix_framework | `Spectrix_framework` | Not yet a repo | Needs conversion |
| Quillow | `Quillow` | Not yet a repo | Needs conversion |
| QPHAROS | `QPHAROS` | Not yet a repo | Needs conversion |
| Quantum_graph | `Quantum_graph` | Not yet a repo | Needs conversion |

## Next Steps

1. **Configure Repository URLs**: Update the `.gitmodules` file with actual repository URLs
2. **Verify Remote Access**: Ensure you have access to all submodule repositories
3. **Initialize Submodules**: Run `git submodule update --init --recursive`
4. **Document Dependencies**: Add submodule version requirements to your main README
5. **Set Up CI/CD**: Configure automated testing across submodules
6. **Consider Converting**: Evaluate if Spectrix_framework, Quillow, QPHAROS, and Quantum_graph should be separate repos

## Additional Resources

- [Git Submodules Official Documentation](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
- [GitHub Guide on Submodules](https://github.blog/2016-02-01-working-with-submodules/)
- [Atlassian Submodules Tutorial](https://www.atlassian.com/git/tutorials/git-submodule)

## Support

For issues with submodule configuration in the BioQL Ecosystem, please:
1. Check this guide first
2. Review the troubleshooting section
3. Contact the BioQL development team
4. Open an issue in the main repository

---

**Last Updated**: November 12, 2025
**Maintainer**: BioQL Development Team
