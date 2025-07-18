# GitHub Actions Setup Guide

## Quick Setup for Repository Maintainers

The volante_lokalnie project includes a comprehensive CI/CD system with multiplatform builds and automated releases. Due to GitHub App permissions, the workflow files need to be manually activated.

### 1. Copy Workflow Files

```bash
# Copy workflow templates to active workflows directory
cp .github/workflows-templates/*.yml .github/workflows/
```

### 2. Configure Repository Secrets

Go to **Settings > Secrets and variables > Actions** and add:

#### Required Secrets
- **`PYPI_TOKEN`**: PyPI API token for package publishing
  - Visit https://pypi.org/manage/account/token/
  - Create a new token scoped to this project
  - Copy the token value to GitHub secrets

### 3. Verify Workflow Files

The system includes three main workflows:

#### `push.yml` - Continuous Integration
- **Triggers**: Push to main, pull requests
- **Tests**: Python 3.10, 3.11, 3.12 on Linux, Windows, macOS
- **Checks**: Ruff linting, MyPy type checking, pytest
- **Builds**: Package distributions and validation

#### `release.yml` - Automated Release
- **Triggers**: Git tags matching `v*` (e.g., `v1.2.3`)
- **Creates**: Multiplatform binaries (Linux, Windows, macOS)
- **Publishes**: PyPI packages and GitHub releases
- **Includes**: Automated release notes

#### `test-release.yml` - Pre-release Testing
- **Triggers**: Pre-release tags (`v*-rc*`, `v*-alpha*`, `v*-beta*`)
- **Tests**: Release pipeline without publishing
- **Validates**: Binary creation and process verification

### 4. Test the Setup

#### Test CI Pipeline
```bash
# Make a small change and push to main
echo "# Test" >> README.md
git add README.md
git commit -m "test: verify CI pipeline"
git push origin main
```

#### Test Pre-release Process
```bash
# Create a pre-release tag
git tag v1.0.3-rc1
git push origin v1.0.3-rc1
```

#### Create Production Release
```bash
# Use the release script
./scripts/release.sh -t patch
```

### 5. What You Get

Once activated, the system provides:

✅ **Automated Testing**
- Cross-platform testing (Linux, Windows, macOS)
- Multiple Python versions (3.10, 3.11, 3.12)
- Code quality checks (Ruff, MyPy)
- Test coverage reporting

✅ **Automated Releases**
- Git-tag-based semantic versioning
- Multiplatform binary distribution
- PyPI package publishing
- GitHub releases with binaries

✅ **Developer Tools**
- Local build scripts (`scripts/build.py`)
- Release management (`scripts/release.sh`)
- Makefile shortcuts (`make release-patch`)
- Comprehensive test suite

✅ **Binary Distribution**
- `volante-lokalnie-linux` (Linux executable)
- `volante-lokalnie-windows.exe` (Windows executable)
- `volante-lokalnie-macos` (macOS executable)

### 6. Usage Examples

#### Daily Development
```bash
make dev-setup          # Setup development environment
make dev-test           # Run tests with coverage
make all                # Run complete pipeline
```

#### Creating Releases
```bash
make release-dry-run    # Test release process
make release-patch      # Create patch release (1.0.0 -> 1.0.1)
make release-minor      # Create minor release (1.0.0 -> 1.1.0)
./scripts/release.sh -t major -m "Breaking changes"  # Custom release
```

### 7. Troubleshooting

#### Workflow Not Triggering
- Ensure workflow files are in `.github/workflows/` (not templates)
- Check that secrets are properly configured
- Verify branch protection rules allow Actions

#### Release Failures
- Verify `PYPI_TOKEN` is valid and has correct permissions
- Check that version numbers follow semantic versioning
- Ensure working directory is clean before release

#### Binary Creation Issues
- PyInstaller may need additional configuration for complex dependencies
- Check that `volante_lokalnie.tcss` file exists and is included
- Verify import paths in `__main__.py`

### 8. Advanced Configuration

#### Customizing Python Versions
Edit the matrix in `push.yml`:
```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12", "3.13"]  # Add Python 3.13
```

#### Adding More Platforms
Add to the OS matrix:
```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest, ubuntu-20.04]
```

#### Modifying Binary Names
Update the binary names in `release.yml`:
```yaml
binary-name: custom-volante-lokalnie-linux
```

### 9. Security Notes

- **PyPI Token**: Use a scoped token, not your global PyPI password
- **Secrets**: Never commit secrets to the repository
- **Permissions**: The workflows use minimal required permissions
- **Validation**: All releases go through comprehensive testing

### 10. Support

After setup, developers can:
- Use local build tools without GitHub Actions
- Create releases manually or through CI/CD
- Download binaries from GitHub releases
- Install via pip from PyPI

The system is designed to work both with and without GitHub Actions, providing flexibility for different development workflows.

## Summary

This setup provides a production-ready CI/CD system with:
- Automated testing and quality checks
- Multiplatform binary distribution
- Semantic versioning with git tags
- Developer-friendly local tooling
- Comprehensive documentation

Once activated, the system requires minimal maintenance and provides a professional development and release experience.