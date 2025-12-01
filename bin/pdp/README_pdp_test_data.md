# PDP Test Data Scripts

Scripts for generating and loading PDP (Pending Data Pool) test data for manual testing.

## Quick Start

### 1. Reset Diagram with Test Data (Recommended)

```bash
uv run python familydiagram/bin/pdp/reset_pdp_test.py <diagram_id>
```

Clears all discussions and loads comprehensive PDP test data.

### 2. View Available Scenarios

```bash
uv run python familydiagram/bin/pdp/generate_pdp_data.py
```

Shows all available test scenarios with their data.

### 3. Generate JSON for a Scenario

```bash
uv run python familydiagram/bin/pdp/generate_pdp_data.py family --json
```

### 4. Load Scenario into Free Diagram

```bash
uv run python familydiagram/bin/pdp/load_pdp_test_data.py family
```

This loads the scenario into the test user's free diagram. Then start the app:

```bash
uv run familydiagram/main.py
```

## Available Scenarios

- **simple**: Single person with birth event
- **couple**: Married couple with pair bond
- **family**: Parents with 2 children (demonstrates transitive closure)
- **complex**: Multiple families with various relationships
- **cascade**: Designed to test cascade deletion (person with multiple events)

## Testing Workflow

1. Reset a diagram: `uv run python familydiagram/bin/pdp/reset_pdp_test.py 1746`
2. Start the app: `uv run familydiagram/main.py`
3. Open the Personal view
4. Test accept/reject on PDP items
5. Verify:
   - Accept: Items move to main diagram with positive IDs
   - Transitive closure: Accepting child accepts parents + pair_bond
   - Reject: Items removed from PDP
   - Cascade deletion: Rejecting person removes their events
   - Undo/redo works correctly

## Advanced Usage

### Save to File

```bash
uv run python familydiagram/bin/pdp/generate_pdp_data.py complex --json -o test_data.json
```

### Use in Python REPL

```python
from btcopilot.schema import from_dict, DiagramData
import json

with open('test_data.json') as f:
    data = from_dict(DiagramData, json.load(f))

# Now you can inspect or modify data
print(len(data.pdp.people))
```

### Load for Different User

```bash
uv run python familydiagram/bin/pdp/load_pdp_test_data.py family --user other@example.com
```

## Test Scenarios Explained

### Family Scenario (Transitive Closure Test)

When you accept **Frank** (child):
- System automatically accepts **David** (parent)
- System automatically accepts **Emma** (parent)
- System automatically accepts **PairBond(-7)** (parents' relationship)
- All IDs remapped to positive values
- All references updated

### Cascade Scenario (Deletion Test)

When you reject **Mike**:
- System removes **Birth event** (-3)
- System removes **Shift event** (-4)
- System removes **Death event** (-5)
- Nancy and her events remain untouched
