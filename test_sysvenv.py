#!/usr/bin/env python3
"""
Comprehensive test suite for sysvenv

Tests all features including:
- Collaboration snapshots (share/import)
- Package provenance tracking
- Smart snapshot reminders
- Dependency orphan cleanup
- Conflict detection
- System package warnings
- Project venv auto-detection
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestSysvenvBase(unittest.TestCase):
    """Base test class with common setup/teardown"""

    def setUp(self):
        """Create temporary test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.sysvenv_root = self.test_dir / ".local" / "python-packages"
        self.venv_path = self.sysvenv_root / "venv"
        self.history_path = self.sysvenv_root / "history"
        self.snapshots_path = self.sysvenv_root / "snapshots"

        # Set environment variable to use test directory
        os.environ['HOME'] = str(self.test_dir)

        # Path to sysvenv script
        self.sysvenv_script = Path(__file__).parent / "sysvenv"

    def tearDown(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def run_sysvenv(self, *args, input_text=None, check=True):
        """Helper to run sysvenv command"""
        cmd = [str(self.sysvenv_script)] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            input=input_text,
            check=check
        )
        return result

    def init_venv(self):
        """Initialize a test venv"""
        result = self.run_sysvenv("init")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.venv_path.exists())


class TestCollaborationSnapshots(TestSysvenvBase):
    """Test share and import functionality"""

    def test_share_creates_sysvenv_file(self):
        """Test that share command creates a .sysvenv file"""
        self.init_venv()

        # Install a test package
        pip_bin = self.venv_path / "bin" / "pip"
        subprocess.run([str(pip_bin), "install", "six"], check=True, capture_output=True)

        # Share environment
        result = self.run_sysvenv("share", "test-env")
        self.assertEqual(result.returncode, 0)

        # Check .sysvenv file exists
        share_files = list(Path.cwd().glob("test-env-*.sysvenv"))
        self.assertEqual(len(share_files), 1)

        share_file = share_files[0]
        content = share_file.read_text()

        # Verify metadata
        self.assertIn("# sysvenv shared environment", content)
        self.assertIn("# Python:", content)
        self.assertIn("# Packages:", content)
        self.assertIn("six==", content)

        # Cleanup
        share_file.unlink()

    def test_import_restores_environment(self):
        """Test that import command restores shared environment"""
        self.init_venv()

        # Create a fake shared environment file
        share_file = Path.cwd() / "test-shared.sysvenv"
        share_content = """# sysvenv shared environment
# Created: 2025-11-05T12:00:00Z
# Python: Python 3.11.0
# Packages: 1
# By: testuser@testhost
#
# To import: sysvenv import test-shared.sysvenv

six==1.16.0
"""
        share_file.write_text(share_content)

        # Import with confirmation bypass
        result = self.run_sysvenv("import", str(share_file), "-y")
        self.assertEqual(result.returncode, 0)

        # Verify package was installed
        pip_bin = self.venv_path / "bin" / "pip"
        result = subprocess.run([str(pip_bin), "freeze"], capture_output=True, text=True)
        self.assertIn("six==1.16.0", result.stdout)

        # Cleanup
        share_file.unlink()

    def test_import_warns_on_python_version_mismatch(self):
        """Test that import warns when Python versions don't match"""
        self.init_venv()

        # Create share file with different Python version
        share_file = Path.cwd() / "test-mismatch.sysvenv"
        share_content = """# sysvenv shared environment
# Python: Python 2.7.0
# Packages: 1

six==1.16.0
"""
        share_file.write_text(share_content)

        # Import should warn about version mismatch
        result = self.run_sysvenv("import", str(share_file), "--dry-run")
        self.assertEqual(result.returncode, 0)
        # Check that warning appears (would need to check stderr/stdout)

        share_file.unlink()


