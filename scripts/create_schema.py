#!/usr/bin/env python3
"""
Create database schema from SQLAlchemy models
This script creates all tables defined in the models
"""

import os
import sys

# Set database URL to test database
os.environ['DATABASE_URL'] = 'postgresql://postgres:password@db:5432/voicenote_test'

from sqlalchemy import create_engine
from app.models.user import User
from app.models.note import Note
from app.models.task import Task
from app.models.base import Base

# Create engine
engine = create_engine(os.environ['DATABASE_URL'])

# Create all tables
print("Creating all tables from SQLAlchemy models...")
Base.metadata.create_all(engine)

print("✓ Database schema created successfully!")

# List created tables
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"\nCreated {len(tables)} tables:")
for table in sorted(tables):
    print(f"  - {table}")
