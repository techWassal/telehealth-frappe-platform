# Agent Governance: Frappe Backend Workspace

## Role: Implementation (Backend API)

This workspace implements:
- REST API endpoints
- Business logic (Frappe DocTypes)
- Database schemas
- Webhooks and integrations

## Critical Rules

### Rule 1: NEVER Start Without Contract Reference
Every implementation task MUST include:
```yaml
metadata:
  upstream_contract_id: "bd-contract-XXXXX"
  tdd_file: ".bmad/tdd/bd-impl-XXXXX-tdd.md"
  module: "core|video|ai|integrations"
  api_contract_path: "../telehealth-core-contracts/contracts/..."
```

### Rule 2: Check Contract Status Before Starting
```bash
# Verify contract is closed BEFORE implementing
cd ../telehealth-core-contracts
bd show bd-contract-XXXXX | grep "status"
# Must return: status = "closed"

# If not closed, BLOCK
if [ "$status" != "closed" ]; then
  echo "BLOCKED: Upstream contract not ready"
  exit 1
fi
```

### Rule 3: Read Contract BEFORE Coding
```bash
# Developer agent MUST read contract first
cat ../telehealth-core-contracts/contracts/api-specs/patient-api.yaml

# Then generate modular TDD
bmad agent scrum-master --issue bd-impl-XXXXX \
  --contract ../telehealth-core-contracts/contracts/api-specs/patient-api.yaml

# Then implement
bmad agent developer --issue bd-impl-XXXXX \
  --tdd .bmad/tdd/bd-impl-XXXXX-tdd.md
```

### Rule 4: Validate Against Contract Before Closing
```bash
# Test implementation matches contract
pytest tests/test_contract_compliance.py::test_patient_api

# Only close if tests pass
bd close bd-impl-XXXXX \
  --upstream bd-contract-XXXXX \
  --artifacts "telehealth_platform/core/api/patient.py"
```

## BMAD Integration

### Developer Agent Workflow
```bash
# 1. Acquire ready task
bd ready --type implementation

# 2. Verify upstream contract (in contracts workspace)
cd ../telehealth-core-contracts
status=$(bd show <upstream_id> | grep status)
cd -

# 3. If not closed, exit
[ "$status" = "closed" ] || exit 1

# 4. Read contract
cat <api_contract_path>

# 5. Generate modular TDD
bmad agent scrum-master --issue bd-impl-XXXXX --contract <path>

# 6. Implement
bmad agent developer --issue bd-impl-XXXXX --tdd .bmad/tdd/...

# 7. Test
bmad agent qa --issue bd-impl-XXXXX

# 8. Validate against contract
pytest tests/test_contract_compliance.py

# 9. Close with upstream reference
bd close bd-impl-XXXXX --upstream <contract_id>
```
