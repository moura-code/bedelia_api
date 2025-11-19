<!-- a1603dfc-d5d0-4cbe-84d2-97eb6746b7de 4ec09865-cc59-47d3-bb2d-756857938af2 -->
# Separate Previas and Posprevias Models

## Current Problem

The current architecture uses a single `RequisitoNodo` model for both previas (prerequisites) and posprevias (dependents). The posprevias validation logic creates extra nodes when trying to add relationships, causing inconsistencies.

## Proposed Architecture

### Current Models (Single Structure)

```
RequisitoNodo (tree structure for both previas and posprevias)
├── RequisitoItem (leaf items)
```

### New Models (Separate Structures)

```
PreviaNodo (tree structure for prerequisites only)
├── PreviaItem (leaf items for prerequisites)

PospreviaNodo (tree structure for dependents only)
├── PosPreviaItem (leaf items for dependents)
```

## Implementation Steps

### 1. Create New Models

Create new models in `api/models.py`:

- `PreviaNodo`: Clone of RequisitoNodo but specifically for previas
- `PreviaItem`: Clone of RequisitoItem but for previas
- `PospreviaNodo`: New model for posprevias tree structure
- `PosPreviaItem`: New model for posprevias items

Key differences:

- `PreviaNodo` will reference the source PlanMateria (the one that HAS prerequisites)
- `PospreviaNodo` will reference the source PlanMateria (the one that IS REQUIRED by others)

### 2. Create Database Migration

Generate migration to:

- Create new tables: `api_previanodo`, `api_previaitem`, `api_posprevianodo`, `api_pospreviaitem`
- Migrate data from `api_requisitonodo` and `api_requisitoitem` to previas tables
- Keep old tables temporarily for safety

### 3. Update Serializers

Update `api/serializers/materias.py`:

- Create `PreviaNodoSerializer` and `PreviaNodoTreeSerializer`
- Create `PospreviaNodoSerializer` and `PospreviaNodoTreeSerializer`
- Keep backward compatibility initially

### 4. Update Views

Update `api/views/materias.py`:

- Modify `PreviasViewSet` to use `PreviaNodo` instead of `RequisitoNodo`
- Modify `PosPreviasViewSet` to use `PospreviaNodo` instead of querying RequisitoNodo

### 5. Update Data Loading Command

Update `api/management/commands/load_bedelia_data.py`:

- Modify `process_previas()` to create `PreviaNodo` and `PreviaItem`
- Modify `process_posprevias()` to create `PospreviaNodo` and `PosPreviaItem` independently
- Remove the validation logic that tries to modify previas tree

### 6. Test Migration

- Export current data
- Run migration
- Verify data integrity
- Test API endpoints

### 7. Remove Old Models (Optional)

Once everything works:

- Deprecate `RequisitoNodo` and `RequisitoItem`
- Create migration to drop old tables

## Benefits

1. **No consistency issues**: Previas and posprevias are completely independent
2. **Clearer data model**: Each model has a single responsibility
3. **Easier maintenance**: Changes to previas don't affect posprevias and vice versa
4. **Better performance**: Separate indexes and queries

## Risks

1. **Data migration complexity**: Need to carefully migrate existing data
2. **API breaking changes**: May need to version the API
3. **Doubled storage**: Trees are stored twice (once as previa, once as posprevia)

## Alternative: Keep Single Model but Fix Logic

If the refactoring is too complex, we could:

- Keep current models
- Fix the posprevias validation to NOT modify the previas tree
- Build posprevias relationships separately in memory or a different table

## Recommendation

I recommend proceeding with the separate models approach as it's cleaner architecturally and prevents future consistency issues.