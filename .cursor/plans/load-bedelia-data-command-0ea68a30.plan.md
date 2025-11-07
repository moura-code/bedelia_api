<!-- 0ea68a30-f7dc-47f5-8a8d-36e44b6f4fae 7c2e6014-5c9e-4aa0-a83d-c5e6c59075bb -->
# Update PosPrevias with Retry Logic and Progress Saving

## Overview

Refactor the PosPrevias scraper to match the improved Previas implementation with retry logic, incremental saving, and resume functionality.

## Implementation Steps

### 1. Add Helper Methods

Copy the same helper methods from Previas:

- `_load_backup_data()` - Load existing backup with error handling
- `_save_backup_data()` - Save data to JSON with UTF-8 encoding
- `_process_plan_with_retry()` - Process single plan with retry logic (3 attempts)

### 2. Refactor Main run() Method

Similar structure to Previas:

- Load existing backup at start
- Get all available plans
- Loop through plans, skipping already processed ones
- Call `_process_plan_with_retry()` for each plan
- Save backup after each successful plan
- Continue to next plan if one fails
- Log progress with ✓ and ✗ symbols

### 3. Move Plan Processing Logic

Extract the current plan processing code into `_process_plan_with_retry()`:

- Navigate to plan section
- Get total pages
- Loop through pages
- Extract posprevias data
- Handle Selenium errors with retries
- Return data for the plan

### 4. Fix Row Selection

Update row XPATH to include both even and odd classes (like Previas):

```python
'//tr[contains(@class, "ui-datatable-even") or contains(@class, "ui-datatable-odd")]'
```

### 5. Add Retry Logic for Stale Elements

Similar to Previas, add retry loops for:

- Extracting row cell data
- Re-finding elements after navigation
- Handling modal overlays

### 6. Use Proper Backup File Name

Use `posprevias_data_backup.json` consistently

## Files to Modify

- `scraper/pages/posprevias.py` - Complete refactor

## Testing

- Run and verify it saves after each plan
- Stop and restart to verify resume works
- Check logging shows retry attempts

### To-dos

- [ ] Create __init__.py in management/commands directory
- [ ] Create load_bedelia.py command skeleton with BaseCommand structure
- [ ] Implement Phase 1: credits.json import (Program + Subject creation)
- [ ] Implement Phase 2: requirements.json import (Offering + RequirementGroup tree)
- [ ] Implement Phase 3: posprevias.json import (inverse requirement relationships)
- [ ] Add helper methods for subject code extraction and credit parsing
- [ ] Add comprehensive logging and error handling
- [ ] Test command with --dry-run and verify database state