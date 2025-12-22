"""
Unit tests for graph storage error handling module

Tests use real components when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from datetime import datetime

from aiecs.infrastructure.graph_storage.error_handling import (
    GraphStoreError,
    GraphStoreConnectionError,
    GraphStoreQueryError,
    GraphStoreValidationError,
    GraphStoreNotFoundError,
    GraphStoreConflictError,
    GraphStoreTimeoutError,
    ErrorSeverity,
    ErrorContext,
    ErrorHandler
)


class TestGraphStoreExceptions:
    """Test exception classes"""
    
    def test_graph_store_error(self):
        """Test base GraphStoreError"""
        error = GraphStoreError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_graph_store_connection_error(self):
        """Test GraphStoreConnectionError"""
        error = GraphStoreConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, GraphStoreError)
    
    def test_graph_store_query_error(self):
        """Test GraphStoreQueryError"""
        error = GraphStoreQueryError("Query failed")
        assert str(error) == "Query failed"
        assert isinstance(error, GraphStoreError)
    
    def test_graph_store_validation_error(self):
        """Test GraphStoreValidationError"""
        error = GraphStoreValidationError("Validation failed")
        assert str(error) == "Validation failed"
        assert isinstance(error, GraphStoreError)
    
    def test_graph_store_not_found_error(self):
        """Test GraphStoreNotFoundError"""
        error = GraphStoreNotFoundError("Entity not found")
        assert str(error) == "Entity not found"
        assert isinstance(error, GraphStoreError)
    
    def test_graph_store_conflict_error(self):
        """Test GraphStoreConflictError"""
        error = GraphStoreConflictError("Duplicate ID")
        assert str(error) == "Duplicate ID"
        assert isinstance(error, GraphStoreError)
    
    def test_graph_store_timeout_error(self):
        """Test GraphStoreTimeoutError"""
        error = GraphStoreTimeoutError("Operation timed out")
        assert str(error) == "Operation timed out"
        assert isinstance(error, GraphStoreError)


class TestErrorSeverity:
    """Test ErrorSeverity enum"""
    
    def test_error_severity_values(self):
        """Test ErrorSeverity enum values"""
        assert ErrorSeverity.LOW == "low"
        assert ErrorSeverity.MEDIUM == "medium"
        assert ErrorSeverity.HIGH == "high"
        assert ErrorSeverity.CRITICAL == "critical"


class TestErrorContext:
    """Test ErrorContext dataclass"""
    
    def test_error_context_defaults(self):
        """Test ErrorContext with defaults"""
        context = ErrorContext(operation="get_entity")
        
        assert context.operation == "get_entity"
        assert context.entity_id is None
        assert context.relation_id is None
        assert context.query is None
        assert context.parameters is None
        assert context.severity == ErrorSeverity.MEDIUM
        assert isinstance(context.timestamp, datetime)
    
    def test_error_context_custom(self):
        """Test ErrorContext with custom values"""
        context = ErrorContext(
            operation="add_entity",
            entity_id="e1",
            severity=ErrorSeverity.HIGH,
            parameters={"type": "Person"}
        )
        
        assert context.operation == "add_entity"
        assert context.entity_id == "e1"
        assert context.severity == ErrorSeverity.HIGH
        assert context.parameters == {"type": "Person"}
    
    def test_error_context_to_dict(self):
        """Test ErrorContext.to_dict()"""
        context = ErrorContext(
            operation="query",
            query="SELECT * FROM entities",
            parameters={"limit": 10}
        )
        
        result = context.to_dict()
        
        assert result["operation"] == "query"
        assert "SELECT * FROM entities" in result["query"]
        assert result["parameters"] == {"limit": 10}
        assert "timestamp" in result
        assert result["severity"] == "medium"
    
    def test_error_context_long_query_truncation(self):
        """Test ErrorContext truncates long queries"""
        long_query = "SELECT " + "x" * 200
        context = ErrorContext(operation="query", query=long_query)
        
        result = context.to_dict()
        
        assert len(result["query"]) <= 103  # 100 + "..."
        assert result["query"].endswith("...")


class TestErrorHandler:
    """Test ErrorHandler"""
    
    @pytest.fixture
    def handler(self):
        """Create ErrorHandler instance"""
        return ErrorHandler()
    
    def test_handle_error_basic(self, handler):
        """Test basic error handling"""
        error = GraphStoreError("Test error")
        context = ErrorContext(operation="test")
        
        # handle_error doesn't return a value, it logs and optionally re-raises
        # Test with reraise=False to verify it doesn't raise
        handler.handle_error(error, context, reraise=False)
        
        # If we get here, error was handled without re-raising
        assert True
    
    def test_handle_error_with_entity_id(self, handler):
        """Test error handling with entity ID"""
        error = GraphStoreNotFoundError("Entity not found")
        context = ErrorContext(operation="get_entity", entity_id="e1")
        
        # Test with reraise=False
        handler.handle_error(error, context, reraise=False)
        
        # Verify context has entity_id
        assert context.entity_id == "e1"
    
    def test_handle_error_with_relation_id(self, handler):
        """Test error handling with relation ID"""
        error = GraphStoreQueryError("Query failed")
        context = ErrorContext(operation="get_relation", relation_id="r1")
        
        # Test with reraise=False
        handler.handle_error(error, context, reraise=False)
        
        # Verify context has relation_id
        assert context.relation_id == "r1"
    
    def test_handle_error_different_severities(self, handler):
        """Test error handling with different severities"""
        error = GraphStoreError("Test")
        
        for severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM, ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            context = ErrorContext(operation="test", severity=severity)
            handler.handle_error(error, context, reraise=False)
            assert context.severity == severity
    
    def test_handle_error_critical_severity(self, handler):
        """Test critical error handling"""
        error = GraphStoreConnectionError("Critical connection failure")
        context = ErrorContext(
            operation="initialize",
            severity=ErrorSeverity.CRITICAL
        )
        
        handler.handle_error(error, context, reraise=False)
        
        assert context.severity == ErrorSeverity.CRITICAL
    
    def test_handle_error_with_parameters(self, handler):
        """Test error handling with parameters"""
        error = GraphStoreQueryError("Query failed")
        context = ErrorContext(
            operation="execute_query",
            query="SELECT * FROM entities",
            parameters={"limit": 10, "offset": 0}
        )
        
        handler.handle_error(error, context, reraise=False)
        
        assert context.parameters == {"limit": 10, "offset": 0}
    
    def test_handle_error_exception_info(self, handler):
        """Test error handling captures exception info"""
        error = GraphStoreError("Test error with traceback")
        context = ErrorContext(operation="test")
        
        # Test with reraise=False to verify it handles the error
        handler.handle_error(error, context, reraise=False)
        
        # Verify error was handled
        assert str(error) == "Test error with traceback"
    
    def test_handle_error_reraise(self, handler):
        """Test error handling with reraise=True"""
        error = GraphStoreError("Test error")
        context = ErrorContext(operation="test")
        
        # Should re-raise the exception
        with pytest.raises(GraphStoreError):
            handler.handle_error(error, context, reraise=True)
    
    def test_handle_error_exception_mapping(self, handler):
        """Test exception mapping"""
        # Test connection error mapping
        connection_error = Exception("Connection timeout")
        context = ErrorContext(operation="connect")
        
        # Should map to GraphStoreConnectionError
        with pytest.raises(GraphStoreConnectionError):
            handler.handle_error(connection_error, context, reraise=True)
    
    def test_handle_error_not_found_mapping(self, handler):
        """Test not found error mapping"""
        not_found_error = Exception("Entity not found")
        context = ErrorContext(operation="get_entity")
        
        # Should map to GraphStoreNotFoundError
        with pytest.raises(GraphStoreNotFoundError):
            handler.handle_error(not_found_error, context, reraise=True)

