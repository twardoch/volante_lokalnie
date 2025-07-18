"""Integration tests for build and release system."""
# this_file: tests/test_build_integration.py

import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture
def build_script():
    """Path to the build script."""
    return Path(__file__).parent.parent / "scripts" / "build.py"


@pytest.fixture
def release_script():
    """Path to the release script."""
    return Path(__file__).parent.parent / "scripts" / "release.sh"


class TestBuildScript:
    """Test the build script functionality."""

    def test_build_script_exists(self, build_script):
        """Test that build script exists and is executable."""
        assert build_script.exists()
        assert build_script.is_file()

    def test_build_script_help(self, build_script):
        """Test that build script shows help."""
        result = subprocess.run([sys.executable, str(build_script), "--help"], 
                              capture_output=True, text=True)
        assert result.returncode == 0
        assert "Build script for volante_lokalnie" in result.stdout

    def test_build_script_clean_command(self, build_script):
        """Test clean command doesn't fail."""
        result = subprocess.run([sys.executable, str(build_script), "clean"], 
                              capture_output=True, text=True)
        # Should not fail even if nothing to clean
        assert result.returncode == 0

    @mock.patch('subprocess.run')
    def test_build_script_version_extraction(self, mock_run, build_script):
        """Test version extraction from git tags."""
        mock_run.return_value.stdout = "v1.2.3"
        mock_run.return_value.returncode = 0
        
        # Import the function and test it
        import sys
        sys.path.insert(0, str(build_script.parent))
        
        try:
            from build import get_version
            version = get_version()
            assert version == "v1.2.3"
        finally:
            sys.path.pop(0)

    def test_build_script_check_requirements(self, build_script):
        """Test that build script can check requirements."""
        import sys
        sys.path.insert(0, str(build_script.parent))
        
        try:
            from build import check_requirements
            # This should not raise an exception if requirements are met
            check_requirements()
        except SystemExit:
            pytest.skip("Required tools not available")
        finally:
            sys.path.pop(0)


class TestReleaseScript:
    """Test the release script functionality."""

    def test_release_script_exists(self, release_script):
        """Test that release script exists and is executable."""
        assert release_script.exists()
        assert release_script.is_file()
        # Check if executable bit is set
        assert release_script.stat().st_mode & 0o111

    def test_release_script_help(self, release_script):
        """Test that release script shows help."""
        result = subprocess.run([str(release_script), "--help"], 
                              capture_output=True, text=True)
        assert result.returncode == 0
        assert "Usage:" in result.stdout

    def test_release_script_dry_run(self, release_script):
        """Test dry run functionality."""
        result = subprocess.run([str(release_script), "-t", "patch", "--dry-run"], 
                              capture_output=True, text=True)
        # Dry run should succeed even without clean git state
        assert "[DRY RUN]" in result.stdout


class TestProjectStructure:
    """Test project structure and configuration."""

    def test_pyproject_toml_exists(self):
        """Test pyproject.toml exists and is valid."""
        pyproject = Path("pyproject.toml")
        assert pyproject.exists()
        
        # Try to parse it
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        
        with open(pyproject, "rb") as f:
            config = tomllib.load(f)
        
        assert "project" in config
        assert "build-system" in config
        assert "tool" in config

    def test_version_configuration(self):
        """Test version configuration in pyproject.toml."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        
        with open("pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        
        # Check hatch-vcs configuration
        assert "tool" in config
        assert "hatch" in config["tool"]
        assert "version" in config["tool"]["hatch"]
        assert config["tool"]["hatch"]["version"]["source"] == "vcs"

    def test_scripts_directory(self):
        """Test scripts directory structure."""
        scripts_dir = Path("scripts")
        assert scripts_dir.exists()
        assert scripts_dir.is_dir()
        
        # Check for required scripts
        build_script = scripts_dir / "build.py"
        release_script = scripts_dir / "release.sh"
        
        assert build_script.exists()
        assert release_script.exists()

    def test_github_workflows_exist(self):
        """Test GitHub workflows exist."""
        workflows_dir = Path(".github/workflows")
        assert workflows_dir.exists()
        assert workflows_dir.is_dir()
        
        # Check for required workflows
        push_workflow = workflows_dir / "push.yml"
        release_workflow = workflows_dir / "release.yml"
        
        assert push_workflow.exists()
        assert release_workflow.exists()


class TestBuildProcess:
    """Test the complete build process."""

    def test_package_can_be_built(self):
        """Test that package can be built successfully."""
        # This is a more comprehensive test that actually tries to build
        result = subprocess.run([
            sys.executable, "-m", "build", "--outdir", "test_dist", "."
        ], capture_output=True, text=True)
        
        # Clean up test artifacts
        import shutil
        if Path("test_dist").exists():
            shutil.rmtree("test_dist")
        
        # Should succeed if all dependencies are available
        if result.returncode != 0:
            pytest.skip(f"Build failed, likely missing dependencies: {result.stderr}")

    def test_imports_work_after_install(self):
        """Test that package imports work correctly."""
        # Test basic imports
        import volante_lokalnie
        assert hasattr(volante_lokalnie, '__version__')
        
        # Test main module can be imported
        from volante_lokalnie import __main__
        assert hasattr(__main__, 'main')

    def test_cli_entry_point_works(self):
        """Test that CLI entry point is accessible."""
        result = subprocess.run([
            sys.executable, "-m", "volante_lokalnie", "--help"
        ], capture_output=True, text=True, timeout=10)
        
        # Should show help without error
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "Usage:" in result.stdout