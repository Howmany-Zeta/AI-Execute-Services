"""
Integration tests for schema generation.

Tests schema auto-generation in a real environment with actual tool classes.
"""

import pytest
from typing import Any
from pydantic import BaseModel, ValidationError

from aiecs.tools import discover_tools, TOOL_CLASSES, get_tool
from aiecs.tools.schema_generator import (
    generate_schema_from_method,
    generate_schemas_for_tool,
    _normalize_type,
    _extract_param_description_from_docstring,
)


@pytest.fixture(scope="module")
def discovered_tools():
    """Discover all tools once for the test module."""
    discover_tools()
    return TOOL_CLASSES


@pytest.mark.integration
class TestSchemaGenerationIntegration:
    """Integration tests for schema generation functionality."""

    def test_schema_generation_for_image_tool(self, discovered_tools):
        """Test schema generation for image tool methods."""
        if "image" not in discovered_tools:
            pytest.skip("image tool not available")

        image_tool = discovered_tools["image"]
        schemas = generate_schemas_for_tool(image_tool)

        assert len(schemas) > 0, "Should generate at least one schema"

        for method_name, schema in schemas.items():
            assert hasattr(schema, "model_fields"), "Schema should have model_fields"
            assert schema.__doc__, "Schema should have a docstring"
            assert issubclass(schema, BaseModel), f"Schema for {method_name} should be a BaseModel"
            assert schema.__name__.endswith("Schema"), "Schema name should end with 'Schema'"

    def test_schema_generation_handles_complex_types(self, discovered_tools):
        """Test that schema generation handles complex types gracefully."""
        if "image" not in discovered_tools:
            pytest.skip("image tool not available")

        image_tool = discovered_tools["image"]

        for method_name in dir(image_tool):
            if method_name.startswith("_") or not callable(getattr(image_tool, method_name)):
                continue

            method = getattr(image_tool, method_name)
            if isinstance(method, type):
                continue

            try:
                schema = generate_schema_from_method(method, method_name)
                if schema:
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
class TestSchemaBackwardCompatibility:
    """Integration tests for backward compatibility with existing tools."""

    def test_schema_generation_does_not_break_existing_tools(self, discovered_tools):
        """Test that schema generation doesn't break existing tool functionality."""
        test_tools = ["image", "search"]
        available_tools = [t for t in test_tools if t in discovered_tools]

        if not available_tools:
            pytest.skip("No test tools available")

        for tool_name in available_tools[:2]:
            tool_class = discovered_tools[tool_name]

            try:
                generate_schemas_for_tool(tool_class)
                tool_instance = get_tool(tool_name)
                assert tool_instance is not None, f"Tool {tool_name} should still be instantiable"
            except Exception as e:
                pytest.fail(f"Schema generation broke {tool_name}: {e}")


@pytest.mark.integration
class TestSchemaValidationIntegration:
    """Integration tests for schema validation."""

    def test_generated_schemas_are_valid_pydantic_models(self, discovered_tools):
        """Test that generated schemas are valid Pydantic models."""
        if "image" not in discovered_tools:
            pytest.skip("image tool not available")

        tool_class = discovered_tools["image"]
        schemas = generate_schemas_for_tool(tool_class)

        for method_name, schema in list(schemas.items())[:3]:
            try:
                field_data = {}
                for field_name, field_info in schema.model_fields.items():
                    if field_info.is_required():
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

        valid_instance = schema(value=42, text="test")
        assert valid_instance.value == 42
        assert valid_instance.text == "test"

        with pytest.raises(ValidationError):
            schema(value="not_an_int", text="test")


@pytest.mark.integration
class TestSchemaPerformance:
    """Integration tests for schema generation performance."""

    def test_schema_generation_performance(self, discovered_tools):
        """Test that schema generation completes within reasonable time."""
        import time

        if "image" not in discovered_tools:
            pytest.skip("image tool not available")

        tool_class = discovered_tools["image"]

        start_time = time.time()
        schemas = generate_schemas_for_tool(tool_class)
        elapsed_time = time.time() - start_time

        assert elapsed_time < 1.0, f"Schema generation took {elapsed_time:.2f}s, should be < 1s"
        assert len(schemas) > 0, "Should generate schemas"


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

        assert desc1 is not None or desc2 is not None

    def test_missing_docstring_handling(self):
        """Test handling of missing docstrings."""
        desc = _extract_param_description_from_docstring("", "param1")
        assert desc is None, "Should return None for missing docstring"

        desc = _extract_param_description_from_docstring(None, "param1")
        assert desc is None, "Should return None for None docstring"
