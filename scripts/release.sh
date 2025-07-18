#!/bin/bash
# this_file: scripts/release.sh
# Convenient release script for volante_lokalnie

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
RELEASE_TYPE=""
CUSTOM_VERSION=""
MESSAGE=""
DRY_RUN=false

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -t, --type TYPE      Release type: major, minor, patch"
    echo "  -v, --version VER    Custom version (e.g., 1.2.3)"
    echo "  -m, --message MSG    Release message"
    echo "  -n, --dry-run        Show what would be done without doing it"
    echo "  -h, --help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 -t patch                    # Create patch release"
    echo "  $0 -t minor -m 'New features' # Create minor release with message"
    echo "  $0 -v 2.0.0                   # Create custom version"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

get_current_version() {
    local version=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    echo "${version#v}"  # Remove 'v' prefix if present
}

increment_version() {
    local version=$1
    local type=$2
    
    IFS='.' read -r major minor patch <<< "$version"
    
    case $type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            log_error "Invalid release type: $type"
            exit 1
            ;;
    esac
    
    echo "$major.$minor.$patch"
}

check_git_status() {
    if [[ -n $(git status --porcelain) ]]; then
        log_error "Working directory is not clean. Please commit or stash changes."
        exit 1
    fi
    
    local current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]]; then
        log_warn "Not on main branch (current: $current_branch)"
        read -p "Continue anyway? (y/N) " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

run_tests() {
    log_info "Running tests..."
    if ! python scripts/build.py test; then
        log_error "Tests failed. Aborting release."
        exit 1
    fi
}

run_lint() {
    log_info "Running linting checks..."
    if ! python scripts/build.py lint; then
        log_error "Linting failed. Aborting release."
        exit 1
    fi
}

create_release() {
    local version=$1
    local message=$2
    
    log_info "Creating release v$version..."
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would create tag: v$version"
        log_info "[DRY RUN] Would push tag to origin"
        return
    fi
    
    # Create and push tag
    if [[ -n "$message" ]]; then
        git tag -a "v$version" -m "$message"
    else
        git tag -a "v$version" -m "Release v$version"
    fi
    
    git push origin "v$version"
    
    log_info "Release v$version created and pushed!"
    log_info "GitHub Actions will now build and publish the release."
}

main() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                RELEASE_TYPE="$2"
                shift 2
                ;;
            -v|--version)
                CUSTOM_VERSION="$2"
                shift 2
                ;;
            -m|--message)
                MESSAGE="$2"
                shift 2
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Validate arguments
    if [[ -z "$RELEASE_TYPE" && -z "$CUSTOM_VERSION" ]]; then
        log_error "Either --type or --version must be specified"
        usage
        exit 1
    fi
    
    if [[ -n "$RELEASE_TYPE" && -n "$CUSTOM_VERSION" ]]; then
        log_error "Cannot specify both --type and --version"
        usage
        exit 1
    fi
    
    # Check git status
    check_git_status
    
    # Determine new version
    local current_version=$(get_current_version)
    local new_version
    
    if [[ -n "$CUSTOM_VERSION" ]]; then
        new_version="$CUSTOM_VERSION"
    else
        new_version=$(increment_version "$current_version" "$RELEASE_TYPE")
    fi
    
    log_info "Current version: $current_version"
    log_info "New version: $new_version"
    
    # Run checks
    if [[ "$DRY_RUN" == "false" ]]; then
        run_lint
        run_tests
    else
        log_info "[DRY RUN] Skipping tests and linting"
    fi
    
    # Create release
    create_release "$new_version" "$MESSAGE"
}

# Make script executable
chmod +x "$0"

main "$@"