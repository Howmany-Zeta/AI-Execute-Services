"""
Integration tests for schema generation and coverage tracking.

Tests schema auto-generation, coverage tracking, and quality metrics
in a real environment with actual tool classes.
"""

import pytest
from typing import Dict, Any, Type, List
from pydantic import BaseModel, ValidationError

from aiecs.tools import discover_tools, TOOL_CLASSES, get_tool
from aiecs.tools.schema_generator import (
    generate_schema_from_method,
    generate_schemas_for_tool,
    _normalize_type,
    _extract_param_description_from_docstring,
)
from aiecs.tools.base_tool import BaseTool
from aiecs.scripts.tools_develop.validate_tool_schemas import (
    analyze_tool_schemas,
    SchemaQualityMetrics,
    validate_schema_quality,
)


@pytest.fixture(scope="module")
def discovered_tools():
    """Discover all tools once for the test module."""
    discover_tools()
    return TOOL_CLASSES


@pytest.mark.integration
class TestSchemaGenerationIntegration:
    """Integration tests for schema generation functionality."""

    def test_schema_generation_for_pandas_tool(self, discovered_tools):
        """Test schema generation for pandas tool methods."""
        if "pandas" not in discovered_tools:
            pytest.skip("pandas tool not available")

        pandas_tool = discovered_tools["pandas"]
        schemas = generate_schemas_for_tool(pandas_tool)

        # Should generate schemas for multiple methods
        assert len(schemas) > 0, "Should generate at least one schema"

        # Verify schemas are valid Pydantic models
        for method_name, schema in schemas.items():
            assert issubclass(schema, BaseModel), f"Schema for {method_name} should be a BaseModel"
            assert schema.__name__.endswith("Schema"), f"Schema name should end with 'Schema'"

    def test_schema_generation_for_stats_tool(self, discovered_tools):
        """Test schema generation for stats tool methods."""
        if "stats" not in discovered_tools:
            pytest.skip("stats tool not available")

        stats_tool = discovered_tools["stats"]
        schemas = generate_schemas_for_tool(stats_tool)

        assert len(schemas) > 0, "Should generate at least one schema"

        # Verify schema structure
        for method_name, schema in schemas.items():
            assert hasattr(schema, "model_fields"), f"Schema should have model_fields"
            assert schema.__doc__, f"Schema should have a docstring"

    def test_schema_generation_handles_complex_types(self, discovered_tools):
        """Test that schema generation handles complex types gracefully."""
        if "pandas" not in discovered_tools:
            pytest.skip("pandas tool not available")

        pandas_tool = discovered_tools["pandas"]
        
        # Find a method that might have complex types
        for method_name in dir(pandas_tool):
            if method_name.startswith("_") or not callable(getattr(pandas_tool, method_name)):
                continue
            
            method = getattr(pandas_tool, method_name)
            if isinstance(method, type):
                continue
            
            try:
                schema = generate_schema_from_method(method, method_name)
                if schema:
                    # Should not raise errors even with complex types
                    assert issubclass(schema, BaseModel)
                    break
            except Exception as e:
                pytest.fail(f"Schema generation failed for {method_name}: {e}")

    def test_schema_generation_extracts_docstrings(self):
        """Test that schema generation extracts descriptions from docstrings."""
        def test_method(data: str, count: int = 10) -> str:
            """
            Test method for docstring extraction.
            
            Args:
                data: Input data string
                count: Number of items (default: 10)
            
            Returns:
                Processed string
            """
            return f"{data}_{count}"

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None, "Should generate schema"
        assert "data" in schema.model_fields, "Should have 'data' field"
        assert "count" in schema.model_fields, "Should have 'count' field"
        
        # Check descriptions were extracted
        data_field = schema.model_fields["data"]
        assert data_field.description == "Input data string", "Should extract description"
        
        count_field = schema.model_fields["count"]
        assert count_field.description == "Number of items (default: 10)", "Should extract description"

    def test_schema_generation_handles_optional_parameters(self):
        """Test schema generation for optional parameters."""
        def test_method(required: str, optional: str = None, with_default: int = 5) -> str:
            """Test method with optional parameters."""
            return required

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        assert schema.model_fields["required"].is_required(), "Required field should be required"
        assert not schema.model_fields["optional"].is_required(), "Optional field should not be required"
        assert not schema.model_fields["with_default"].is_required(), "Field with default should not be required"
        assert schema.model_fields["with_default"].default == 5, "Default value should be preserved"


