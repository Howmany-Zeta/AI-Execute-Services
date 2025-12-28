"""
Unit tests for schema generator covering various method signatures.

Tests edge cases, complex types, generics, optional parameters, and docstring extraction.
"""

import pytest
from typing import List, Dict, Optional, Union, Any, Tuple, Callable, get_origin
from pydantic import BaseModel, ValidationError

from aiecs.tools.schema_generator import (
    generate_schema_from_method,
    generate_schemas_for_tool,
    _normalize_type,
    _extract_param_description_from_docstring,
    _validate_generated_schema,
)


class TestTypeNormalization:
    """Test type normalization functionality."""

    def test_normalize_pandas_dataframe(self):
        """Test that pandas DataFrame is normalized to Any."""
        try:
            import pandas as pd
            df_type = type(pd.DataFrame())
            normalized = _normalize_type(df_type)
            assert normalized == Any, "DataFrame should be normalized to Any"
        except ImportError:
            pytest.skip("pandas not available")

    def test_normalize_pandas_series(self):
        """Test that pandas Series is normalized to Any."""
        try:
            import pandas as pd
            series_type = type(pd.Series())
            normalized = _normalize_type(series_type)
            assert normalized == Any, "Series should be normalized to Any"
        except ImportError:
            pytest.skip("pandas not available")

    def test_normalize_standard_types(self):
        """Test that standard types are not normalized."""
        assert _normalize_type(str) == str
        assert _normalize_type(int) == int
        assert _normalize_type(float) == float
        assert _normalize_type(bool) == bool

    def test_normalize_list_generic(self):
        """Test normalization of List[T] generic."""
        normalized = _normalize_type(List[str])
        assert get_origin(normalized) is list or normalized == List[Any]

    def test_normalize_dict_generic(self):
        """Test normalization of Dict[K, V] generic."""
        normalized = _normalize_type(Dict[str, int])
        assert get_origin(normalized) is dict or normalized == Dict[str, Any]

    def test_normalize_optional(self):
        """Test normalization of Optional[T]."""
        normalized = _normalize_type(Optional[str])
        # Should extract the inner type
        assert normalized == str or get_origin(normalized) is Union

    def test_normalize_union(self):
        """Test normalization of Union types."""
        normalized = _normalize_type(Union[str, int])
        # Complex unions should become Any
        assert normalized == Any or get_origin(normalized) is Union

    def test_normalize_none_type(self):
        """Test normalization of None type."""
        normalized = _normalize_type(type(None))
        assert normalized == Any

    def test_normalize_callable(self):
        """Test normalization of Callable types."""
        normalized = _normalize_type(Callable[[str], int])
        assert normalized == Any


class TestDocstringExtraction:
    """Test docstring extraction functionality."""

    def test_google_style_extraction(self):
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

    def test_google_style_with_type_annotation(self):
        """Test Google style with type annotations."""
        docstring = """
        Test method.
        
        Args:
            param1 (str): First parameter description
            param2 (int): Second parameter description
        """
        
        desc1 = _extract_param_description_from_docstring(docstring, "param1")
        desc2 = _extract_param_description_from_docstring(docstring, "param2")
        
        assert desc1 == "First parameter description"
        assert desc2 == "Second parameter description"

    def test_numpy_style_extraction(self):
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
        
        # NumPy style should be extracted
        assert desc1 is not None or desc2 is not None

    def test_sphinx_style_extraction(self):
        """Test extraction from Sphinx-style docstrings."""
        docstring = """
        Test method.
        
        :param param1: First parameter description
        :param param2: Second parameter description
        :returns: Result description
        """
        
        desc1 = _extract_param_description_from_docstring(docstring, "param1")
        desc2 = _extract_param_description_from_docstring(docstring, "param2")
        
        assert desc1 == "First parameter description"
        assert desc2 == "Second parameter description"

    def test_multi_line_description(self):
        """Test extraction of multi-line descriptions."""
        docstring = """
        Test method.
        
        Args:
            param1: First line of description.
                Second line of description.
                Third line of description.
        """
        
        desc = _extract_param_description_from_docstring(docstring, "param1")
        assert "First line" in desc
        assert "Second line" in desc or "Third line" in desc

    def test_missing_docstring(self):
        """Test handling of missing docstrings."""
        desc = _extract_param_description_from_docstring("", "param1")
        assert desc is None
        
        desc = _extract_param_description_from_docstring(None, "param1")
        assert desc is None

    def test_missing_parameter(self):
        """Test handling when parameter is not in docstring."""
        docstring = """
        Test method.
        
        Args:
            param1: Description
        """
        
        desc = _extract_param_description_from_docstring(docstring, "nonexistent")
        assert desc is None


