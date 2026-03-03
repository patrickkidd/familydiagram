#!/usr/bin/env bash
# sync-board.sh — Sync GitHub project board Status & Owner fields
# from issue milestones and assignees.
#
# Usage: ./scripts/sync-board.sh [--dry-run]

set -euo pipefail

PROJECT_ID="PVT_kwHOABjmWc4BP0PU"
STATUS_FIELD_ID="PVTSSF_lAHOABjmWc4BP0PUzg-HbRs"
OWNER_FIELD_ID="PVTSSF_lAHOABjmWc4BP0PUzg-HbS8"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# --- 1. Ensure Status field has Goal options ---

echo "=== Ensuring Status field has Goal options ==="
FIELD_RESULT=$(gh api graphql -f query='
mutation {
  updateProjectV2Field(input: {
    fieldId: "'"$STATUS_FIELD_ID"'"
    singleSelectOptions: [
      {name: "Todo", color: BLUE, description: ""},
      {name: "In Progress", color: YELLOW, description: ""},
      {name: "Done", color: GREEN, description: ""},
      {name: "Goal 1", color: PURPLE, description: "Single-Prompt Extraction E2E"},
      {name: "Goal 2", color: ORANGE, description: "Human Beta"},
      {name: "Goal 3", color: PINK, description: "Pro App Viewing"},
      {name: "No Milestone", color: GRAY, description: "No milestone assigned"}
    ]
  }) {
    projectV2Field {
      ... on ProjectV2SingleSelectField {
        options { id name }
      }
    }
  }
}')

# Parse option IDs
get_option_id() {
    echo "$FIELD_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
opts = data['data']['updateProjectV2Field']['projectV2Field']['options']
for o in opts:
    if o['name'] == '$1':
        print(o['id'])
        break
"
}

GOAL1_ID=$(get_option_id "Goal 1")
GOAL2_ID=$(get_option_id "Goal 2")
GOAL3_ID=$(get_option_id "Goal 3")
NO_MILESTONE_ID=$(get_option_id "No Milestone")

echo "  Goal 1 option ID: $GOAL1_ID"
echo "  Goal 2 option ID: $GOAL2_ID"
echo "  Goal 3 option ID: $GOAL3_ID"
echo "  No Milestone option ID: $NO_MILESTONE_ID"

# --- 2. Owner option IDs (static) ---
# These map GitHub login -> Owner field option
declare -A OWNER_MAP=(
    ["patrickkidd"]="2120b409"
    ["patrickkidd-hurin"]="4e27439a"
    ["patrickkidd-beren"]="fb745a0e"
    ["patrickkidd-tuor"]="e0b8b5b9"
)

declare -A OWNER_NAMES=(
    ["2120b409"]="Patrick"
    ["4e27439a"]="Hurin"
    ["fb745a0e"]="Beren"
    ["e0b8b5b9"]="Tuor"
)

# --- 3. Milestone -> Status option ID mapping ---
declare -A MILESTONE_STATUS_MAP=(
    ["Goal 1: Single-Prompt Extraction E2E"]="$GOAL1_ID"
    ["Goal 2: Human Beta"]="$GOAL2_ID"
    ["Goal 3: Pro App Viewing"]="$GOAL3_ID"
)

declare -A MILESTONE_LABEL_MAP=(
    ["Goal 1: Single-Prompt Extraction E2E"]="Goal 1"
    ["Goal 2: Human Beta"]="Goal 2"
    ["Goal 3: Pro App Viewing"]="Goal 3"
)

# --- 4. Query all project items ---

echo ""
echo "=== Querying project items ==="
ITEMS_JSON=$(gh api graphql -f query='
{
  node(id: "'"$PROJECT_ID"'") {
    ... on ProjectV2 {
      items(first: 100) {
        nodes {
          id
          fieldValues(first: 20) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                optionId
                field { ... on ProjectV2SingleSelectField { name id } }
              }
            }
          }
          content {
            ... on Issue {
              number
              title
              milestone { title }
              assignees(first: 5) { nodes { login } }
            }
            ... on PullRequest {
              number
              title
            }
          }
        }
      }
    }
  }
}')

# --- 5. Process each item ---

echo ""
echo "=== Processing items ==="

CHANGES=()
ITEM_COUNT=$(echo "$ITEMS_JSON" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['data']['node']['items']['nodes']))")

