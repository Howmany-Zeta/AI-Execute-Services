"""
Test API exposure of DocumentWriterTool enhanced methods

Verifies that the new find_replace parameters and search_replace_blocks
method are properly exposed via the tool's API schema.
"""

import pytest
from pydantic import BaseModel

from aiecs.tools.docs.document_writer_tool import DocumentWriterTool


class TestAPIExposure:
    """Test that enhanced methods are properly exposed via API"""
    
    def test_find_replace_schema_exists(self):
        """Test that Find_replaceSchema is defined"""
        tool = DocumentWriterTool()
        
        # Check that the schema class exists
        assert hasattr(DocumentWriterTool, 'Find_replaceSchema')
        schema_class = DocumentWriterTool.Find_replaceSchema
        
        # Verify it's a Pydantic model
        assert issubclass(schema_class, BaseModel)
    
    def test_find_replace_schema_has_new_fields(self):
        """Test that Find_replaceSchema includes new parameters"""
        schema_class = DocumentWriterTool.Find_replaceSchema
        
        # Get the model fields
        fields = schema_class.model_fields
        
        # Verify all required fields exist
        assert 'target_path' in fields
        assert 'find_text' in fields
        assert 'replace_text' in fields
        assert 'replace_all' in fields
        
        # Verify new fields exist
        assert 'occurrence' in fields, "occurrence parameter should be in schema"
        assert 'start_line' in fields, "start_line parameter should be in schema"
        assert 'end_line' in fields, "end_line parameter should be in schema"
        
        # Verify existing fields
        assert 'case_sensitive' in fields
        assert 'regex_mode' in fields
    
    def test_find_replace_schema_field_types(self):
        """Test that schema fields have correct types"""
        schema_class = DocumentWriterTool.Find_replaceSchema
        fields = schema_class.model_fields
        
        # Check that occurrence is Optional[int]
        occurrence_field = fields['occurrence']
        assert occurrence_field.default is None, "occurrence should default to None"
        
        # Check that start_line is Optional[int]
        start_line_field = fields['start_line']
        assert start_line_field.default is None, "start_line should default to None"
        
        # Check that end_line is Optional[int]
        end_line_field = fields['end_line']
        assert end_line_field.default is None, "end_line should default to None"
    
    def test_find_replace_schema_validation(self):
        """Test that schema validation works correctly"""
        schema_class = DocumentWriterTool.Find_replaceSchema
        
        # Valid schema with all new parameters
        valid_data = {
            'target_path': 'test.txt',
            'find_text': 'old',
            'replace_text': 'new',
            'occurrence': 3,
            'start_line': 10,
            'end_line': 50
        }
        
        instance = schema_class(**valid_data)
        assert instance.occurrence == 3
        assert instance.start_line == 10
        assert instance.end_line == 50
        
        # Valid schema without new parameters (backward compatible)
        minimal_data = {
            'target_path': 'test.txt',
            'find_text': 'old',
            'replace_text': 'new'
        }
        
        instance = schema_class(**minimal_data)
        assert instance.occurrence is None
        assert instance.start_line is None
        assert instance.end_line is None
    
    def test_search_replace_blocks_schema_exists(self):
        """Test that Search_replace_blocksSchema is defined"""
        tool = DocumentWriterTool()
        
        # Check that the schema class exists
        assert hasattr(DocumentWriterTool, 'Search_replace_blocksSchema')
        schema_class = DocumentWriterTool.Search_replace_blocksSchema
        
        # Verify it's a Pydantic model
        assert issubclass(schema_class, BaseModel)
    
    def test_search_replace_blocks_schema_fields(self):
        """Test that Search_replace_blocksSchema has correct fields"""
        schema_class = DocumentWriterTool.Search_replace_blocksSchema
        fields = schema_class.model_fields
        
        # Verify required fields
        assert 'target_path' in fields
        assert 'blocks' in fields
        assert 'case_sensitive' in fields
    
    def test_search_replace_blocks_schema_validation(self):
        """Test that Search_replace_blocksSchema validation works"""
        schema_class = DocumentWriterTool.Search_replace_blocksSchema
        
        blocks_text = """
<<<<<<< SEARCH
old text
=======
new text
>>>>>>> REPLACE
"""
        
        valid_data = {
            'target_path': 'test.py',
            'blocks': blocks_text,
            'case_sensitive': True
        }
        
        instance = schema_class(**valid_data)
        assert instance.target_path == 'test.py'
        assert instance.blocks == blocks_text
        assert instance.case_sensitive is True
    
    def test_tool_schemas_registered(self):
        """Test that schemas are properly registered in the tool"""
        tool = DocumentWriterTool()

        # Access the internal _schemas dict (this is how BaseTool stores schemas)
        schemas = tool._schemas

        # Verify find_replace schema is registered
        assert 'find_replace' in schemas, "find_replace schema should be registered"
        assert schemas['find_replace'] is not None, "find_replace schema should not be None"

        # Verify search_replace_blocks schema is registered
        assert 'search_replace_blocks' in schemas, "search_replace_blocks schema should be registered"
        assert schemas['search_replace_blocks'] is not None, "search_replace_blocks schema should not be None"

        # Verify the schemas are the correct classes
        assert schemas['find_replace'] == DocumentWriterTool.Find_replaceSchema
        assert schemas['search_replace_blocks'] == DocumentWriterTool.Search_replace_blocksSchema


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

