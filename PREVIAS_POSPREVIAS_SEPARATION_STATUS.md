# Previas/Posprevias Model Separation - Implementation Status

## ✅ COMPLETED TASKS

### 1. New Models Created
- **PreviaNodo**: Separate model for prerequisites tree structure
- **PreviaItem**: Items for prerequisites  
- **PospreviaNodo**: Separate model for dependents tree structure  
- **PosPreviaItem**: Items for dependents

**Location:** `bedelia/api/models.py` (lines 308-606)
**Tables Created:**
- `previas_nodos`
- `previas_items`
- `posprevias_nodos`
- `posprevias_items`

### 2. Database Migration
- **Migration File:** `api/migrations/0003_add_separate_previas_posprevias_models.py`
- **Status:** ✅ Applied successfully
- **Database:** PostgreSQL

### 3. Data Migration
- **Source:** RequisitoNodo → PreviaNodo
- **Records Migrated:**
  - 23,451 PreviaNodos
  - 56,483 PreviaItems
- **Duration:** 32.25 seconds
- **Verification:** ✅ Passed (checked materia 1944 structure)

### 4. Serializers Created
- **PreviaItemSerializer**: Serializer for previa items
- **PreviaNodoSerializer**: Basic serializer for previa nodes
- **PreviaNodoTreeSerializer**: Recursive tree serializer
**Location:** `bedelia/api/serializers/materias.py` (lines 283-380)
- **Status:** ✅ No linter errors

## 🔄 NEXT STEPS (NOT YET IMPLEMENTED)

### 5. Update Views
**File:** `bedelia/api/views/materias.py`

#### Change Required in PreviasViewSet (line ~475):
```python
# OLD:
serializer_class = RequisitoNodoTreeSerializer
# ... filter logic uses RequisitoNodo

# NEW:
serializer_class = PreviaNodoTreeSerializer  
# ... filter logic uses PreviaNodo
```

**Specific Changes:**
1. Update import: Add `PreviaNodo, PreviaItem, PreviaNodoTreeSerializer`
2. Change `serializer_class` to use `PreviaNodoTreeSerializer`
3. Update queryset filters to use `PreviaNodo` instead of `RequisitoNodo`
4. Update `extract_requirements()` method if it exists

### 6. Update Data Loading Command  
**File:** `bedelia/api/management/commands/load_bedelia_data.py`

**Changes Required:**
1. Import new models: `PreviaNodo, PreviaItem`
2. Update `process_previas()` method (around line ~900):
   - Change from `RequisitoNodo.objects.create()` to `PreviaNodo.objects.create()`
   - Change from `RequisitoItem.objects.create()` to `PreviaItem.objects.create()`
3. **REMOVE** posprevias validation logic that modifies previas tree (lines ~1341-1521)
4. Update posprevias processing to create `PospreviaNodo` independently

### 7. Test Migration
**Test Cases:**
1. Test API endpoint: `GET /api/previas/?plan_id=3ed3612f-b5af-4563-a202-9dd103224e2f&materia_code=1944&unidad_tipo=CURSO`
2. Verify structure matches original (2 children: NOT node + credits LEAF)
3. Test other materias and plans
4. Performance test with complex prerequisite trees

### 8. (Optional) Remove Old Models
Once everything is verified working:
1. Mark `RequisitoNodo` and `RequisitoItem` as deprecated
2. Create migration to drop old tables:
   - `requisitos_nodos`
   - `requisitos_items`
3. Update any remaining references in admin.py or other files

## 📊 Current State

### Database Tables
- ✅ `previas_nodos` - 23,451 records
- ✅ `previas_items` - 56,483 records  
- ⚠️  `requisitos_nodos` - 23,451 records (old, can be deleted later)
- ⚠️  `requisitos_items` - 56,483 records (old, can be deleted later)
- 🔲 `posprevias_nodos` - 0 records (needs population)
- 🔲 `posprevias_items` - 0 records (needs population)

### API Endpoints
- ⚠️  `/api/previas/` - Still using old RequisitoNodo model
- ⚠️  `/api/posprevias/` - Still using old RequisitoNodo model

## 🎯 Benefits of Separation

1. **No Consistency Issues**: Previas and posprevias are completely independent
2. **Clearer Data Model**: Each model has single responsibility
3. **Easier Maintenance**: Changes to previas don't affect posprevias
4. **Better Performance**: Separate indexes and optimized queries
5. **Prevents Bugs**: No more accidental modifications to previa trees from posprevia validation

## ⚠️ Important Notes

- Old `RequisitoNodo` data is still in database (safe to keep for now)
- Views still use old models - API will work but won't benefit from separation yet
- Once views are updated, the API will be fully migrated to new architecture
- Postman collection may need updates after view changes

## 📝 Rollback Plan

If needed, can rollback by:
1. Update views back to use `RequisitoNodo`
2. Drop new tables: `previas_nodos`, `previas_items`, `posprevias_nodos`, `posprevias_items`
3. Revert migration: `python manage.py migrate api 0002`

All original data remains intact in `requisitos_nodos` and `requisitos_items` tables.

