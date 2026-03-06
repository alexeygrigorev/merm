"""Smoke tests for project setup."""

import subprocess


class TestCLI:
    """Test CLI entry point."""

    def test_cli_help(self):
        result = subprocess.run(
            ["uv", "run", "merm", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = (result.stdout + result.stderr).lower()
        assert "merm" in output or "usage" in output
