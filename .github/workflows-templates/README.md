# GitHub Actions Workflows Templates

This directory contains GitHub Actions workflow templates for the volante_lokalnie project's comprehensive CI/CD system.

## Setup Instructions

Due to GitHub App permissions, these workflow files need to be manually copied to `.github/workflows/` directory by a repository maintainer.

### 1. Copy Workflow Files

```bash
# Copy all workflow templates to the workflows directory
cp .github/workflows-templates/*.yml .github/workflows/
```

### 2. Required Secrets

The workflows require the following secrets to be configured in the repository:

#### PyPI Publishing (for release.yml)
- `PYPI_TOKEN`: PyPI API token for publishing packages
  - Go to https://pypi.org/manage/account/token/
  - Create a new token with scope for this project
  - Add it to GitHub repository secrets

#### GitHub Token (automatically provided)
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions
  - Used for creating releases and uploading artifacts

### 3. Workflow Files Description

#### `push.yml` - Continuous Integration
- **Trigger**: Push to main branch, pull requests
- **Purpose**: Code quality checks, testing, building
- **Features**:
  - Multiplatform testing (Linux, Windows, macOS)
  - Python version matrix (3.10, 3.11, 3.12)
  - Linting with Ruff and MyPy
  - Build script validation
  - Artifact generation

#### `release.yml` - Automated Release
- **Trigger**: Git tags matching `v*` pattern
- **Purpose**: Automated package publishing and binary distribution
- **Features**:
  - Pre-release testing
  - Multiplatform binary creation
  - PyPI package publishing
  - GitHub release with binaries
  - Automated release notes

#### `test-release.yml` - Pre-release Testing
- **Trigger**: Pre-release tags (`v*-rc*`, `v*-alpha*`, `v*-beta*`)
- **Purpose**: Test release process without publishing
- **Features**:
  - Release pipeline validation
  - Binary creation testing
  - Process verification

### 4. Workflow Activation

After copying the files:

1. **Commit and push** the workflow files
2. **Configure secrets** in repository settings
3. **Test the workflows**:
   - Push to main branch (triggers push.yml)
   - Create a pre-release tag (triggers test-release.yml)
   - Create a release tag (triggers release.yml)

### 5. Usage Examples

#### Testing the CI Pipeline
```bash
# Push changes to main branch
git push origin main
```

#### Creating a Pre-release for Testing
```bash
# Create and push a pre-release tag
git tag v1.2.3-rc1
git push origin v1.2.3-rc1
```

#### Creating a Production Release
```bash
# Use the release script
./scripts/release.sh -t patch

# Or manually create a tag
git tag v1.2.3
git push origin v1.2.3
```

### 6. Workflow Customization

The workflows can be customized by modifying:

- **Python versions**: Update the matrix in `push.yml`
- **Operating systems**: Add/remove OS in the matrix
- **Build tools**: Modify the build steps
- **Publishing**: Change PyPI publishing settings

### 7. Troubleshooting

#### Common Issues

1. **Permission Denied**: Ensure PYPI_TOKEN is correctly set
2. **Build Failures**: Check that all dependencies are specified
3. **Binary Creation**: Verify PyInstaller works with your code
4. **Tag Format**: Ensure tags follow `v*` pattern for releases

#### Debug Steps

1. Check GitHub Actions logs for detailed error messages
2. Test locally using the build scripts
3. Verify secrets are correctly configured
4. Ensure branch protection rules allow the workflows

### 8. Local Development

The build system works independently of GitHub Actions:

```bash
# Local development and testing
make dev-setup
make dev-test
make all

# Local release testing
make release-dry-run
./scripts/release.sh -t patch --dry-run
```

### 9. Migration Steps

If you're migrating from the existing workflow system:

1. Backup existing workflows
2. Copy new workflow templates
3. Update any custom configurations
4. Test with a pre-release tag first
5. Verify all secrets are properly configured

## Benefits

Once set up, this system provides:

- **Automated testing** across multiple platforms and Python versions
- **Automated releases** with binary distribution
- **Quality gates** to prevent broken releases
- **Developer-friendly** local tooling
- **Production-ready** CI/CD pipeline

The workflows are designed to be robust, comprehensive, and maintainable for long-term use.