"""
Schema Validation Utility

Validates that the database schema matches the SQLAlchemy models.
Helps catch schema drift and migration issues early.
"""

import sys
from typing import List, Tuple

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import sync_engine as engine


class SchemaValidator:
    """Validates database schema against SQLAlchemy models"""

    def __init__(self, db_session: Session = None):
        self.engine = engine
        self.inspector = inspect(self.engine)
        self.mismatches = []
        self.warnings = []

    def validate_all_models(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate all models against database schema.

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        # Get all model classes
        model_classes = [
            models.User,
            models.Note,
            models.Task,
            models.Wallet,
            models.Transaction,
            models.ServicePlan,
            models.UsageLog,
            models.SystemSettings,
            models.AdminActionLog,
        ]

        for model_class in model_classes:
            self._validate_model(model_class)

        is_valid = len(self.mismatches) == 0
        return is_valid, self.mismatches, self.warnings

    def _validate_model(self, model_class):
        """Validate a single model against its database table"""
        table_name = model_class.__tablename__

        # Check if table exists
        if not self.inspector.has_table(table_name):
            self.mismatches.append(
                f"❌ Table '{table_name}' does not exist in database"
            )
            return

        # Get database columns
        db_columns = {
            col["name"]: col for col in self.inspector.get_columns(table_name)
        }

        # Get model columns
        model_columns = {col.name: col for col in model_class.__table__.columns}

        # Check for missing columns in database
        for col_name, col_obj in model_columns.items():
            if col_name not in db_columns:
                self.mismatches.append(
                    f"❌ Column '{table_name}.{col_name}' exists in model but not in database"
                )

        # Check for extra columns in database (warnings only)
        for col_name in db_columns:
            if col_name not in model_columns:
                self.warnings.append(
                    f"⚠️  Column '{table_name}.{col_name}' exists in database but not in model"
                )

        # Validate foreign keys
        db_fks = self.inspector.get_foreign_keys(table_name)
        model_fks = [fk for fk in model_class.__table__.foreign_keys]

        if len(db_fks) != len(model_fks):
            self.warnings.append(
                f"⚠️  Table '{table_name}' has {len(db_fks)} foreign keys in DB but {len(model_fks)} in model"
            )

    def print_report(self):
        """Print validation report to stdout"""
        print("\n" + "=" * 60)
        print("📊 DATABASE SCHEMA VALIDATION REPORT")
        print("=" * 60 + "\n")

        if not self.mismatches and not self.warnings:
            print("✅ All models match database schema perfectly!\n")
            return

        if self.mismatches:
            print(f"🔴 ERRORS ({len(self.mismatches)}):")
            print("-" * 60)
            for error in self.mismatches:
                print(f"  {error}")
            print()

        if self.warnings:
            print(f"🟡 WARNINGS ({len(self.warnings)}):")
            print("-" * 60)
            for warning in self.warnings:
                print(f"  {warning}")
            print()

        print("=" * 60)

        if self.mismatches:
            print(
                "\n💡 Recommendation: Run 'alembic upgrade head' to apply pending migrations"
            )
            print(
                "   Or generate a new migration with 'alembic revision --autogenerate'\n"
            )


def validate_schema() -> bool:
    """
    Main validation function.

    Returns:
        True if schema is valid, False otherwise
    """
    validator = SchemaValidator()
    is_valid, errors, warnings = validator.validate_all_models()
    validator.print_report()

    return is_valid


if __name__ == "__main__":
    # Run validation
    is_valid = validate_schema()
    sys.exit(0 if is_valid else 1)
