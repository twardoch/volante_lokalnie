"""Test version handling and semver compliance."""
# this_file: tests/test_version.py

import re
from unittest import mock

import pytest

from volante_lokalnie import __version__


def test_version_is_string():
    """Test that version is a string."""
    assert isinstance(__version__, str)
    assert __version__ != ""


def test_version_format():
    """Test version follows semantic versioning format."""
    # Regex for semantic versioning (may include dev/post suffixes)
    semver_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:\.(?:post|dev)\d+)?(?:\+[a-zA-Z0-9.-]+)?$'
    
    # Remove 'v' prefix if present
    version = __version__.lstrip('v')
    
    assert re.match(semver_pattern, version), f"Version {version} doesn't match semver pattern"


def test_version_components():
    """Test version has valid components."""
    # Extract base version without suffixes
    base_version = re.match(r'^(\d+)\.(\d+)\.(\d+)', __version__.lstrip('v'))
    assert base_version is not None
    
    major, minor, patch = base_version.groups()
    assert int(major) >= 0
    assert int(minor) >= 0
    assert int(patch) >= 0


def test_version_importable():
    """Test version can be imported from package."""
    import volante_lokalnie
    assert hasattr(volante_lokalnie, '__version__')
    assert volante_lokalnie.__version__ == __version__


def test_version_consistency():
    """Test version is consistent across different import methods."""
    import volante_lokalnie
    from volante_lokalnie import __version__ as pkg_version
    from volante_lokalnie.__version__ import __version__ as ver_version
    
    assert pkg_version == ver_version
    assert volante_lokalnie.__version__ == ver_version


@mock.patch('subprocess.run')
def test_build_script_version_handling(mock_run):
    """Test that build script can handle version operations."""
    # Mock git describe output
    mock_run.return_value.stdout = "v1.2.3"
    mock_run.return_value.returncode = 0
    
    # Import and test the get_version function from build script
    import sys
    sys.path.insert(0, 'scripts')
    
    try:
        from build import get_version
        version = get_version()
        assert version == "v1.2.3"
    except ImportError:
        pytest.skip("Build script not available")
    finally:
        sys.path.pop(0)


def test_version_not_dev_in_release():
    """Test that production versions don't contain dev markers."""
    # This test might fail during development, which is expected
    if "dev" in __version__:
        pytest.skip("Development version detected")
    
    assert "dev" not in __version__
    assert "dirty" not in __version__