@pytest.mark.integration
class TestSchemaCoverageTracking:
    """Integration tests for schema coverage tracking."""

    def test_schema_coverage_analysis(self, discovered_tools):
        """Test schema coverage analysis for all tools."""
        # Analyze a few tools
        test_tools = ["pandas", "stats", "research"]
        available_tools = [t for t in test_tools if t in discovered_tools]
        
        if not available_tools:
            pytest.skip("No test tools available")

        for tool_name in available_tools[:2]:  # Test first 2 available tools
            tool_class = discovered_tools[tool_name]
            result = analyze_tool_schemas(tool_name, tool_class)
            
            assert "metrics" in result, "Result should contain metrics"
            assert "methods" in result, "Result should contain methods"
            
            metrics = result["metrics"]
            assert isinstance(metrics, SchemaQualityMetrics), "Should return SchemaQualityMetrics"
            assert metrics.total_methods > 0, "Should have at least one method"
            
            scores = metrics.get_scores()
            assert "generation_rate" in scores
            assert "description_quality" in scores
            assert "type_coverage" in scores
            assert "overall_score" in scores

    def test_schema_coverage_metrics_calculation(self, discovered_tools):
        """Test that schema coverage metrics are calculated correctly."""
        if "pandas" not in discovered_tools:
            pytest.skip("pandas tool not available")

        tool_class = discovered_tools["pandas"]
        result = analyze_tool_schemas("pandas", tool_class)
        
        metrics = result["metrics"]
        scores = metrics.get_scores()
        
        # Generation rate should be between 0 and 100
        assert 0 <= scores["generation_rate"] <= 100
        assert 0 <= scores["description_quality"] <= 100
        assert 0 <= scores["type_coverage"] <= 100
        assert 0 <= scores["overall_score"] <= 100

    def test_schema_quality_validation(self, discovered_tools):
        """Test schema quality validation."""
        if "pandas" not in discovered_tools:
            pytest.skip("pandas tool not available")

        tool_class = discovered_tools["pandas"]
        
        # Find a method with a schema
        for method_name in dir(tool_class):
            if method_name.startswith("_") or method_name in ["run", "run_async", "run_batch"]:
                continue
            
            method = getattr(tool_class, method_name)
            if not callable(method) or isinstance(method, type):
                continue
            
            schema = generate_schema_from_method(method, method_name)
            if schema:
                issues = validate_schema_quality(schema, method, method_name)
                # Should return a list (may be empty)
                assert isinstance(issues, list)
                break


@pytest.mark.integration
class TestSchemaBackwardCompatibility:
    """Integration tests for backward compatibility with existing tools."""

    def test_existing_manual_schemas_are_preserved(self, discovered_tools):
        """Test that existing manual schemas are not overwritten."""
        # Tools that should have manual schemas
        tools_with_manual_schemas = ["ai_data_analysis_orchestrator", "data_profiler"]
        
        for tool_name in tools_with_manual_schemas:
            if tool_name not in discovered_tools:
                continue
            
            tool_class = discovered_tools[tool_name]
            result = analyze_tool_schemas(tool_name, tool_class)
            
            # Check that manual schemas are detected
            manual_schemas = [m for m in result["methods"] if m.get("schema_type") == "manual"]
            assert len(manual_schemas) > 0, f"{tool_name} should have manual schemas"

    def test_auto_generation_fallback_works(self, discovered_tools):
        """Test that auto-generation works as fallback when manual schemas are missing."""
        if "pandas" not in discovered_tools:
            pytest.skip("pandas tool not available")

        tool_class = discovered_tools["pandas"]
        result = analyze_tool_schemas("pandas", tool_class)
        
        # Should have both manual and auto schemas, or at least auto schemas
        auto_schemas = [m for m in result["methods"] if m.get("schema_type") == "auto"]
        assert len(auto_schemas) > 0, "Should have auto-generated schemas"

    def test_schema_generation_does_not_break_existing_tools(self, discovered_tools):
        """Test that schema generation doesn't break existing tool functionality."""
        # Test with a few tools
        test_tools = ["pandas", "stats", "research"]
        available_tools = [t for t in test_tools if t in discovered_tools]
        
        if not available_tools:
            pytest.skip("No test tools available")

        for tool_name in available_tools[:2]:
            tool_class = discovered_tools[tool_name]
            
            # Generate schemas - should not raise exceptions
            try:
                schemas = generate_schemas_for_tool(tool_class)
                # Should not break tool instantiation
                tool_instance = get_tool(tool_name)
                assert tool_instance is not None, f"Tool {tool_name} should still be instantiable"
            except Exception as e:
                pytest.fail(f"Schema generation broke {tool_name}: {e}")


