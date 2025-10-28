# Bedelia API - Postman Collection Guide

This document explains how to use the Postman collection for testing the Bedelia API.

## Import the Collection

1. Open Postman
2. Click **Import** in the top left
3. Select the file `bedelia_api_postman_collection.json`
4. The collection will be imported with all endpoints organized in folders

## Collection Structure

The collection includes **8 main folders**, each representing a different resource:

### 1. Programs
- List all academic programs
- Get program details by ID
- Filter by plan year
- Search by name

### 2. Subjects
- List all subjects/courses
- Get subject details (includes offerings and aliases)
- Filter by program, credits, semester
- Search by code or name

### 3. Offerings
- List all course/exam offerings
- Get offering details (includes requirement groups)
- **Custom action**: Get full requirement tree (recursive)
- **Custom action**: Search by requirement patterns
- Filter by subject, type (COURSE/EXAM), term, active status
- Search by subject code/name

### 4. Requirement Groups
- List all requirement groups
- Get group details (includes items and child links)
- Filter by offering, scope (ALL/ANY/NONE), flavor, min_required

### 5. Requirement Group Links
- List all parent-child links between requirement groups
- Get link details
- Filter by parent or child group

### 6. Requirement Items
- List all requirement items (leaf requirements)
- Get item details
- Filter by group, target type, target subject/offering, condition
- Search by alternative code or label

### 7. Subject Equivalences
- List all subject equivalences
- Get equivalence details
- Filter by subject_a, subject_b, or kind (FULL/PARTIAL)

### 8. Dependency Edges
- List all dependency edges between offerings
- Get edge details
- Filter by source/target offering or dependency kind

## Variables

The collection uses variables to make testing easier. After importing, you can set these in the collection variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `base_url` | API base URL | `http://localhost:8000/api` |
| `program_id` | UUID of a program | Copy from API response |
| `subject_id` | UUID of a subject | Copy from API response |
| `offering_id` | UUID of an offering | Copy from API response |
| `group_id` | UUID of a requirement group | Copy from API response |
| `link_id` | UUID of a group link | Copy from API response |
| `item_id` | UUID of a requirement item | Copy from API response |
| `equivalence_id` | UUID of an equivalence | Copy from API response |
| `edge_id` | UUID of a dependency edge | Copy from API response |

### How to Set Variables

1. Right-click the collection name
2. Select **Edit**
3. Go to the **Variables** tab
4. Update the **Current Value** column
5. Click **Save**

## Getting Started

### Step 1: Start the Django Server

```bash
cd bedelia
python manage.py runserver
```

### Step 2: Load Sample Data

```bash
python manage.py load_bedelia \
    --credits ../data/credits.json \
    --requirements ../data/requirements.json \
    --posprevias ../data/posprevias.json \
    --default-term 2025S1
```

### Step 3: Test Basic Endpoints

1. **List Programs**: Send `Programs > List all programs`
2. Copy a `program_id` from the response
3. **Get Program**: Send `Programs > Get program by ID` (uses the variable)
4. Repeat for subjects, offerings, etc.

## Advanced Usage Examples

### Example 1: Find All Exams

**Request**: `Offerings > Filter by type (COURSE or EXAM)`
- Set `type` parameter to `EXAM`

### Example 2: Search Calculus Courses

**Request**: `Subjects > Search by code or name`
- Set `search` parameter to `CALCULO`

### Example 3: Get Full Requirement Tree

**Request**: `Offerings > Get requirement tree`
- First get an offering_id from `Offerings > List all offerings`
- Set the `offering_id` variable
- Send the request to see the complete nested requirement structure

### Example 4: Find Courses with Specific Prerequisites

**Request**: `Offerings > Search by requirements (custom)`
- Set `requires_subject` to a subject code (e.g., `DMA01`)
- Optionally add `scope` filter (e.g., `ALL`)

### Example 5: Filter by Credit Range

**Request**: `Subjects > Filter by credits (range)`
- Set `credits__gte=10` and `credits__lte=15`
- Returns subjects between 10 and 15 credits

## Query Parameter Patterns

The API supports several filtering patterns:

### Exact Match
```
?field=value
?type=EXAM
?is_active=true
```

### Contains (case-insensitive)
```
?field__icontains=value
?code__icontains=DMA
```

### Greater Than / Less Than
```
?field__gte=value
?field__lte=value
?credits__gte=10
?credits__lte=15
```

### Full-Text Search
```
?search=query
?search=CALCULO
```

### Multiple Filters
Combine multiple filters with `&`:
```
?type=EXAM&is_active=true&term=2025S1
```

## Response Format

All list endpoints return paginated responses:

```json
{
    "count": 100,
    "next": "http://localhost:8000/api/subjects/?page=2",
    "previous": null,
    "results": [
        // Array of objects
    ]
}
```

Detail endpoints return a single object:

```json
{
    "id": "uuid-here",
    "field1": "value1",
    // More fields
}
```

## Tips

1. **Use Environment**: Create a Postman environment for different setups (local, staging, production)
2. **Save Responses**: Use Postman's "Save Response" feature to keep example responses
3. **Tests**: Add Postman tests to automatically extract IDs from responses and set variables
4. **Documentation**: Generate API documentation directly from this collection in Postman

## Troubleshooting

### 404 Not Found
- Make sure the Django server is running
- Check that migrations are applied: `python manage.py migrate`
- Verify the base_url variable is correct

### Empty Results
- Make sure you've loaded data with the `load_bedelia` command
- Check that the database isn't empty: `python manage.py shell -c "from api.models import Subject; print(Subject.objects.count())"`

### Invalid UUID
- UUIDs must be in the correct format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- Copy IDs directly from API responses
- Make sure you're using the correct variable for each resource type

## Support

For issues or questions:
1. Check the Django server logs for errors
2. Verify data was loaded correctly
3. Test endpoints in the Django browsable API: `http://localhost:8000/api/`