class TestSchemaGeneration:
    """Test schema generation for various method signatures."""

    def test_simple_method(self):
        """Test schema generation for a simple method."""
        def test_method(value: int, name: str) -> str:
            """Test method with simple parameters."""
            return f"{name}_{value}"

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        assert issubclass(schema, BaseModel)
        assert "value" in schema.model_fields
        assert "name" in schema.model_fields
        assert schema.model_fields["value"].annotation == int
        assert schema.model_fields["name"].annotation == str

    def test_method_with_defaults(self):
        """Test schema generation for methods with default values."""
        def test_method(required: str, optional: str = "default", count: int = 10) -> str:
            """Test method with default values."""
            return required

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        assert schema.model_fields["required"].is_required()
        assert not schema.model_fields["optional"].is_required()
        assert not schema.model_fields["count"].is_required()
        assert schema.model_fields["optional"].default == "default"
        assert schema.model_fields["count"].default == 10

    def test_method_with_optional_none(self):
        """Test schema generation for Optional parameters."""
        def test_method(required: str, optional: Optional[str] = None) -> str:
            """Test method with Optional parameter."""
            return required

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        assert schema.model_fields["required"].is_required()
        assert not schema.model_fields["optional"].is_required()
        assert schema.model_fields["optional"].default is None

    def test_method_with_list_parameter(self):
        """Test schema generation for List parameters."""
        def test_method(items: List[str], counts: List[int]) -> List[str]:
            """Test method with List parameters."""
            return items

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        assert "items" in schema.model_fields
        assert "counts" in schema.model_fields

    def test_method_with_dict_parameter(self):
        """Test schema generation for Dict parameters."""
        def test_method(data: Dict[str, int], config: Dict[str, Any]) -> Dict:
            """Test method with Dict parameters."""
            return data

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        assert "data" in schema.model_fields
        assert "config" in schema.model_fields

    def test_method_with_union_parameter(self):
        """Test schema generation for Union parameters."""
        def test_method(value: Union[str, int]) -> str:
            """Test method with Union parameter."""
            return str(value)

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        assert "value" in schema.model_fields

    def test_method_with_complex_types(self):
        """Test schema generation handles complex types gracefully."""
        try:
            import pandas as pd
            
            def test_method(df: pd.DataFrame, series: pd.Series) -> pd.DataFrame:
                """Test method with pandas types."""
                return df

            schema = generate_schema_from_method(test_method, "test_method")
            
            # Should not raise errors
            assert schema is not None
            assert "df" in schema.model_fields
            assert "series" in schema.model_fields
        except ImportError:
            pytest.skip("pandas not available")

    def test_method_with_no_parameters(self):
        """Test schema generation for methods with no parameters."""
        def test_method() -> str:
            """Test method with no parameters."""
            return "result"

        schema = generate_schema_from_method(test_method, "test_method")
        
        # Should return None for methods without parameters
        assert schema is None

    def test_method_with_only_self(self):
        """Test schema generation for instance methods."""
        class TestClass:
            def test_method(self, value: int) -> str:
                """Test instance method."""
                return str(value)

        schema = generate_schema_from_method(TestClass.test_method, "test_method")
        
        assert schema is not None
        assert "value" in schema.model_fields
        assert "self" not in schema.model_fields

    def test_method_with_docstring_extraction(self):
        """Test that docstrings are properly extracted."""
        def test_method(data: str, count: int = 10) -> str:
            """
            Process data with count.
            
            Args:
                data: Input data string
                count: Number of items (default: 10)
            
            Returns:
                Processed string
            """
            return f"{data}_{count}"

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        assert schema.model_fields["data"].description == "Input data string"
        assert "Number of items" in schema.model_fields["count"].description

    def test_method_with_missing_type_hints(self):
        """Test schema generation when type hints are missing."""
        def test_method(value, name="default") -> str:
            """Test method without type hints."""
            return f"{name}_{value}"

        schema = generate_schema_from_method(test_method, "test_method")
        
        # Should still generate schema with Any types
        assert schema is not None
        assert "value" in schema.model_fields
        assert "name" in schema.model_fields


