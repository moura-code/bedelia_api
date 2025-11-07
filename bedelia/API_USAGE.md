# Bedelia API Usage Guide

## 🎯 New Custom Endpoints

### 1. Check Available Courses

**Endpoint**: `POST /api/subjects/available_courses/`

Get all courses you can take based on completed courses.

**Request Body:**
```json
{
  "completed_codes": ["1020", "1061", "1911", "1443"],
  "program_id": "uuid-of-program",  // Optional
  "only_active": true,               // Optional, default: false
  "offering_type": "COURSE"          // Optional, default: COURSE
}
```

**Response:**
```json
{
  "available_offerings": [
    {
      "id": "uuid",
      "subject": {
        "code": "1321",
        "name": "PROGRAMACION 2",
        "credits": "12.00"
      },
      "type": "COURSE",
      "term": "2025S1",
      "is_active": true
    }
  ],
  "completed_count": 4,
  "available_count": 15
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/subjects/available_courses/ \
  -H "Content-Type: application/json" \
  -d '{
    "completed_codes": ["1020", "1061", "1411"],
    "only_active": true
  }'
```

---

### 2. Check What Courses Unlock (PosPrevias)

**Endpoint**: `POST /api/subjects/unlocked_by/`

Find all courses that would be unlocked by completing specific courses.

**Request Body:**
```json
{
  "course_codes": ["1020", "1061"],
  "program_id": "uuid-of-program",  // Optional
  "only_active": true                // Optional, default: false
}
```

**Response:**
```json
{
  "input_courses": ["1020", "1061"],
  "unlocked_offerings": [
    {
      "id": "uuid",
      "subject": {
        "code": "1022",
        "name": "CALCULO 2",
        "credits": "16.00"
      },
      "type": "COURSE",
      "is_active": true
    }
  ],
  "unlocked_count": 8
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/subjects/unlocked_by/ \
  -H "Content-Type: application/json" \
  -d '{
    "course_codes": ["1020", "GAL1"],
    "only_active": true
  }'
```

---

### 3. Course Recommendations (Smart)

**Endpoint**: `POST /api/course-recommendations/`

Get intelligent recommendations for which courses to take next.

**Request Body:**
```json
{
  "completed_codes": ["1020", "1061", "1911", "1443"],
  "program_id": "uuid",  // Optional
  "max_results": 10,     // Optional, default: 10
  "only_active": true,   // Optional, default: true
  "semester": 1          // Optional: 1 or 2
}
```

**Response:**
```json
{
  "completed_count": 4,
  "total_available": 12,
  "recommendations": [
    {
      "offering": {
        "id": "uuid",
        "subject": {
          "code": "1443",
          "name": "ARQUITECTURA DE COMPUTADORAS",
          "credits": "10.00"
        }
      },
      "priority": "high",
      "missing_requirements": 0,
      "unlocks_count": 8,
      "reason": "Available now - unlocks 8 other course(s)"
    },
    {
      "offering": {...},
      "priority": "medium",
      "missing_requirements": 0,
      "unlocks_count": 3,
      "reason": "Available now - unlocks 3 other course(s)"
    }
  ]
}
```

**Priority Levels:**
- `high`: Unlocks 5+ courses
- `medium`: Unlocks 2-4 courses
- `low`: Unlocks 0-1 courses
- `future`: Missing 1 requirement (almost ready)

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/course-recommendations/ \
  -H "Content-Type: application/json" \
  -d '{
    "completed_codes": ["1020", "GAL1", "1411"],
    "only_active": true,
    "max_results": 5
  }'
```

---

### 4. Course Pathway Planner

**Endpoint**: `POST /api/course-pathway/`

Find what courses you need to complete to reach a target course.

**Request Body:**
```json
{
  "target_code": "1911",  // Course you want to take
  "completed_codes": ["1020", "1061"],
  "program_id": "uuid"    // Optional
}
```

**Response:**
```json
{
  "target_course": {
    "code": "1911",
    "name": "FUNDAMENTOS DE BASES DE DATOS",
    "credits": "10.00"
  },
  "completed_courses": ["1020", "1061"],
  "pathway": [
    {
      "code": "1321",
      "name": "PROGRAMACION 2",
      "credits": 12.0
    },
    {
      "code": "1443",
      "name": "ARQUITECTURA DE COMPUTADORAS",
      "credits": 10.0
    }
  ],
  "total_missing": 2,
  "can_take_now": false
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:8000/api/course-pathway/ \
  -H "Content-Type: application/json" \
  -d '{
    "target_code": "1911",
    "completed_codes": ["1020", "GAL1", "1411", "1321"]
  }'
