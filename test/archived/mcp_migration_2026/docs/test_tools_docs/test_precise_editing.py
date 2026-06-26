"""
Test suite for precise editing features in DocumentWriterTool

Tests the new occurrence-based replacement, line range support,
and SEARCH/REPLACE block parsing functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path

from aiecs.tools.docs.document_writer_tool import DocumentWriterTool, DocumentFormat, WriteMode


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def doc_writer(temp_dir):
    """Create a DocumentWriterTool instance with temp directory"""
    config = {
        "temp_dir": temp_dir,
        "backup_dir": os.path.join(temp_dir, "backups"),
        "enable_backup": True,
    }
    return DocumentWriterTool(config=config)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file with repeated content"""
    file_path = os.path.join(temp_dir, "sample.txt")
    content = """Line 1: Hello World
Line 2: Hello World
Line 3: Hello World
Line 4: Goodbye World
Line 5: Hello World
Line 6: Hello World
Line 7: Different content
Line 8: Hello World
Line 9: Hello World
Line 10: Final line"""
    
    with open(file_path, "w") as f:
        f.write(content)
    
    return file_path


class TestOccurrenceReplacement:
    """Test occurrence-based replacement functionality"""
    
    def test_replace_first_occurrence(self, doc_writer, sample_file):
        """Test replacing only the first occurrence"""
        result = doc_writer.find_replace(
            target_path=sample_file,
            find_text="Hello World",
            replace_text="Hi Universe",
            replace_all=False
        )
        
        assert result["replacements_made"] == 1
        
        # Verify only first occurrence was replaced
        with open(sample_file, "r") as f:
            content = f.read()
        
        assert content.count("Hi Universe") == 1
        assert content.count("Hello World") == 6  # 7 total - 1 replaced
    
    def test_replace_specific_occurrence(self, doc_writer, sample_file):
        """Test replacing a specific occurrence (3rd)"""
        result = doc_writer.find_replace(
            target_path=sample_file,
            find_text="Hello World",
            replace_text="Hi Universe",
            occurrence=3
        )
        
        assert result["replacements_made"] == 1
        assert result["occurrence_replaced"] == 3
        assert result["total_matches"] == 7
        
        # Verify only 3rd occurrence was replaced
        with open(sample_file, "r") as f:
            lines = f.readlines()
        
        assert "Hi Universe" in lines[2]  # Line 3 (0-indexed)
        assert "Hello World" in lines[0]  # Line 1 unchanged
        assert "Hello World" in lines[1]  # Line 2 unchanged
    
    def test_replace_last_occurrence(self, doc_writer, sample_file):
        """Test replacing the last occurrence"""
        result = doc_writer.find_replace(
            target_path=sample_file,
            find_text="Hello World",
            replace_text="Hi Universe",
            occurrence=7  # Last occurrence
        )
        
        assert result["replacements_made"] == 1
        assert result["occurrence_replaced"] == 7
    
    def test_occurrence_out_of_range(self, doc_writer, sample_file):
        """Test requesting an occurrence that doesn't exist"""
        result = doc_writer.find_replace(
            target_path=sample_file,
            find_text="Hello World",
            replace_text="Hi Universe",
            occurrence=100  # Way more than available
        )
        
        assert result["replacements_made"] == 0
        # Content should be unchanged


class TestLineRangeReplacement:
    """Test line range-based replacement functionality"""
    
    def test_replace_in_line_range(self, doc_writer, sample_file):
        """Test replacing all occurrences within a line range"""
        result = doc_writer.find_replace(
            target_path=sample_file,
            find_text="Hello World",
            replace_text="Hi Universe",
            replace_all=True,
            start_line=2,
            end_line=5
        )

        # Should replace occurrences in lines 2-5 (3 occurrences: lines 2, 3, 5)
        # Line 4 has "Goodbye World" so no match
        assert result["replacements_made"] == 3
        assert result["line_range"]["start"] == 2
        assert result["line_range"]["end"] == 5

        # Verify replacements only in specified range
        with open(sample_file, "r") as f:
            lines = f.readlines()

        assert "Hello World" in lines[0]  # Line 1 unchanged
        assert "Hi Universe" in lines[1]  # Line 2 changed
        assert "Hi Universe" in lines[4]  # Line 5 changed
        assert "Hello World" in lines[7]  # Line 8 unchanged

    def test_replace_specific_occurrence_in_range(self, doc_writer, sample_file):
        """Test replacing a specific occurrence within a line range"""
        result = doc_writer.find_replace(
            target_path=sample_file,
            find_text="Hello World",
            replace_text="Hi Universe",
            occurrence=2,  # 2nd occurrence within the range
            start_line=2,
            end_line=6
        )

        assert result["replacements_made"] == 1
        assert result["occurrence_replaced"] == 2

        # Verify only 2nd occurrence in range was replaced
        with open(sample_file, "r") as f:
            lines = f.readlines()

        # Line 1 should be unchanged (outside range)
        assert "Hello World" in lines[0]
        # Line 2 should be unchanged (1st in range)
        assert "Hello World" in lines[1]
        # Line 3 should be changed (2nd in range)
        assert "Hi Universe" in lines[2]

    def test_line_range_start_only(self, doc_writer, sample_file):
        """Test line range with only start_line specified"""
        result = doc_writer.find_replace(
            target_path=sample_file,
            find_text="Hello World",
            replace_text="Hi Universe",
            replace_all=True,
            start_line=6
        )

        # Should replace from line 6 to end
        assert result["replacements_made"] == 3  # Lines 6, 8, 9

        with open(sample_file, "r") as f:
            lines = f.readlines()

        # Lines 1-5 should have Hello World
        assert "Hello World" in lines[0]
        # Lines 6+ should have Hi Universe
        assert "Hi Universe" in lines[5]


