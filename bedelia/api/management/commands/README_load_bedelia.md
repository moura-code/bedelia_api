# Load Bedelia Command

Django management command to import Bedelia course data from JSON files into the database.

## Installation

The command is located at: `bedelia/api/management/commands/load_bedelia.py`

## Usage

```bash
cd bedelia
python manage.py load_bedelia \
    --credits ../data/credits.json \
    --requirements ../data/requirements.json \
    --posprevias ../data/posprevias.json \
    --default-term 2025S1 \
    [--dry-run] \
    [--verbose]
```

### Arguments

- `--credits` (required): Path to credits.json file containing subject codes, names, and credits
- `--requirements` (required): Path to requirements.json file containing prerequisite trees
- `--posprevias` (required): Path to posprevias.json file containing forward dependencies
- `--default-term` (optional): Default term for offerings (default: 2025S1)
- `--dry-run` (optional): Run without saving to database (useful for testing)
- `--verbose` (optional): Show detailed progress messages

## What It Does

The command processes data in three phases:

### Phase 1: Credits (Subjects)
- Loads all subjects from `credits.json`
- Creates a default Program record
- Parses credit values (handles special formats like "OPTATIVA - 4")
- Creates Subject records with code, name, and credits

### Phase 2: Requirements (Previas)
- Loads prerequisite trees from `requirements.json`
- Creates Offering records (Course or Exam type)
- Builds hierarchical RequirementGroup structures:
  - `ALL` groups: all children required
  - `ANY` groups: min_required children needed
  - `NONE` groups: forbidden requirements
- Creates RequirementItem records linking to subjects
- Handles complex nested requirement structures

### Phase 3: PosPrevias (Forward Dependencies)
- Loads forward dependencies from `posprevias.json`
- For each subject, finds what courses it unlocks
- Creates inverse requirement relationships
- Example: if subject A is in B's posprevias, then B requires A

## Output

The command displays:
- Progress for each phase
- Warnings for missing subjects or unparseable data
- Final summary with counts:
  - Programs created
  - Subjects created
  - Offerings created
  - Requirement groups created
  - Requirement items created
  - Warnings and errors

## Example Output

```
Running in DRY-RUN mode - no changes will be saved
Loading JSON files...

=== Phase 1: Loading Credits (Subjects) ===

=== Phase 2: Loading Requirements (Previas) ===

=== Phase 3: Processing PosPrevias ===
WARNING: Target subject not found: 1946
...

============================================================
Import Summary
============================================================
Programs created: 1
Subjects created: 632
Offerings created: 215
Requirement groups created: 458
Requirement items created: 1247
Warnings: 1973
Errors: 0
============================================================
```

## Notes

- The command is idempotent - safe to run multiple times
- Uses database transactions (all-or-nothing)
- Warnings about missing subjects are normal (posprevias references subjects not in credits.json)
- Always test with `--dry-run` first
- Credits parsing handles special formats automatically

## Database Models Populated

- **Program**: Academic programs/plans
- **Subject**: Courses with codes, names, credits
- **Offering**: Course/Exam instances per term
- **RequirementGroup**: Groups of requirements (ALL/ANY/NONE logic)
- **RequirementGroupLink**: Links between groups (tree structure)
- **RequirementItem**: Individual prerequisite items

## Troubleshooting

**Problem**: Many warnings about missing subjects  
**Solution**: This is normal. `posprevias.json` references subjects that may not be in `credits.json`

**Problem**: Import fails partway through  
**Solution**: Check database constraints. The transaction will roll back automatically.

**Problem**: Encoding errors on Windows  
**Solution**: The command has been updated to avoid Unicode characters in output

## Future Enhancements

- Auto-detect programs from subject data
- Handle subject aliases better
- Import historical equivalencies
- Support incremental updates

