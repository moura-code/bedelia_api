"""
Database connection and session management for Bedelia scraper.

This module provides utilities for connecting to PostgreSQL database
and managing SQLAlchemy sessions.
"""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from models import Base
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and sessions"""

    def __init__(self, database_url: str = None):
        """
        Initialize database manager with connection URL.

        Args:
            database_url: PostgreSQL connection URL. If None, constructs from env vars.
        """
        if database_url is None:
            database_url = self._build_database_url()

        self.engine = create_engine(
            database_url,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections after 1 hour
        )

        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def _build_database_url(self) -> str:
        """Build database URL from environment variables."""
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "bedelia")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")

        if not all([db_host, db_port, db_name, db_user]):
            raise ValueError(
                "Missing required database environment variables. "
                "Please set DB_HOST, DB_PORT, DB_NAME, DB_USER, and optionally DB_PASSWORD."
            )

        return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    def create_tables(self):
        """Create all tables defined in models."""
        try:
            # First create the enums if they don't exist
            self._create_enums()

            # Then create all tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Successfully created all database tables")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def _create_enums(self):
        """Create PostgreSQL enums if they don't exist."""
        enum_definitions = [
            "CREATE TYPE offering_type AS ENUM ('COURSE','EXAM');",
            "CREATE TYPE group_scope AS ENUM ('ALL','ANY','NONE');",
            """CREATE TYPE group_flavor AS ENUM (
                'GENERIC', 'APPROVALS', 'ACTIVITIES', 'COURSE_APPROVED',
                'COURSE_ENROLLED', 'EXAM_APPROVED', 'EXAM_ENROLLED',
                'COURSE_CREDITED', 'EXAM_CREDITED'
            );""",
            "CREATE TYPE req_condition AS ENUM ('APPROVED','ENROLLED','CREDITED');",
            "CREATE TYPE target_type AS ENUM ('SUBJECT','OFFERING');",
            """CREATE TYPE dep_kind AS ENUM (
                'REQUIRES_ALL', 'ALTERNATIVE_ANY', 'FORBIDDEN_NONE'
            );""",
        ]

        with self.engine.connect() as conn:
            for enum_def in enum_definitions:
                try:
                    # Check if type exists first
                    type_name = enum_def.split()[2]  # Extract type name
                    exists_query = text("""
                        SELECT EXISTS (
                            SELECT 1 FROM pg_type WHERE typname = :type_name
                        )
                    """)
                    result = conn.execute(
                        exists_query, {"type_name": type_name}
                    ).scalar()

                    if not result:
                        conn.execute(text(enum_def))
                        logger.info(f"Created enum type: {type_name}")
                except Exception as e:
                    logger.warning(f"Could not create enum {type_name}: {e}")

            conn.commit()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.

        Usage:
            with db_manager.get_session() as session:
                # Use session here
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def get_session_sync(self) -> Session:
        """
        Get a database session for manual management.
        Note: Remember to close the session when done.
        """
        return self.SessionLocal()

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                logger.info("Database connection test successful")
                return result == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def close(self):
        """Close the database engine."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine closed")


# Global database manager instance
db_manager = None


def get_db_manager() -> DatabaseManager:
    """Get or create the global database manager instance."""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager


def init_database():
    """Initialize database with tables and setup."""
    manager = get_db_manager()

    # Test connection
    if not manager.test_connection():
        raise RuntimeError("Cannot connect to database")

    # Create tables
    manager.create_tables()
    logger.info("Database initialized successfully")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Convenience function to get a database session."""
    manager = get_db_manager()
    with manager.get_session() as session:
        yield session