class TestSearchReplaceBlocks:
    """Test SEARCH/REPLACE block parsing and execution"""

    def test_single_block(self, doc_writer, temp_dir):
        """Test parsing and executing a single SEARCH/REPLACE block"""
        file_path = os.path.join(temp_dir, "code.py")
        content = """def old_function():
    pass

def another_function():
    return True"""

        with open(file_path, "w") as f:
            f.write(content)

        blocks = """<<<<<<< SEARCH
def old_function():
    pass
=======
def new_function():
    return False
>>>>>>> REPLACE"""

        result = doc_writer.search_replace_blocks(
            target_path=file_path,
            blocks=blocks
        )

        assert result["blocks_processed"] == 1
        assert result["blocks_successful"] == 1
        assert result["total_replacements"] == 1

        with open(file_path, "r") as f:
            new_content = f.read()

        assert "def new_function():" in new_content
        assert "def old_function():" not in new_content
        assert "def another_function():" in new_content  # Unchanged

    def test_multiple_blocks(self, doc_writer, temp_dir):
        """Test parsing and executing multiple SEARCH/REPLACE blocks"""
        file_path = os.path.join(temp_dir, "config.py")
        content = """OLD_CONSTANT = 1
ANOTHER_CONSTANT = 2
THIRD_CONSTANT = 3"""

        with open(file_path, "w") as f:
            f.write(content)

        blocks = """<<<<<<< SEARCH
OLD_CONSTANT = 1
=======
NEW_CONSTANT = 100
>>>>>>> REPLACE

<<<<<<< SEARCH
THIRD_CONSTANT = 3
=======
UPDATED_CONSTANT = 300
>>>>>>> REPLACE"""

        result = doc_writer.search_replace_blocks(
            target_path=file_path,
            blocks=blocks
        )

        assert result["blocks_processed"] == 2
        assert result["blocks_successful"] == 2
        assert result["total_replacements"] == 2

        with open(file_path, "r") as f:
            new_content = f.read()

        assert "NEW_CONSTANT = 100" in new_content
        assert "UPDATED_CONSTANT = 300" in new_content
        assert "ANOTHER_CONSTANT = 2" in new_content  # Unchanged

    def test_block_with_no_match(self, doc_writer, temp_dir):
        """Test SEARCH/REPLACE block when search text doesn't exist"""
        file_path = os.path.join(temp_dir, "test.txt")
        content = "Some content here"

        with open(file_path, "w") as f:
            f.write(content)

        blocks = """<<<<<<< SEARCH
nonexistent text
=======
replacement
>>>>>>> REPLACE"""

        result = doc_writer.search_replace_blocks(
            target_path=file_path,
            blocks=blocks
        )

        assert result["blocks_processed"] == 1
        assert result["blocks_successful"] == 0
        assert result["total_replacements"] == 0
        assert len(result["errors"]) > 0

    def test_invalid_blocks(self, doc_writer, temp_dir):
        """Test handling of invalid block format"""
        file_path = os.path.join(temp_dir, "test.txt")
        content = "Some content"

        with open(file_path, "w") as f:
            f.write(content)

        blocks = "This is not a valid SEARCH/REPLACE block"

        result = doc_writer.search_replace_blocks(
            target_path=file_path,
            blocks=blocks
        )

        assert result["blocks_processed"] == 0
        assert result["total_replacements"] == 0


class TestCaseSensitivity:
    """Test case sensitivity in replacements"""

    def test_case_insensitive_occurrence(self, doc_writer, temp_dir):
        """Test case-insensitive replacement with occurrence"""
        file_path = os.path.join(temp_dir, "case.txt")
        content = "hello HELLO Hello HeLLo"

        with open(file_path, "w") as f:
            f.write(content)

        result = doc_writer.find_replace(
            target_path=file_path,
            find_text="hello",
            replace_text="hi",
            occurrence=3,
            case_sensitive=False
        )

        assert result["replacements_made"] == 1
        assert result["occurrence_replaced"] == 3

        with open(file_path, "r") as f:
            new_content = f.read()

        # Third occurrence (Hello) should be replaced
        assert new_content.count("hello") == 1
        assert new_content.count("HELLO") == 1
        assert new_content.count("hi") == 1  # Replaced "Hello"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

