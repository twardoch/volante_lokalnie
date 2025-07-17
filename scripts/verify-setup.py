#!/usr/bin/env python3
"""Verify that the build system is properly set up."""
# this_file: scripts/verify-setup.py

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

def run_command(cmd: List[str], check: bool = True) -> Tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"

def check_file_exists(path: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(path).exists():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: {path} (missing)")
        return False

def check_command(cmd: List[str], description: str) -> bool:
    """Check if a command works."""
    success, output = run_command(cmd, check=False)
    if success:
        print(f"✅ {description}: Available")
        return True
    else:
        print(f"❌ {description}: {output.strip()}")
        return False

def check_python_import(module: str, description: str) -> bool:
    """Check if a Python module can be imported."""
    try:
        __import__(module)
        print(f"✅ {description}: Available")
        return True
    except ImportError:
        print(f"❌ {description}: Module not found")
        return False

def main():
    """Main verification function."""
    print("🔍 Verifying volante_lokalnie build system setup...\n")
    
    all_checks_passed = True
    
    # Check essential files
    print("📁 Checking essential files:")
    essential_files = [
        ("pyproject.toml", "Project configuration"),
        ("scripts/build.py", "Build script"),
        ("scripts/release.sh", "Release script"),
        ("Makefile", "Makefile"),
        ("src/volante_lokalnie/__init__.py", "Package initialization"),
        ("src/volante_lokalnie/__main__.py", "CLI entry point"),
    ]
    
    for file_path, description in essential_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    print()
    
    # Check GitHub Actions templates
    print("🔧 Checking GitHub Actions templates:")
    workflow_files = [
        (".github/workflows-templates/push.yml", "Push workflow template"),
        (".github/workflows-templates/release.yml", "Release workflow template"),
        (".github/workflows-templates/test-release.yml", "Test release workflow template"),
        (".github/workflows-templates/README.md", "Workflow setup instructions"),
    ]
    
    for file_path, description in workflow_files:
        if not check_file_exists(file_path, description):
            all_checks_passed = False
    
    print()
    
    # Check commands
    print("🔨 Checking available commands:")
    commands = [
        (["git", "--version"], "Git"),
        (["python3", "--version"], "Python 3"),
        ([sys.executable, "-c", "import sys; print(sys.version)"], "Python interpreter"),
    ]
    
    for cmd, description in commands:
        if not check_command(cmd, description):
            all_checks_passed = False
    
    print()
    
    # Check Python dependencies (basic)
    print("📦 Checking Python package structure:")
    python_modules = [
        ("volante_lokalnie", "Main package"),
        ("volante_lokalnie.__version__", "Version module"),
    ]
    
    for module, description in python_modules:
        if not check_python_import(module, description):
            all_checks_passed = False
    
    print()
    
    # Check build system functionality
    print("🔧 Testing build system:")
    
    # Test build script
    success, output = run_command([sys.executable, "scripts/build.py", "--help"], check=False)
    if success:
        print("✅ Build script: Functional")
    else:
        print(f"❌ Build script: {output.strip()}")
        all_checks_passed = False
    
    # Test release script
    success, output = run_command(["bash", "scripts/release.sh", "--help"], check=False)
    if success:
        print("✅ Release script: Functional")
    else:
        print(f"❌ Release script: {output.strip()}")
        all_checks_passed = False
    
    # Test Makefile
    success, output = run_command(["make", "help"], check=False)
    if success:
        print("✅ Makefile: Functional")
    else:
        print(f"❌ Makefile: {output.strip()}")
        all_checks_passed = False
    
    print()
    
    # Check git status
    print("📋 Checking git status:")
    success, output = run_command(["git", "status", "--porcelain"], check=False)
    if success:
        if output.strip():
            print("⚠️  Git: Working directory has uncommitted changes")
        else:
            print("✅ Git: Working directory is clean")
    else:
        print(f"❌ Git: {output.strip()}")
        all_checks_passed = False
    
    # Check current version
    try:
        from volante_lokalnie import __version__
        print(f"✅ Current version: {__version__}")
    except ImportError:
        print("❌ Current version: Could not import")
        all_checks_passed = False
    
    print()
    
    # Summary
    if all_checks_passed:
        print("🎉 All checks passed! The build system is properly set up.")
        print("\n📋 Next steps:")
        print("1. For maintainers: Set up GitHub Actions (see GITHUB_ACTIONS_SETUP.md)")
        print("2. For development: Run 'make dev-setup' to install dev dependencies")
        print("3. For testing: Run 'make dev-test' to run tests")
        print("4. For releases: Run 'make release-dry-run' to test release process")
    else:
        print("❌ Some checks failed. Please review the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()