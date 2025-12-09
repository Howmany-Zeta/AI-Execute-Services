# Test Execution Instructions for Multi-Tenancy Sections 1 & 2

## Tests Created

The following test files have been created for sections 1 and 2:

1. **`test/infrastructure/graph_storage/test_tenant.py`**
   - Tests for `TenantContext` dataclass
   - Tests for `TenantIsolationMode` enum
   - Tests for `validate_tenant_id()` function
   - Tests for `normalize_tenant_id()` function
   - Tests for `InvalidTenantIdError` exception
   - Tests for `CrossTenantRelationError` exception

2. **`test/domain/knowledge_graph/models/test_entity_tenant.py`**
   - Tests for Entity `tenant_id` field
   - Tests for tenant_id validation on Entity
   - Tests for Entity serialization with tenant_id

3. **`test/domain/knowledge_graph/models/test_relation_tenant.py`**
   - Tests for Relation `tenant_id` field
   - Tests for tenant_id validation on Relation
   - Tests for Relation tenant consistency validation
   - Tests for cross-tenant relation prevention

## Running Tests

### Run All Tenant Tests

```bash
poetry run pytest test/infrastructure/graph_storage/test_tenant.py \
                 test/domain/knowledge_graph/models/test_entity_tenant.py \
                 test/domain/knowledge_graph/models/test_relation_tenant.py \
                 -v
```

### Run Specific Test File

```bash
# Tenant infrastructure tests
poetry run pytest test/infrastructure/graph_storage/test_tenant.py -v

# Entity tenant tests
poetry run pytest test/domain/knowledge_graph/models/test_entity_tenant.py -v

# Relation tenant tests
poetry run pytest test/domain/knowledge_graph/models/test_relation_tenant.py -v
```

### Run Specific Test Class

```bash
# Test TenantContext
poetry run pytest test/infrastructure/graph_storage/test_tenant.py::TestTenantContext -v

# Test Entity tenant_id
poetry run pytest test/domain/knowledge_graph/models/test_entity_tenant.py::TestEntityTenantId -v

# Test Relation tenant consistency
poetry run pytest test/domain/knowledge_graph/models/test_relation_tenant.py::TestRelationTenantConsistency -v
```

### Run with Coverage

```bash
poetry run pytest test/infrastructure/graph_storage/test_tenant.py \
                 test/domain/knowledge_graph/models/test_entity_tenant.py \
                 test/domain/knowledge_graph/models/test_relation_tenant.py \
                 --cov=aiecs.infrastructure.graph_storage.tenant \
                 --cov=aiecs.domain.knowledge_graph.models.entity \
                 --cov=aiecs.domain.knowledge_graph.models.relation \
                 --cov-report=term-missing \
                 -v
```

## Expected Test Results

All tests should pass. The test suite covers:

- ✅ Tenant ID validation (valid and invalid formats)
- ✅ TenantContext creation and validation
- ✅ TenantIsolationMode enum values
- ✅ Entity tenant_id field (with and without tenant_id)
- ✅ Relation tenant_id field (with and without tenant_id)
- ✅ Cross-tenant relation prevention
- ✅ Serialization with tenant_id
- ✅ Exception handling

## Quick Verification

To quickly verify the implementation works:

```bash
poetry run python << 'EOF'
from aiecs.infrastructure.graph_storage.tenant import TenantContext, validate_tenant_id
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

# Test TenantContext
ctx = TenantContext(tenant_id="test-tenant")
print(f"✓ TenantContext: {ctx}")

# Test Entity with tenant_id
entity = Entity(id="e1", entity_type="Person", tenant_id="test-tenant")
print(f"✓ Entity tenant_id: {entity.tenant_id}")

# Test Relation with tenant_id
relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2", tenant_id="test-tenant")
print(f"✓ Relation tenant_id: {relation.tenant_id}")

# Test validation
try:
    validate_tenant_id("invalid@id")
except Exception as e:
    print(f"✓ Validation error caught: {type(e).__name__}")

print("\n✓ All basic functionality verified!")
EOF
```
