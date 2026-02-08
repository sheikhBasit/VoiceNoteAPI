#!/usr/bin/env python3
"""
CLI Script to validate database schema against SQLAlchemy models.

Usage:
    python scripts/validate_schema.py
    
Exit Codes:
    0 - Schema is valid
    1 - Schema has errors
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.utils.schema_validator import validate_schema

if __name__ == "__main__":
    is_valid = validate_schema()
    sys.exit(0 if is_valid else 1)
