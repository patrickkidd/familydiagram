# Backend Endpoint for AI Auto-Arrange

This document describes the backend API endpoint needed for the LLM-based auto-arrange feature.

## Endpoint

**POST** `/copilot/auto-arrange`

## Authentication

Uses the same vedana signature authentication as other endpoints.

## Request Format

**Content-Type:** `application/json`

```json
{
  "session": "user_session_token",
  "system_prompt": "You are an expert at arranging family diagrams...",
  "people": [
    {
      "id": "person_123",
      "x": 100.5,
      "y": 200.3,
      "width": 80.0,
      "height": 80.0,
      "name": "John Doe",
      "gender": "male",
      "selected": true,
      "is_married_to": "person_456",
      "children_ids": ["person_789"],
      "parent_ids": []
    },
    {
      "id": "person_456",
      "x": 180.5,
      "y": 200.3,
      "width": 80.0,
      "height": 80.0,
      "name": "Jane Doe",
      "gender": "female",
      "selected": true,
      "is_married_to": "person_123",
      "children_ids": ["person_789"],
      "parent_ids": []
    },
    {
      "id": "person_789",
      "x": 140.5,
      "y": 320.3,
      "width": 80.0,
      "height": 80.0,
      "name": "Child Doe",
      "gender": "person",
      "selected": true,
      "is_married_to": null,
      "children_ids": [],
      "parent_ids": ["person_123", "person_456"]
    }
  ]
}
```

**Note:** The `x` and `y` coordinates represent the **CENTER** of each person's bounding rectangle.

## Person Object Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the person |
| `x` | float | X coordinate of CENTER of person's rectangle |
| `y` | float | Y coordinate of CENTER of person's rectangle |
| `width` | float | Bounding rectangle width |
| `height` | float | Bounding rectangle height |
| `name` | string | Person's display name |
| `gender` | string | One of: "male", "female", "person" |
| `selected` | boolean | **True if should be rearranged, False if fixed** |
| `is_married_to` | string\|null | ID of spouse if married |
| `children_ids` | array[string] | IDs of this person's children |
| `parent_ids` | array[string] | IDs of this person's parents |

## Expected Response

**Content-Type:** `application/json`

```json
{
  "person_123": {"x": 110.5, "y": 190.0},
  "person_456": {"x": 210.5, "y": 190.0},
  "person_789": {"x": 160.5, "y": 340.0}
}
```

**Response Schema:**
- Simple dictionary mapping person IDs (strings) to position objects
- Each position is an object with `x` and `y` float coordinates
- **Only include selected people** (where `selected: true`)
- Unselected people should NOT be in the response

## Implementation Notes

### Backend Implementation (btcopilot)

The backend should:

1. **Extract the request data**
   - Parse JSON request
   - Extract `system_prompt` and `people` array

2. **Call LLM** (Claude, GPT, etc.)
   - Use `system_prompt` as the system message
   - Send the `people` array as the user message
   - Request JSON response mode (structured output)
   - Optional: Set temperature to ~0.7 for variety, or use seed for determinism

3. **Parse LLM response**
   - Extract the `positions` object from LLM JSON response
   - Validate that only selected people are included
   - Ensure all coordinates are valid floats

4. **Return response**
   - Return JSON with `positions` object

### Example Implementation (Python/Flask)

```python
@app.route('/copilot/auto-arrange', methods=['POST'])
def auto_arrange():
    data = request.json
    system_prompt = data['system_prompt']
    people = data['people']

    # Call your LLM service
    llm_response = llm_client.chat.completions.create(
        model="claude-3-5-sonnet-20241022",  # or gpt-4, etc.
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps({"people": people})}
        ],
        response_format={"type": "json_object"},  # For structured output
        temperature=0.7  # For variety between requests
    )

    # Parse LLM response (should be a dict mapping person_id -> {x, y})
    positions = json.loads(llm_response.choices[0].message.content)

    return jsonify(positions)
```

## System Prompt Strategy

The system prompt (included in the request) instructs the LLM to:

1. **Only move selected people** - Never change unselected positions
2. **Respect family relationships**:
   - Keep married couples horizontally adjacent
   - Position children below parents
   - Maintain generational hierarchy
3. **Use proper spacing** based on person dimensions
4. **Minimize line crossings** for clarity
5. **Create balanced, symmetric layouts**

## Testing

Test cases should include:

1. Simple married couple
2. Family with parents and children
3. Multi-generational family
4. Mixed selected/unselected people (ensure unselected don't move)
5. Complex families with multiple marriages
6. Siblings from same parents

## Error Handling

The endpoint should return appropriate HTTP status codes:

- **200**: Success
- **400**: Invalid request format
- **401**: Authentication failed
- **500**: LLM service error

Error response format:
```json
{
  "error": "Description of what went wrong"
}
```