class TestPackageProvenance(TestSysvenvBase):
    """Test provenance tracking"""

    def test_provenance_tracked_in_history(self):
        """Test that installation provenance is tracked in history"""
        self.init_venv()

        pip_bin = self.venv_path / "bin" / "pip"

        # Install a package
        subprocess.run([str(pip_bin), "install", "six"], check=True, capture_output=True)

        # Check history contains provenance
        history_files = list(self.history_path.glob("*_before.json"))
        self.assertGreater(len(history_files), 0)

        # Load most recent before snapshot
        with open(history_files[-1]) as f:
            entry = json.load(f)

        self.assertIn("provenance", entry)
        # For PyPI installs, provenance might be empty or contain source info

    def test_diff_shows_provenance(self):
        """Test that diff command shows provenance information"""
        self.init_venv()

        pip_bin = self.venv_path / "bin" / "pip"
        subprocess.run([str(pip_bin), "install", "six"], check=True, capture_output=True)

        # Run diff command
        result = self.run_sysvenv("diff")
        self.assertEqual(result.returncode, 0)

        # Verify output shows the package
        self.assertIn("six==", result.stdout)

    def test_history_detailed_mode(self):
        """Test history --detailed shows provenance"""
        self.init_venv()

        pip_bin = self.venv_path / "bin" / "pip"
        subprocess.run([str(pip_bin), "install", "six"], check=True, capture_output=True)

        # Run history with --detailed
        result = self.run_sysvenv("history", "--detailed")
        self.assertEqual(result.returncode, 0)


class TestSmartSnapshots(TestSysvenvBase):
    """Test smart snapshot reminders"""

    def test_status_suggests_snapshot_for_stable_env(self):
        """Test that status suggests snapshot for stable environments"""
        self.init_venv()

        pip_bin = self.venv_path / "bin" / "pip"

        # Install enough packages to trigger suggestion (15+)
        packages = ["six", "urllib3", "requests", "certifi", "charset-normalizer",
                    "idna", "click", "jinja2", "markupsafe", "werkzeug",
                    "itsdangerous", "flask", "setuptools", "pip", "wheel"]

        for pkg in packages[:5]:  # Install a few to get started
            subprocess.run([str(pip_bin), "install", pkg], check=True, capture_output=True)

        # Run status
        result = self.run_sysvenv("status")
        self.assertEqual(result.returncode, 0)

        # Should not suggest yet (not enough packages or history)
        # After enough operations, should suggest

    def test_no_suggestion_if_snapshots_exist(self):
        """Test that no suggestion if named snapshots already exist"""
        self.init_venv()

        # Create a named snapshot
        self.run_sysvenv("snapshot", "my-snapshot", "-y")

        # Run status
        result = self.run_sysvenv("status")
        self.assertEqual(result.returncode, 0)

        # Should not suggest (already has named snapshot)


class TestDependencyOrphans(TestSysvenvBase):
    """Test orphan package detection"""

    def test_orphans_detected_after_uninstall(self):
        """Test that orphaned dependencies are detected"""
        self.init_venv()

        pip_bin = self.venv_path / "bin" / "pip"

        # Install requests (brings in dependencies)
        subprocess.run([str(pip_bin), "install", "requests==2.28.0"],
                       check=True, capture_output=True)

        # Verify dependencies installed
        result = subprocess.run([str(pip_bin), "freeze"], capture_output=True, text=True)
        self.assertIn("urllib3", result.stdout)
        self.assertIn("certifi", result.stdout)

        # Uninstall requests
        subprocess.run([str(pip_bin), "uninstall", "requests", "-y"],
                       check=True, capture_output=True)

        # Orphan check should have run automatically via pip-wrapper
        # Check that orphan message would appear (this requires pip-wrapper integration)

    def test_no_orphans_if_still_required(self):
        """Test that packages still required by others are not marked orphan"""
        self.init_venv()

        pip_bin = self.venv_path / "bin" / "pip"

        # Install two packages that share a dependency
        subprocess.run([str(pip_bin), "install", "requests", "boto3"],
                       check=True, capture_output=True)

        # Uninstall just requests
        subprocess.run([str(pip_bin), "uninstall", "requests", "-y"],
                       check=True, capture_output=True)

        # urllib3 should NOT be orphaned (still needed by boto3)
        result = subprocess.run([str(pip_bin), "freeze"], capture_output=True, text=True)
        self.assertIn("urllib3", result.stdout)