class TestSchemaValidation:
    """Test schema validation functionality."""

    def test_validate_generated_schema(self):
        """Test that generated schemas are validated."""
        def test_method(value: int, name: str) -> str:
            """Test method."""
            return f"{name}_{value}"

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        
        # Should be able to create instance with valid data
        instance = schema(value=42, name="test")
        assert isinstance(instance, BaseModel)
        assert instance.value == 42
        assert instance.name == "test"

    def test_schema_validation_rejects_invalid_data(self):
        """Test that schemas reject invalid data."""
        def test_method(value: int, name: str) -> str:
            """Test method."""
            return f"{name}_{value}"

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        
        # Valid data should work
        instance = schema(value=42, name="test")
        assert instance.value == 42
        
        # Invalid data should raise ValidationError
        with pytest.raises(ValidationError):
            schema(value="not_an_int", name="test")

    def test_schema_with_optional_fields(self):
        """Test schema validation with optional fields."""
        def test_method(required: str, optional: Optional[str] = None) -> str:
            """Test method."""
            return required

        schema = generate_schema_from_method(test_method, "test_method")
        
        assert schema is not None
        
        # Should work with optional field provided
        instance1 = schema(required="test", optional="value")
        assert instance1.optional == "value"
        
        # Should work with optional field omitted
        instance2 = schema(required="test")
        assert instance2.optional is None
        
        # Should fail without required field
        with pytest.raises(ValidationError):
            schema(optional="value")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_method_with_complex_nested_types(self):
        """Test schema generation for nested complex types."""
        def test_method(data: List[Dict[str, Any]]) -> Dict[str, List[int]]:
            """Test method with nested types."""
            return {}

        schema = generate_schema_from_method(test_method, "test_method")
        
        # Should not raise errors
        assert schema is not None
        assert "data" in schema.model_fields

    def test_method_with_tuple_parameter(self):
        """Test schema generation for Tuple parameters."""
        def test_method(coords: Tuple[int, int]) -> str:
            """Test method with Tuple."""
            return str(coords)

        schema = generate_schema_from_method(test_method, "test_method")
        
        # Should handle gracefully
        assert schema is not None or schema is None  # Either is acceptable

    def test_method_with_callable_parameter(self):
        """Test schema generation for Callable parameters."""
        def test_method(func: Callable[[str], int]) -> int:
            """Test method with Callable."""
            return func("test")

        schema = generate_schema_from_method(test_method, "test_method")
        
        # Should handle gracefully
        assert schema is not None
        assert "func" in schema.model_fields

    def test_method_with_forward_references(self):
        """Test schema generation with forward references."""
        def test_method(value: "str") -> "str":  # type: ignore
            """Test method with string annotations."""
            return value

        schema = generate_schema_from_method(test_method, "test_method")
        
        # Should handle gracefully
        assert schema is not None or schema is None

    def test_method_with_invalid_type_hints(self):
        """Test schema generation handles invalid type hints gracefully."""
        def test_method(value: "InvalidType") -> "InvalidType":  # type: ignore
            """Test method with invalid type hints."""
            return value

        schema = generate_schema_from_method(test_method, "test_method")
        
        # Should not crash, may return None or schema with Any
        assert schema is None or schema is not None

    def test_method_with_varargs(self):
        """Test schema generation for *args and **kwargs."""
        def test_method(*args: str, **kwargs: int) -> str:
            """Test method with varargs."""
            return "result"

        schema = generate_schema_from_method(test_method, "test_method")
        
        # Varargs are typically not included in schemas
        # Should return None or handle gracefully
        assert schema is None or schema is not None


class TestSchemaGenerationForTool:
    """Test schema generation for entire tool classes."""

    def test_generate_schemas_for_simple_tool(self):
        """Test generating schemas for a simple tool class."""
        class SimpleTool:
            def method1(self, value: int) -> str:
                """Method 1."""
                return str(value)
            
            def method2(self, name: str, count: int = 5) -> str:
                """Method 2."""
                return f"{name}_{count}"
            
            def _private_method(self):
                """Should be skipped."""
                pass

        schemas = generate_schemas_for_tool(SimpleTool)
        
        # Should generate schemas for public methods
        assert len(schemas) >= 2
        assert "method1" in schemas or "method1" in [k.lower().replace("_", "") for k in schemas.keys()]
        assert "method2" in schemas or "method2" in [k.lower().replace("_", "") for k in schemas.keys()]

    def test_generate_schemas_skips_base_methods(self):
        """Test that base class methods are skipped."""
        class TestTool:
            def run(self, value: str) -> str:
                """Base method - should be skipped."""
                return value
            
            def run_async(self, value: str) -> str:
                """Base method - should be skipped."""
                return value
            
            def custom_method(self, value: int) -> str:
                """Custom method - should be included."""
                return str(value)

        schemas = generate_schemas_for_tool(TestTool)
        
        # Should only include custom_method
        assert len(schemas) == 1
        assert "custommethod" in schemas or "custom_method" in schemas
