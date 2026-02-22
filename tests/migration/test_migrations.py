"""
Alembic migration tests.

These tests verify that database migrations can be applied and rolled back cleanly.
Marked as integration tests since they require a real PostgreSQL database.

Run with: pytest tests/migration/ -v -m integration
"""

import subprocess
import sys

import pytest


pytestmark = pytest.mark.integration


class TestAlembicMigrations:
    """Verify Alembic migrations work correctly."""

    def test_upgrade_head(self):
        """Running 'alembic upgrade head' must succeed."""
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/home/basitdev/Me/StudioProjects/VoiceNoteAPI",
        )
        assert result.returncode == 0, (
            f"alembic upgrade head failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_current_shows_head(self):
        """After upgrade head, 'alembic current' must show (head)."""
        # First ensure we're at head
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/home/basitdev/Me/StudioProjects/VoiceNoteAPI",
        )

        result = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd="/home/basitdev/Me/StudioProjects/VoiceNoteAPI",
        )
        assert result.returncode == 0, (
            f"alembic current failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "(head)" in result.stdout, (
            f"Expected '(head)' in output, got: {result.stdout}"
        )

    def test_downgrade_upgrade_roundtrip(self):
        """Downgrade one revision then upgrade back to head must succeed."""
        # Ensure at head first
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/home/basitdev/Me/StudioProjects/VoiceNoteAPI",
        )

        # Downgrade one revision
        result_down = subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "-1"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/home/basitdev/Me/StudioProjects/VoiceNoteAPI",
        )
        assert result_down.returncode == 0, (
            f"alembic downgrade -1 failed:\nstdout: {result_down.stdout}\nstderr: {result_down.stderr}"
        )

        # Upgrade back to head
        result_up = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/home/basitdev/Me/StudioProjects/VoiceNoteAPI",
        )
        assert result_up.returncode == 0, (
            f"alembic upgrade head (after downgrade) failed:\n"
            f"stdout: {result_up.stdout}\nstderr: {result_up.stderr}"
        )
