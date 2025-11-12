# BioQL Project Badges

This file contains badges and status indicators for the BioQL Ecosystem. Add these badges to your main README.md file.

## Coverage Badge

Add the Codecov coverage badge to your README:

```markdown
[![codecov](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graph/badge.svg?token=YOUR_CODECOV_BADGE_TOKEN)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
```

### How to Get Your Badge Token

1. Go to [codecov.io](https://codecov.io) and sign in
2. Navigate to your repository: `Spectrix_BioQL`
3. Go to **Settings > Badge**
4. Copy the badge markdown code
5. Replace `YOUR_USERNAME` with your GitHub username
6. Replace `YOUR_CODECOV_BADGE_TOKEN` with the token from Codecov

**Note**: The badge token is different from the upload token (CODECOV_TOKEN). The badge token is public and safe to include in your README.

## Example Badge Display

Once configured, the badge will show:

- Current coverage percentage
- Color-coded status (red < 60%, yellow 60-80%, green > 80%)
- Clickable link to detailed coverage report

## Additional Suggested Badges

### CI/CD Status

```markdown
[![CI/CD](https://github.com/YOUR_USERNAME/Spectrix_BioQL/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/Spectrix_BioQL/actions/workflows/ci.yml)
```

### Python Version

```markdown
![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue)
```

### License

```markdown
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
```

### Pre-commit

```markdown
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
```

## Complete Badge Section Example

Here's a complete example of a badges section for your README:

```markdown
# BioQL Ecosystem

[![codecov](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graph/badge.svg?token=YOUR_CODECOV_BADGE_TOKEN)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
[![CI/CD](https://github.com/YOUR_USERNAME/Spectrix_BioQL/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/Spectrix_BioQL/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

*Advanced quantum computing framework for biological research and drug discovery.*
```

## Badge Customization

You can customize badge appearance using shields.io parameters:

```markdown
[![codecov](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graph/badge.svg?token=YOUR_TOKEN&style=flat-square)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
```

Available styles:
- `flat` (default)
- `flat-square`
- `plastic`
- `for-the-badge`
- `social`

## Multi-Component Badges

For individual components, you can create separate badges:

### Spectrix Framework

```markdown
[![Spectrix Coverage](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graph/badge.svg?token=YOUR_TOKEN&flag=spectrix)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
```

### Quillow

```markdown
[![Quillow Coverage](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graph/badge.svg?token=YOUR_TOKEN&flag=quillow)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
```

### QPHAROS

```markdown
[![QPHAROS Coverage](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graph/badge.svg?token=YOUR_TOKEN&flag=qpharos)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
```

## Coverage Graphs

You can also embed coverage graphs in your README:

### Sunburst Chart

```markdown
[![Sunburst](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graphs/sunburst.svg?token=YOUR_TOKEN)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
```

### Tree Graph

```markdown
[![Tree](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graphs/tree.svg?token=YOUR_TOKEN)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
```

### Icicle Chart

```markdown
[![Icicle](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL/branch/main/graphs/icicle.svg?token=YOUR_TOKEN)](https://codecov.io/gh/YOUR_USERNAME/Spectrix_BioQL)
```

## Next Steps

1. Set up Codecov account (see [CODECOV_SETUP.md](CODECOV_SETUP.md))
2. Get your badge token from Codecov
3. Create or update your main README.md
4. Add the badges from this file
5. Commit and push changes
6. Verify badges display correctly on GitHub

---

**See Also**:
- [CODECOV_SETUP.md](CODECOV_SETUP.md) - Complete Codecov setup guide
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [.codecov.yml](.codecov.yml) - Codecov configuration file