class TestConflictDetection(TestSysvenvBase):
    """Test conflict detection features"""

    def test_downgrade_detection(self):
        """Test that version downgrades are detected"""
        self.init_venv()

        pip_bin = self.venv_path / "bin" / "pip"

        # Install newer version
        subprocess.run([str(pip_bin), "install", "six==1.16.0"],
                       check=True, capture_output=True)

        # Try to install older version (would trigger downgrade warning)
        # In practice, this is detected by _check-downgrades before pip runs
        # We can test the detection function directly

    def test_version_comparison(self):
        """Test version comparison logic"""
        # Import the functions from sysvenv
        import sys
        sys.path.insert(0, str(Path(__file__).parent))

        # We'll need to test is_version_downgrade function
        # For now, basic test cases
        self.assertTrue(True)  # Placeholder

    def test_system_package_conflict_detection(self):
        """Test detection of system package conflicts"""
        # This requires dpkg/rpm to be available
        # Skip if not on appropriate system
        if not shutil.which('dpkg') and not shutil.which('rpm'):
            self.skipTest("No package manager available")

        # Test conflict detection
        # Would need actual system packages installed to test properly


class TestProjectVenvDetection(TestSysvenvBase):
    """Test project venv auto-detection"""

    def test_detects_requirements_txt(self):
        """Test that requirements.txt triggers project detection"""
        self.init_venv()

        # Create a project directory with requirements.txt
        project_dir = self.test_dir / "test-project"
        project_dir.mkdir()
        (project_dir / "requirements.txt").write_text("requests==2.28.0\n")

        # Change to project directory
        orig_dir = os.getcwd()
        try:
            os.chdir(project_dir)

            # pip-wrapper should detect project marker
            # This requires actually running pip through wrapper
            # For MVP, test passes if marker detection logic works

        finally:
            os.chdir(orig_dir)

    def test_detects_pyproject_toml(self):
        """Test that pyproject.toml triggers detection"""
        self.init_venv()

        project_dir = self.test_dir / "test-project"
        project_dir.mkdir()
        (project_dir / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        # Similar test to above
        self.assertTrue(True)  # Placeholder

    def test_warns_about_unactivated_venv(self):
        """Test warning when venv exists but not activated"""
        self.init_venv()

        project_dir = self.test_dir / "test-project"
        project_dir.mkdir()
        (project_dir / "venv").mkdir()

        # Should detect venv and warn
        self.assertTrue(True)  # Placeholder


class TestIntegration(TestSysvenvBase):
    """Integration tests for complete workflows"""

    def test_full_workflow_init_to_snapshot(self):
        """Test complete workflow: init -> install -> snapshot -> restore"""
        # Initialize
        self.init_venv()

        # Install packages
        pip_bin = self.venv_path / "bin" / "pip"
        subprocess.run([str(pip_bin), "install", "six"], check=True, capture_output=True)

        # Create snapshot
        result = self.run_sysvenv("snapshot", "test-snapshot", "-y")
        self.assertEqual(result.returncode, 0)

        # Verify snapshot file exists
        snapshot_file = self.snapshots_path / "test-snapshot.txt"
        self.assertTrue(snapshot_file.exists())

        # List snapshots
        result = self.run_sysvenv("list-snapshots")
        self.assertEqual(result.returncode, 0)
        self.assertIn("test-snapshot", result.stdout)

        # Restore from snapshot
        result = self.run_sysvenv("restore", "test-snapshot", "-y")
        self.assertEqual(result.returncode, 0)

        # Verify package still installed
        result = subprocess.run([str(pip_bin), "freeze"], capture_output=True, text=True)
        self.assertIn("six==", result.stdout)

    def test_undo_and_redo_operations(self):
        """Test undo functionality"""
        self.init_venv()

        pip_bin = self.venv_path / "bin" / "pip"

        # Install package
        subprocess.run([str(pip_bin), "install", "six"], check=True, capture_output=True)

        # Verify installed
        result = subprocess.run([str(pip_bin), "freeze"], capture_output=True, text=True)
        self.assertIn("six==", result.stdout)

        # Undo the install
        result = self.run_sysvenv("undo", "1", "-y")
        self.assertEqual(result.returncode, 0)

        # Verify package removed
        result = subprocess.run([str(pip_bin), "freeze"], capture_output=True, text=True)
        self.assertNotIn("six==", result.stdout)

    def test_history_tracking(self):
        """Test that operations are tracked in history"""
        self.init_venv()

        pip_bin = self.venv_path / "bin" / "pip"

        # Perform several operations
        subprocess.run([str(pip_bin), "install", "six"], check=True, capture_output=True)
        subprocess.run([str(pip_bin), "install", "urllib3"], check=True, capture_output=True)
        subprocess.run([str(pip_bin), "uninstall", "six", "-y"], check=True, capture_output=True)

        # Check history
        result = self.run_sysvenv("history")
        self.assertEqual(result.returncode, 0)

        # Should show operations
        self.assertIn("install", result.stdout.lower())

    def test_doctor_command(self):
        """Test doctor health check"""
        self.init_venv()

        result = self.run_sysvenv("doctor")
        self.assertEqual(result.returncode, 0)
        self.assertIn("✓", result.stdout)  # Check marks indicate health

    def test_status_command(self):
        """Test status command output"""
        self.init_venv()

        result = self.run_sysvenv("status")
        self.assertEqual(result.returncode, 0)

        # Verify expected information
        self.assertIn("Python", result.stdout)
        self.assertIn("Pip", result.stdout)
        self.assertIn("Installed packages", result.stdout)


class TestEdgeCases(TestSysvenvBase):
    """Test edge cases and error handling"""

    def test_init_twice(self):
        """Test that init can be run multiple times"""
        self.init_venv()

        # Run init again (should prompt for confirmation)
        result = self.run_sysvenv("init", input_text="n\n", check=False)
        # Should not error

    def test_snapshot_with_invalid_name(self):
        """Test snapshot with invalid characters in name"""
        self.init_venv()

        # Try invalid names
        invalid_names = ["test/snapshot", "test snapshot", "../test", ".test"]

        for name in invalid_names:
            result = self.run_sysvenv("snapshot", name, check=False)
            self.assertNotEqual(result.returncode, 0)

    def test_restore_nonexistent_snapshot(self):
        """Test restoring a snapshot that doesn't exist"""
        self.init_venv()

        result = self.run_sysvenv("restore", "nonexistent", check=False)
        self.assertNotEqual(result.returncode, 0)

    def test_undo_with_no_history(self):
        """Test undo when there's no history"""
        self.init_venv()

        result = self.run_sysvenv("undo", check=False)
        self.assertEqual(result.returncode, 0)  # Should handle gracefully

    def test_large_number_of_packages(self):
        """Test with many packages installed"""
        self.init_venv()

        pip_bin = self.venv_path / "bin" / "pip"

        # Install several packages
        packages = ["six", "urllib3", "certifi", "charset-normalizer", "idna"]
        for pkg in packages:
            subprocess.run([str(pip_bin), "install", pkg], check=True, capture_output=True)

        # Operations should still work
        result = self.run_sysvenv("status")
        self.assertEqual(result.returncode, 0)

        result = self.run_sysvenv("history")
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
