"""
Pytest configuration for AI utilities tests

Simplified config that doesn't require database setup
"""

import pytest

# Disable database setup for utility-only tests
pytest.mark.asyncio_mode = "auto"
