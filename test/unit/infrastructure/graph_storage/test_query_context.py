"""
Unit Tests for QueryContext

Tests for QueryContext class including variable binding, error accumulation,
and lifecycle management.

Run with: python -m pytest test_query_context.py -v
"""

import pytest
from aiecs.application.knowledge_graph.reasoning.logic_parser.query_context import (
    QueryContext,
    VariableRedefinitionError,
    UndefinedVariableError
)


# Mock schema for testing
class MockSchema:
    """Mock schema manager for testing"""
    def __init__(self):
        self.entity_types = {"Person", "Paper"}


# Mock error for testing
class MockError:
    """Mock error for testing"""
    def __init__(self, message: str):
        self.message = message


def test_create_query_context():
    """Test creating a QueryContext"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    assert context.schema == schema
    assert context.variables == {}
    assert context.query_steps == []
    assert context.errors == []


def test_bind_variable():
    """Test binding a variable"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    context.bind_variable("person_id", "123")
    assert context.variables["person_id"] == "123"
    assert context.has_variable("person_id") == True


def test_bind_variable_redefinition_error():
    """Test that redefining a variable raises an error"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    context.bind_variable("person_id", "123")
    
    with pytest.raises(VariableRedefinitionError) as exc_info:
        context.bind_variable("person_id", "456")
    assert "person_id" in str(exc_info.value)
    assert "already defined" in str(exc_info.value)


def test_resolve_variable():
    """Test resolving a variable"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    context.bind_variable("person_id", "123")
    value = context.resolve_variable("person_id")
    assert value == "123"


def test_resolve_undefined_variable_error():
    """Test that resolving undefined variable raises an error"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    with pytest.raises(UndefinedVariableError) as exc_info:
        context.resolve_variable("unknown")
    assert "unknown" in str(exc_info.value)
    assert "not defined" in str(exc_info.value)


def test_has_variable():
    """Test checking if variable exists"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    assert context.has_variable("person_id") == False
    
    context.bind_variable("person_id", "123")
    assert context.has_variable("person_id") == True
    assert context.has_variable("unknown") == False


def test_add_error():
    """Test adding errors"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    error1 = MockError("Error 1")
    error2 = MockError("Error 2")
    
    context.add_error(error1)
    assert len(context.errors) == 1
    assert context.has_errors() == True
    
    context.add_error(error2)
    assert len(context.errors) == 2


def test_has_errors():
    """Test checking if errors exist"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    assert context.has_errors() == False
    
    context.add_error(MockError("Error"))
    assert context.has_errors() == True


def test_clear():
    """Test clearing context state"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    # Add some state
    context.bind_variable("person_id", "123")
    context.add_error(MockError("Error"))
    context.query_steps.append("step1")
    
    assert len(context.variables) == 1
    assert len(context.errors) == 1
    assert len(context.query_steps) == 1
    
    # Clear
    context.clear()
    
    assert len(context.variables) == 0
    assert len(context.errors) == 0
    assert len(context.query_steps) == 0
    assert context.has_errors() == False


def test_multiple_variables():
    """Test binding and resolving multiple variables"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    context.bind_variable("person_id", "123")
    context.bind_variable("paper_id", "456")
    context.bind_variable("company_id", "789")
    
    assert context.resolve_variable("person_id") == "123"
    assert context.resolve_variable("paper_id") == "456"
    assert context.resolve_variable("company_id") == "789"
    
    assert len(context.variables) == 3


def test_context_repr():
    """Test string representation"""
    schema = MockSchema()
    context = QueryContext(schema)
    
    context.bind_variable("person_id", "123")
    context.add_error(MockError("Error"))
    
    repr_str = repr(context)
    assert "QueryContext" in repr_str
    assert "variables=1" in repr_str
    assert "errors=1" in repr_str


def test_context_isolation():
    """Test that contexts are isolated from each other"""
    schema = MockSchema()
    
    context1 = QueryContext(schema)
    context2 = QueryContext(schema)
    
    context1.bind_variable("person_id", "123")
    
    # context2 should not have the variable
    assert context1.has_variable("person_id") == True
    assert context2.has_variable("person_id") == False

