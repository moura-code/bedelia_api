# Bedelia API - ORM Database Integration

This project has been migrated from using pure SQL and JSON file storage to a comprehensive ORM-based approach using SQLAlchemy with PostgreSQL.

## What Changed

### Before (Pure SQL/JSON)
- Data was scraped and saved to JSON files (`table_data.json`, `previas_data.json`)
- No database integration in the scraper
- Manual SQL queries would be needed to interact with data

### After (ORM Integration)
- Data is scraped and stored directly in PostgreSQL database using SQLAlchemy ORM
- Comprehensive database models based on the existing schema
- Automatic database table creation and management
- Rich relationship mapping between entities
- JSON files are still created as backups

## New Architecture

### Core Components

1. **`models.py`** - SQLAlchemy ORM models
   - Complete mapping of the PostgreSQL schema
   - All tables, relationships, and constraints
   - Enums for controlled vocabularies

2. **`database.py`** - Database connection management
   - Session management with context managers
   - Connection pooling and error handling
   - Database initialization utilities

3. **`data_parser.py`** - Data parsing and storage
   - Converts scraped data to ORM objects
   - Handles duplicate detection and updates
   - Maintains data integrity through relationships

4. **`db_setup.py`** - Database management utility
   - Setup, drop, test database operations
   - Statistics and data inspection
   - JSON import/export functionality

## Database Models

The ORM includes complete models for:

- **Programs** - Academic programs/plans
- **Subjects** - Individual courses/subjects  
- **Subject Aliases** - Alternative names/codes for subjects
- **Offerings** - Specific course/exam instances
- **Offering Links** - Associated URLs and resources
- **Requirement Groups** - Hierarchical prerequisite groups
- **Requirement Items** - Individual prerequisite items
- **Subject Equivalences** - Course equivalencies
- **Dependency Edges** - Materialized prerequisite relationships
- **Audit Sources** - Scraping audit trail

## Setup Instructions

### 1. Install Dependencies

```bash
cd scraper
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bedelia
DB_USER=postgres
DB_PASSWORD=your_password

# Scraper Authentication
DOCUMENTO=your_document_number
CONTRASENA=your_password

# Optional Settings
DEBUG=false
BROWSER=firefox
DB_ECHO=false
```

### 3. Setup Database

```bash
# Test database connection
python db_setup.py test

# Initialize database (creates tables and enums)
python db_setup.py setup

# Check database statistics
python db_setup.py stats
```

### 4. Run Scraper

```bash
python main.py
```

## Database Management

### Using the db_setup.py utility:

```bash
# Setup database (create tables)
python db_setup.py setup

# Test connection
python db_setup.py test

# Show statistics
python db_setup.py stats

# List subjects (first 10)
python db_setup.py list

# List more subjects
python db_setup.py list --limit 50

# Import from JSON backup
python db_setup.py import --file table_data_backup.json

# Drop all tables (DANGEROUS!)
python db_setup.py drop
```

## Key Benefits

### 1. **Type Safety & Validation**
- SQLAlchemy models provide type checking
- Database constraints enforce data integrity
- Enum types prevent invalid values

### 2. **Relationship Management**
- Automatic foreign key management
- Cascade deletions where appropriate
- Easy navigation between related entities

### 3. **Performance**
- Connection pooling reduces overhead
- Indexed queries for common operations
- Materialized views for complex relationships

### 4. **Maintainability**
- Clear separation of concerns
- Comprehensive logging throughout
- Error handling and recovery

### 5. **Flexibility**
- Easy to add new fields or relationships
- Migration support through Alembic
- Both ORM and raw SQL query support

## Usage Examples

### Querying Data

```python
from database import get_db_session
from models import Subject, Offering

# Find a subject by code
with get_db_session() as session:
    subject = session.query(Subject).filter(
        Subject.code == 'CP1'
    ).first()
    
    if subject:
        print(f"Found: {subject.name}")
        
        # Get all offerings for this subject
        for offering in subject.offerings:
            print(f"  - {offering.type} ({offering.term})")

# Count active offerings
with get_db_session() as session:
    active_count = session.query(Offering).filter(
        Offering.is_active == True
    ).count()
    
    print(f"Active offerings: {active_count}")
```

### Adding New Data

```python
from database import get_db_session
from models import Program, Subject

with get_db_session() as session:
    # Create a program
    program = Program(
        name="Ingeniería en Computación",
        plan_year=2024
    )
    session.add(program)
    session.flush()  # Get the ID
    
    # Create a subject
    subject = Subject(
        code="ING001",
        name="Introducción a la Ingeniería",
        program_id=program.id,
        credits=4,
        semester=1
    )
    session.add(subject)
    # Commit happens automatically with context manager
```

## Migration Notes

- Existing JSON files are preserved as backups
- The scraper now runs both data storage methods (database + JSON backup)
- All original scraping functionality is maintained
- Database schema matches the original `db.sql` specification

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Verify PostgreSQL is running
   - Check database credentials in `.env`
   - Ensure database exists and user has permissions

2. **Import Errors**
   - Check that all dependencies are installed
   - Verify Python path includes the scraper directory
   - Check for missing environment variables

3. **Enum Creation Errors**
   - These are usually safe to ignore on first run
   - The system will create enums if they don't exist

### Getting Help

Check logs for detailed error messages:
```bash
python main.py 2>&1 | tee scraper.log
```

The system provides comprehensive logging at each step to help diagnose issues.
