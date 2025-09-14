#!/usr/bin/env python3
"""
Database setup and management utility for Bedelia scraper.

This script provides utilities for setting up, managing, and querying
the PostgreSQL database using SQLAlchemy ORM.
"""

import sys
import argparse
import logging
from OCR.database import DatabaseManager, init_database
from OCR.models import Base, Subject, Offering, Program
from OCR.data_parser import DataParser

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_database():
    """Initialize database with all tables and enums."""
    try:
        logger.info("Setting up database...")
        init_database()
        logger.info("Database setup completed successfully!")
        return True
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return False


def drop_database():
    """Drop all tables (DANGEROUS!)."""
    response = input("WARNING: This will delete ALL data! Type 'yes' to confirm: ")
    if response.lower() != "yes":
        logger.info("Operation cancelled.")
        return False

    try:
        manager = DatabaseManager()
        Base.metadata.drop_all(bind=manager.engine)
        logger.info("All tables dropped successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        return False


def test_connection():
    """Test database connection."""
    try:
        manager = DatabaseManager()
        if manager.test_connection():
            logger.info("✅ Database connection successful!")
            return True
        else:
            logger.error("❌ Database connection failed!")
            return False
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        return False


def show_stats():
    """Show database statistics."""
    try:
        manager = DatabaseManager()
        with manager.get_session() as session:
            programs_count = session.query(Program).count()
            subjects_count = session.query(Subject).count()
            offerings_count = session.query(Offering).count()

            logger.info("📊 Database Statistics:")
            logger.info(f"  Programs: {programs_count}")
            logger.info(f"  Subjects: {subjects_count}")
            logger.info(f"  Offerings: {offerings_count}")

            return True
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return False


def list_subjects(limit=10):
    """List subjects in database."""
    try:
        manager = DatabaseManager()
        with manager.get_session() as session:
            subjects = session.query(Subject).limit(limit).all()

            if not subjects:
                logger.info("No subjects found in database.")
                return True

            logger.info(f"📚 First {limit} subjects:")
            for subject in subjects:
                logger.info(f"  {subject.code} - {subject.name}")

            return True
    except Exception as e:
        logger.error(f"Failed to list subjects: {e}")
        return False


def import_json_data(json_file):
    """Import data from JSON backup file."""
    try:
        import json

        logger.info(f"Importing data from {json_file}...")

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        parser = DataParser()

        if json_file.endswith("table_data.json") or json_file.endswith(
            "table_data_backup.json"
        ):
            # Import subjects data
            subjects_count, offerings_count = parser.store_scraped_data(
                data, program_name="Imported Program"
            )
            logger.info(
                f"Imported {subjects_count} subjects and {offerings_count} offerings"
            )

        elif json_file.endswith("previas_data.json") or json_file.endswith(
            "previas_data_backup.json"
        ):
            # Import prerequisites data
            requirements_count = parser.store_previas_data(data)
            logger.info(f"Imported {requirements_count} prerequisite requirements")

        else:
            logger.warning(f"Unknown JSON format: {json_file}")
            return False

        return True

    except FileNotFoundError:
        logger.error(f"File not found: {json_file}")
        return False
    except Exception as e:
        logger.error(f"Failed to import data: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Bedelia Database Management Utility")
    parser.add_argument(
        "action",
        choices=["setup", "drop", "test", "stats", "list", "import"],
        help="Action to perform",
    )

    parser.add_argument("--file", help="JSON file to import (for import action)")
    parser.add_argument("--limit", type=int, default=10, help="Limit for list action")

    args = parser.parse_args()

    success = False

    if args.action == "setup":
        success = setup_database()
    elif args.action == "drop":
        success = drop_database()
    elif args.action == "test":
        success = test_connection()
    elif args.action == "stats":
        success = show_stats()
    elif args.action == "list":
        success = list_subjects(args.limit)
    elif args.action == "import":
        if not args.file:
            logger.error("--file argument required for import action")
            sys.exit(1)
        success = import_json_data(args.file)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