```

---

## 📋 Standard CRUD Endpoints

### Programs
- `GET /api/programs/` - List all programs
- `GET /api/programs/{id}/` - Get program details
- **Filters**: `?plan_year=1997`
- **Search**: `?search=COMPUTACIÓN`

### Subjects
- `GET /api/subjects/` - List all subjects
- `GET /api/subjects/{id}/` - Get subject with offerings and aliases
- **Filters**: 
  - `?programs={uuid}` - Filter by program
  - `?code=1020` - Exact code match
  - `?code__icontains=GAL` - Partial code match
  - `?credits__gte=10` - Minimum credits
  - `?semester=1` - Semester 1 or 2
- **Search**: `?search=CALCULO`

### Offerings
- `GET /api/offerings/` - List all offerings
- `GET /api/offerings/{id}/` - Get offering with full requirements
- `GET /api/offerings/{id}/requirement_tree/` - Get recursive requirement tree
- **Filters**:
  - `?subject={uuid}` - Filter by subject
  - `?type=COURSE` or `?type=EXAM`
  - `?is_active=true` - Only active offerings
  - `?term=2025S1`
  - `?semester=1`

### Requirement Groups
- `GET /api/requirement-groups/` - List all requirement groups
- `GET /api/requirement-groups/{id}/` - Get group with items and children

### Requirement Items
- `GET /api/requirement-items/` - List all requirement items
- `GET /api/requirement-items/{id}/` - Get specific item

---

## 🚀 Usage Examples

### Example 1: What can I take this semester?

```bash
curl -X POST http://localhost:8000/api/course-recommendations/ \
  -H "Content-Type: application/json" \
  -d '{
    "completed_codes": ["1020", "GAL1", "1411", "1061", "PROG1"],
    "only_active": true,
    "semester": 1,
    "max_results": 5
  }'
```

### Example 2: What does completing CDIV unlock?

```bash
curl -X POST http://localhost:8000/api/subjects/unlocked_by/ \
  -H "Content-Type: application/json" \
  -d '{
    "course_codes": ["CDIV"],
    "only_active": true
  }'
```

### Example 3: Path to graduate (target: Proyecto de Grado)

```bash
curl -X POST http://localhost:8000/api/course-pathway/ \
  -H "Content-Type: application/json" \
  -d '{
    "target_code": "1730",
    "completed_codes": ["1020", "GAL1", "CDIV", "1411", "1321", "1443", "1911"]
  }'
```

### Example 4: All active courses in a program

```bash
# First get the program ID
curl http://localhost:8000/api/programs/?search=COMPUTACIÓN

# Then filter offerings
curl "http://localhost:8000/api/offerings/?subject__programs={program_id}&is_active=true"
```

---

## 🔧 Running the Server

```bash
cd bedelia
python3 manage.py runserver
```

Then access:
- API Root: http://localhost:8000/api/
- Django Admin: http://localhost:8000/admin/
- Browsable API: All endpoints support web browsing

---

## 📊 Loading Data

```bash
cd bedelia

# Load all data (using defaults)
python3 manage.py load_bedelia

# Load with specific files
python3 manage.py load_bedelia \
  --credits ../data/credits_data_backup.json \
  --requirements ../data/previas_data_backup.json \
  --posprevias ../data/posprevias_data_backup.json \
  --vigentes ../data/vigentes_data_backup.json

# Dry run (test without saving)
python3 manage.py load_bedelia --dry-run --verbose
```

---

## 💡 Tips

1. **Program IDs**: Use `GET /api/programs/` to find program UUIDs
2. **Subject Codes**: Subject codes like "1020", "GAL1", "CDIV" are unique across all programs
3. **Active vs All**: Use `only_active=true` to see only currently offered courses
4. **Priorities**: "high" priority courses unlock the most other courses
5. **Pathways**: Shows the minimum courses needed to reach your target

---

## 🏗️ Data Model

```
Program (1997 - INGENIERÍA EN COMPUTACIÓN)
  ↓ ManyToMany
Subject (CDIV - CÁLCULO DIFERENCIAL)
  ↓ OneToMany
Offering (CDIV - COURSE - 2025S1)
  ↓ OneToMany
RequirementGroup (ALL/ANY/NONE)
  ↓ OneToMany
RequirementItem → Target Subject/Offering
```

Each subject can belong to multiple programs, allowing shared courses like CDIV, GAL, FÍSICA to exist once but serve multiple engineering programs.

