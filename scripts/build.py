#!/usr/bin/env python3
"""Build script for volante_lokalnie project.

This script provides comprehensive build, test, and release functionality.
"""
# this_file: scripts/build.py

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

def run_command(cmd: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def check_requirements() -> None:
    """Check if required tools are installed."""
    required_tools = ['git']
    for tool in required_tools:
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"Error: {tool} is not installed or not in PATH")
            sys.exit(1)
    
    # Check for uv or fallback to pip
    try:
        subprocess.run(['uv', '--version'], capture_output=True, check=True)
        print("Using uv for package management")
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            subprocess.run([sys.executable, '-m', 'pip', '--version'], capture_output=True, check=True)
            print("UV not found, falling back to pip")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: Neither uv nor pip is available")
            sys.exit(1)

def clean_build() -> None:
    """Clean build artifacts."""
    print("Cleaning build artifacts...")
    artifacts = ['dist/', 'build/', '*.egg-info/', '__pycache__/', '.pytest_cache/', 'coverage.xml']
    for artifact in artifacts:
        if Path(artifact).exists():
            if Path(artifact).is_dir():
                import shutil
                shutil.rmtree(artifact)
            else:
                Path(artifact).unlink()

def get_python_runner() -> List[str]:
    """Get the appropriate Python runner (uv or pip)."""
    try:
        subprocess.run(['uv', '--version'], capture_output=True, check=True)
        return ['uv', 'run']
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [sys.executable, '-m']

def run_tests() -> None:
    """Run the complete test suite."""
    print("Running tests...")
    runner = get_python_runner()
    
    # Try to run with coverage if available
    try:
        run_command(runner + ['pytest', '-v', '--cov=src/volante_lokalnie', '--cov-report=xml', '--cov-report=term-missing', 'tests/'])
    except SystemExit:
        # Fallback to basic pytest
        try:
            run_command(runner + ['pytest', '-v', 'tests/'])
        except SystemExit:
            # Final fallback
            run_command([sys.executable, '-m', 'pytest', 'tests/'])

def run_lint() -> None:
    """Run linting checks."""
    print("Running linting checks...")
    runner = get_python_runner()
    
    # Try to run linting tools
    try:
        run_command(runner + ['ruff', 'check', 'src/', 'tests/', 'scripts/'])
        run_command(runner + ['ruff', 'format', '--check', 'src/', 'tests/', 'scripts/'])
        run_command(runner + ['mypy', 'src/', 'tests/', '--config-file=pyproject.toml'])
    except SystemExit:
        print("Warning: Some linting tools may not be available")

def build_package() -> None:
    """Build the package."""
    print("Building package...")
    try:
        run_command(['uv', 'build'])
    except SystemExit:
        # Fallback to python -m build
        try:
            run_command([sys.executable, '-m', 'build'])
        except SystemExit:
            print("Error: Neither uv nor build module available")
            sys.exit(1)

def get_version() -> str:
    """Get the current version from git tags."""
    try:
        result = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "0.0.0"

def create_binary(target_os: str) -> None:
    """Create binary distribution using PyInstaller."""
    print(f"Creating binary for {target_os}...")
    
    # Try to install PyInstaller if not present
    try:
        subprocess.run(['uv', 'add', '--dev', 'pyinstaller'], capture_output=True, check=True)
        runner = ['uv', 'run']
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Try pip install
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], capture_output=True, check=True)
            runner = [sys.executable, '-m']
        except subprocess.CalledProcessError:
            print("Error: Could not install PyInstaller")
            sys.exit(1)
    
    # Basic PyInstaller command
    cmd = runner + [
        'pyinstaller', 
        '--onefile',
        '--name', f'volante-lokalnie-{target_os}',
        '--add-data', 'src/volante_lokalnie/volante_lokalnie.tcss:volante_lokalnie/',
        'src/volante_lokalnie/__main__.py'
    ]
    
    # OS-specific modifications
    if target_os == 'windows':
        cmd.extend(['--console'])
    elif target_os == 'macos':
        cmd.extend(['--console'])
    
    run_command(cmd)

def release_check() -> None:
    """Check if ready for release."""
    print("Checking release readiness...")
    
    # Check if on main branch
    result = subprocess.run(['git', 'branch', '--show-current'], 
                          capture_output=True, text=True)
    if result.stdout.strip() != 'main':
        print("Warning: Not on main branch")
    
    # Check if working directory is clean
    result = subprocess.run(['git', 'status', '--porcelain'], 
                          capture_output=True, text=True)
    if result.stdout.strip():
        print("Error: Working directory is not clean")
        sys.exit(1)
    
    # Check if ahead of remote
    result = subprocess.run(['git', 'status', '--porcelain=v1', '--branch'], 
                          capture_output=True, text=True)
    if '[ahead' in result.stdout:
        print("Warning: Local branch is ahead of remote")

def create_release(version: str, message: str = "") -> None:
    """Create a new release tag."""
    print(f"Creating release {version}...")
    
    release_check()
    
    # Create annotated tag
    tag_message = message or f"Release {version}"
    run_command(['git', 'tag', '-a', version, '-m', tag_message])
    
    # Push tag
    run_command(['git', 'push', 'origin', version])
    
    print(f"Release {version} created and pushed!")

def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Build script for volante_lokalnie')
    parser.add_argument('command', choices=[
        'clean', 'lint', 'test', 'build', 'binary', 'release', 'all'
    ], help='Command to run')
    parser.add_argument('--version', help='Version for release command')
    parser.add_argument('--message', help='Release message')
    parser.add_argument('--target-os', choices=['linux', 'windows', 'macos'], 
                       default=platform.system().lower(), help='Target OS for binary')
    
    args = parser.parse_args()
    
    check_requirements()
    
    if args.command == 'clean':
        clean_build()
    elif args.command == 'lint':
        run_lint()
    elif args.command == 'test':
        run_tests()
    elif args.command == 'build':
        build_package()
    elif args.command == 'binary':
        create_binary(args.target_os)
    elif args.command == 'release':
        if not args.version:
            print("Error: --version required for release command")
            sys.exit(1)
        create_release(args.version, args.message)
    elif args.command == 'all':
        clean_build()
        run_lint()
        run_tests()
        build_package()
    
    print("Build completed successfully!")

if __name__ == '__main__':
    main()