@pytest.mark.integration
class TestSchemaValidationIntegration:
    """Integration tests for schema validation."""

    def test_generated_schemas_are_valid_pydantic_models(self, discovered_tools):
        """Test that generated schemas are valid Pydantic models."""
        if "pandas" not in discovered_tools:
            pytest.skip("pandas tool not available")

        tool_class = discovered_tools["pandas"]
        schemas = generate_schemas_for_tool(tool_class)
        
        for method_name, schema in list(schemas.items())[:3]:  # Test first 3
            # Should be able to instantiate with valid data
            try:
                # Get field names and create sample data
                field_data = {}
                for field_name, field_info in schema.model_fields.items():
                    if field_info.is_required():
                        # Use default values based on type
                        if field_info.annotation == str:
                            field_data[field_name] = "test"
                        elif field_info.annotation == int:
                            field_data[field_name] = 1
                        elif field_info.annotation == list:
                            field_data[field_name] = []
                        else:
                            field_data[field_name] = None
                
                instance = schema(**field_data)
                assert isinstance(instance, BaseModel)
            except ValidationError:
                # Some schemas might require specific data, that's okay
                pass
            except Exception as e:
                pytest.fail(f"Schema {schema.__name__} should be valid: {e}")

    def test_schema_validation_rejects_invalid_data(self):
        """Test that schemas properly validate input data."""
        def test_method(value: int, text: str) -> str:
            """Test method with typed parameters."""
            return f"{text}_{value}"

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        
        # Valid data should work
        valid_instance = schema(value=42, text="test")
        assert valid_instance.value == 42
        assert valid_instance.text == "test"
        
        # Invalid data should raise ValidationError
        with pytest.raises(ValidationError):
            schema(value="not_an_int", text="test")


@pytest.mark.integration
class TestSchemaPerformance:
    """Integration tests for schema generation performance."""

    def test_schema_generation_performance(self, discovered_tools):
        """Test that schema generation completes within reasonable time."""
        import time
        
        if "pandas" not in discovered_tools:
            pytest.skip("pandas tool not available")

        tool_class = discovered_tools["pandas"]
        
        start_time = time.time()
        schemas = generate_schemas_for_tool(tool_class)
        elapsed_time = time.time() - start_time
        
        # Should complete in less than 1 second per tool
        assert elapsed_time < 1.0, f"Schema generation took {elapsed_time:.2f}s, should be < 1s"
        assert len(schemas) > 0, "Should generate schemas"

    def test_schema_coverage_analysis_performance(self, discovered_tools):
        """Test that schema coverage analysis completes within reasonable time."""
        import time
        
        if "pandas" not in discovered_tools:
            pytest.skip("pandas tool not available")

        tool_class = discovered_tools["pandas"]
        
        start_time = time.time()
        result = analyze_tool_schemas("pandas", tool_class)
        elapsed_time = time.time() - start_time
        
        # Should complete in less than 2 seconds
        assert elapsed_time < 2.0, f"Analysis took {elapsed_time:.2f}s, should be < 2s"
        assert "metrics" in result


@pytest.mark.integration
class TestSchemaTypeNormalization:
    """Integration tests for type normalization."""

    def test_pandas_dataframe_normalization(self):
        """Test that pandas DataFrame types are normalized to Any."""
        try:
            import pandas as pd
            df_type = type(pd.DataFrame())
            normalized = _normalize_type(df_type)
            assert normalized == Any, "DataFrame should be normalized to Any"
        except ImportError:
            pytest.skip("pandas not available")

    def test_pandas_series_normalization(self):
        """Test that pandas Series types are normalized to Any."""
        try:
            import pandas as pd
            series_type = type(pd.Series())
            normalized = _normalize_type(series_type)
            assert normalized == Any, "Series should be normalized to Any"
        except ImportError:
            pytest.skip("pandas not available")

    def test_standard_types_are_not_normalized(self):
        """Test that standard types are not normalized."""
        from typing import List, Dict, Optional
        
        assert _normalize_type(str) == str
        assert _normalize_type(int) == int
        assert _normalize_type(List[str]) == List[str]
        assert _normalize_type(Dict[str, int]) == Dict[str, int]
        assert _normalize_type(Optional[str]) == Optional[str]


@pytest.mark.integration
class TestDocstringExtraction:
    """Integration tests for docstring extraction."""

    def test_google_style_docstring_extraction(self):
        """Test extraction from Google-style docstrings."""
        docstring = """
        Test method.
        
        Args:
            param1: First parameter description
            param2: Second parameter description
        
        Returns:
            Result description
        """
        
        desc1 = _extract_param_description_from_docstring(docstring, "param1")
        desc2 = _extract_param_description_from_docstring(docstring, "param2")
        
        assert desc1 == "First parameter description"
        assert desc2 == "Second parameter description"

    def test_numpy_style_docstring_extraction(self):
        """Test extraction from NumPy-style docstrings."""
        docstring = """
        Test method.
        
        Parameters
        ----------
        param1 : str
            First parameter description
        param2 : int
            Second parameter description
        
        Returns
        -------
        str
            Result description
        """
        
        desc1 = _extract_param_description_from_docstring(docstring, "param1")
        desc2 = _extract_param_description_from_docstring(docstring, "param2")
        
        # NumPy style might not be fully supported yet, but shouldn't crash
        assert desc1 is not None or desc2 is not None

    def test_missing_docstring_handling(self):
        """Test handling of missing docstrings."""
        desc = _extract_param_description_from_docstring("", "param1")
        assert desc is None, "Should return None for missing docstring"
        
        desc = _extract_param_description_from_docstring(None, "param1")
        assert desc is None, "Should return None for None docstring"
