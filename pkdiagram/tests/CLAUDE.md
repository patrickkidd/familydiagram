# tests/CLAUDE.md

familydiagram CI test suite. Current TODO is in `doc/TESTS_TODO.md`

## Test Style Guidelines

### Declarative vs Imperative Style in Data Migration tests

Data migration tests in tests/test_compat.py should use **declarative expected
values** rather than imperative assertions whenever possible.

**❌ Bad (Imperative)**:
```python
def test_something():
    data = {...}
    compat.update_data(data)

    # Don't do this - imperative assertions
    assert len(data["people"]) == 3
    inferred = [p for p in data["people"] if p.get("_isInferred")]
    assert len(inferred) == 2
    assert inferred[0]["size"] == 2
```

**✅ Good (Declarative)**:
```python
def test_something():
    data = {...}

    expected = {
        "people": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "gender": "male", "size": 2},
            {"id": 3, "gender": "female", "size": 2},
        ],
        "marriages": [...],
        ...
    }

    compat.update_data(data)
    assert data == expected
```

**Why?**
- Declarative tests are easier to read and understand
- They show the complete expected state, not just fragments
- Failures show full diffs of what's different
- They serve as better documentation of expected behavior

**When to use imperative assertions**:
- For tests that need to verify dynamic behavior or state changes
- For integration tests where the exact output varies
- When the expected state is too large or complex to write out completely

