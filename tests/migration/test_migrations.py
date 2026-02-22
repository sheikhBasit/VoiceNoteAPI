"""
Alembic migration tests.

These tests verify that database migrations can be applied and rolled back cleanly.
They require a live PostgreSQL database (the Docker DB on port 5433).

Run with: pytest tests/migration/ -v -m integration
      OR: docker exec voicenote_api python -m pytest tests/migration/ -v
"""

import os
import subprocess
import sys

import pytest


# ---------------------------------------------------------------------------
# Module-level skip guard — skip when PostgreSQL is not reachable
# ---------------------------------------------------------------------------

def _postgres_is_up() -> bool:
    """Return True if the project's PostgreSQL instance is reachable."""
    try:
        import sqlalchemy

        # Honour a custom DATABASE_URL if set, but never run on SQLite
        url = os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:password@localhost:5433/voicenote",
        )
        if "sqlite" in url:
            return False

        engine = sqlalchemy.create_engine(
            url, connect_args={"connect_timeout": 3}
        )
        with engine.connect():
            pass
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _postgres_is_up(),
        reason=(
            "PostgreSQL not reachable — start the Docker DB first: "
            "docker compose up -d db"
        ),
    ),
]


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
