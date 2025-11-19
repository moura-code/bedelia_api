<!-- b3c34b48-f9b2-4eb4-bb6a-5875c1c9e2b9 d807dac2-41e5-4d72-adf3-e437ac6cfdc9 -->
# Support Credits in Plan Requirements

## Problem

The previas data now includes a new type of requirement:

- **source**: "PLAN"
- **modality**: "credits_in_plan"
- **credits_required**: number of credits needed
- **plan_year** and **plan_name**: which plan the credits must be from

Example:

```json
{
  "source": "PLAN",
  "modality": "credits_in_plan",
  "credits_required": 140,
  "plan_year": "2021",
  "plan_name": "INGENIERÍA CIVIL",
  "code": "",
  "title": "2021 - INGENIERÍA CIVIL",
  "raw": "140 créditos en el Plan: 2021 - INGENIERÍA CIVIL"
}
```

This needs to be stored in the database as a RequisitoItem.

## Changes Required

### File: `bedelia/api/management/commands/load_bedelia_data.py`

#### Update `_process_requisito_item` method (around lines 1036-1112)

The current implementation only handles items with `source: "UCB"`. We need to add handling for `source: "PLAN"` with `modality: "credits_in_plan"`.

**Current logic flow**:

1. Check if modality matches UCB types (ucb_module, course, exam, course_enrollment)
2. If yes, try to create UNIDAD type RequisitoItem
3. If fails or doesn't match, create TEXTO type RequisitoItem

**New logic needed**:

1. Check if source is "PLAN" and modality is "credits_in_plan"
2. If yes, create TEXTO type RequisitoItem with formatted text
3. Otherwise, proceed with existing UCB logic

#### Specific changes:

**After line 1042** (after extracting modality, code, title, raw), add check for PLAN source:

```python
def _process_requisito_item(self, nodo: RequisitoNodo, item_data: Dict, orden: int):
    """Procesar un item de requisito (LEAF)."""
    # ... existing code to extract fields ...
    
    source = item_data.get('source', 'UCB')
    
    # Handle PLAN-based requirements (credits in plan)
    if source == 'PLAN' and modality_mapped == 'credits_in_plan':
        credits_required = item_data.get('credits_required', 0)
        plan_year = item_data.get('plan_year', '')
        plan_name = item_data.get('plan_name', '')
        
        # Create descriptive text
        if plan_year and plan_name:
            texto = f"{credits_required} créditos en el Plan: {plan_year} - {plan_name}"
        else:
            texto = raw or title or f"{credits_required} créditos requeridos"
        
        try:
            if self.dry_run:
                item = RequisitoItem(
                    nodo=nodo,
                    tipo=RequisitoItem.TipoItem.TEXTO,
                    texto=texto,
                    orden=orden
                )
            else:
                item, created = RequisitoItem.objects.get_or_create(
                    nodo=nodo,
                    tipo=RequisitoItem.TipoItem.TEXTO,
                    texto=texto,
                    defaults={'orden': orden}
                )
                if created:
                    self.stats['requisitos_items_creados'] += 1
            return
        except Exception as e:
            # Log error and continue to fallback
            if self.verbose:
                self.stdout.write(
                    self.style.WARNING(f'       [#]  Error creando item TEXTO para credits_in_plan: {str(e)}')
                )
    
    # Determine tipo de item (existing UCB logic)
    # ... rest of existing code ...
```

**Location**: Insert this new logic right after extracting the source field (around line 1042-1045), before the existing UCB modality checking logic.

The key changes are:

1. Extract `source` from item_data (defaults to 'UCB' for backward compatibility)
2. Check if source is 'PLAN' and modality is 'credits_in_plan'
3. Create a TEXTO type RequisitoItem with formatted requirement text
4. Return early if handled, otherwise fall through to existing UCB logic

## Testing

After implementation:

1. Load previas data with credits_in_plan requirements
2. Verify RequisitoItem objects are created with tipo=TEXTO
3. Verify the texto field contains readable credit requirement information
4. Check that no errors are raised for this new requirement type