for i in $(seq 0 $((ITEM_COUNT - 1))); do
    ITEM_DATA=$(echo "$ITEMS_JSON" | python3 -c "
import sys, json
data = json.load(sys.stdin)
item = data['data']['node']['items']['nodes'][$i]
content = item.get('content', {})
number = content.get('number', '')
title = content.get('title', '')
milestone = (content.get('milestone') or {}).get('title', '')
assignees = [a['login'] for a in (content.get('assignees', {}).get('nodes', []))]
assignee = assignees[0] if assignees else ''

# Get current field values
current_status = ''
current_status_id = ''
current_owner = ''
current_owner_id = ''
for fv in item.get('fieldValues', {}).get('nodes', []):
    field = fv.get('field', {})
    if field.get('name') == 'Status':
        current_status = fv.get('name', '')
        current_status_id = fv.get('optionId', '')
    elif field.get('name') == 'Owner':
        current_owner = fv.get('name', '')
        current_owner_id = fv.get('optionId', '')

print(f'{item[\"id\"]}|{number}|{title}|{milestone}|{assignee}|{current_status}|{current_status_id}|{current_owner}|{current_owner_id}')
")

    IFS='|' read -r ITEM_ID ISSUE_NUM ISSUE_TITLE MILESTONE ASSIGNEE CUR_STATUS CUR_STATUS_ID CUR_OWNER CUR_OWNER_ID <<< "$ITEM_DATA"

    # Skip non-issue items (PRs, drafts without milestone info)
    [[ -z "$ISSUE_NUM" ]] && continue

    # Determine desired status
    if [[ -n "$MILESTONE" && -n "${MILESTONE_STATUS_MAP[$MILESTONE]:-}" ]]; then
        DESIRED_STATUS_ID="${MILESTONE_STATUS_MAP[$MILESTONE]}"
        DESIRED_STATUS_LABEL="${MILESTONE_LABEL_MAP[$MILESTONE]}"
    else
        DESIRED_STATUS_ID="$NO_MILESTONE_ID"
        DESIRED_STATUS_LABEL="No Milestone"
    fi

    # Determine desired owner
    DESIRED_OWNER_ID=""
    DESIRED_OWNER_LABEL=""
    if [[ -n "$ASSIGNEE" && -n "${OWNER_MAP[$ASSIGNEE]:-}" ]]; then
        DESIRED_OWNER_ID="${OWNER_MAP[$ASSIGNEE]}"
        DESIRED_OWNER_LABEL="${OWNER_NAMES[$DESIRED_OWNER_ID]}"
    fi

    # Check if status needs updating
    STATUS_CHANGED=false
    if [[ "$DESIRED_STATUS_ID" != "$CUR_STATUS_ID" ]]; then
        STATUS_CHANGED=true
        CHANGE_MSG="#${ISSUE_NUM}: Status '${CUR_STATUS}' -> '${DESIRED_STATUS_LABEL}'"
        echo "  $CHANGE_MSG"
        CHANGES+=("$CHANGE_MSG")

        if [[ "$DRY_RUN" == "false" ]]; then
            gh api graphql -f query='
            mutation {
              updateProjectV2ItemFieldValue(input: {
                projectId: "'"$PROJECT_ID"'"
                itemId: "'"$ITEM_ID"'"
                fieldId: "'"$STATUS_FIELD_ID"'"
                value: { singleSelectOptionId: "'"$DESIRED_STATUS_ID"'" }
              }) {
                projectV2Item { id }
              }
            }' > /dev/null
        fi
    fi

    # Check if owner needs updating
    OWNER_CHANGED=false
    if [[ -n "$DESIRED_OWNER_ID" && "$DESIRED_OWNER_ID" != "$CUR_OWNER_ID" ]]; then
        OWNER_CHANGED=true
        CHANGE_MSG="#${ISSUE_NUM}: Owner '${CUR_OWNER}' -> '${DESIRED_OWNER_LABEL}'"
        echo "  $CHANGE_MSG"
        CHANGES+=("$CHANGE_MSG")

        if [[ "$DRY_RUN" == "false" ]]; then
            gh api graphql -f query='
            mutation {
              updateProjectV2ItemFieldValue(input: {
                projectId: "'"$PROJECT_ID"'"
                itemId: "'"$ITEM_ID"'"
                fieldId: "'"$OWNER_FIELD_ID"'"
                value: { singleSelectOptionId: "'"$DESIRED_OWNER_ID"'" }
              }) {
                projectV2Item { id }
              }
            }' > /dev/null
        fi
    fi

    if [[ "$STATUS_CHANGED" == "false" && "$OWNER_CHANGED" == "false" ]]; then
        echo "  #${ISSUE_NUM}: no changes needed"
    fi
done

# --- 6. Summary ---

echo ""
echo "=== Sync Summary ==="
if [[ ${#CHANGES[@]} -eq 0 ]]; then
    echo "No changes were needed."
else
    echo "${#CHANGES[@]} change(s) made:"
    for c in "${CHANGES[@]}"; do
        echo "  - $c"
    done
fi

if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo "(DRY RUN — no mutations were executed)"
fi
