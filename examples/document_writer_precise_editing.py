"""
Examples demonstrating precise editing features in DocumentWriterTool

This file shows how to use the enhanced find_replace method with:
1. Occurrence-based replacement (replace nth occurrence)
2. Line range support (limit replacements to specific lines)
3. SEARCH/REPLACE block parsing (Cline/Claude Code format)
"""

from aiecs.tools.docs.document_writer_tool import DocumentWriterTool


def example_occurrence_replacement():
    """Example: Replace a specific occurrence"""
    tool = DocumentWriterTool()
    
    # Replace only the 3rd occurrence of "TODO"
    result = tool.find_replace(
        target_path="project/tasks.py",
        find_text="TODO",
        replace_text="DONE",
        occurrence=3  # Replace only the 3rd occurrence
    )
    
    print(f"Replaced occurrence {result['occurrence_replaced']} of {result['total_matches']}")
    # Output: Replaced occurrence 3 of 7


def example_line_range_replacement():
    """Example: Replace within a specific line range"""
    tool = DocumentWriterTool()
    
    # Replace all occurrences of "old_api" in lines 50-100
    result = tool.find_replace(
        target_path="project/api.py",
        find_text="old_api",
        replace_text="new_api",
        replace_all=True,
        start_line=50,
        end_line=100
    )
    
    print(f"Made {result['replacements_made']} replacements in lines {result['line_range']}")
    # Output: Made 5 replacements in lines {'start': 50, 'end': 100}


def example_occurrence_in_range():
    """Example: Replace specific occurrence within a line range"""
    tool = DocumentWriterTool()
    
    # Replace the 2nd occurrence of "config" in lines 10-30
    result = tool.find_replace(
        target_path="project/settings.py",
        find_text="config",
        replace_text="configuration",
        occurrence=2,  # 2nd occurrence within the range
        start_line=10,
        end_line=30
    )
    
    print(f"Replaced occurrence {result['occurrence_replaced']} in specified range")


def example_search_replace_blocks():
    """Example: Use SEARCH/REPLACE blocks (Cline/Claude Code format)"""
    tool = DocumentWriterTool()
    
    # Define multiple SEARCH/REPLACE blocks
    blocks = """
<<<<<<< SEARCH
def old_function():
    pass
=======
def new_function():
    return True
>>>>>>> REPLACE

<<<<<<< SEARCH
OLD_CONSTANT = 1
=======
NEW_CONSTANT = 100
>>>>>>> REPLACE
"""
    
    result = tool.search_replace_blocks(
        target_path="project/code.py",
        blocks=blocks
    )
    
    print(f"Processed {result['blocks_processed']} blocks")
    print(f"Successful: {result['blocks_successful']}")
    print(f"Total replacements: {result['total_replacements']}")
    
    # Check individual block results
    for block_result in result['results']:
        print(f"Block {block_result['block_number']}: {block_result['success']}")


def example_case_insensitive_occurrence():
    """Example: Case-insensitive replacement with occurrence"""
    tool = DocumentWriterTool()
    
    # Replace the 5th occurrence of "error" (case-insensitive)
    # Will match: error, Error, ERROR, ErRoR, etc.
    result = tool.find_replace(
        target_path="project/logs.txt",
        find_text="error",
        replace_text="warning",
        occurrence=5,
        case_sensitive=False
    )
    
    print(f"Replaced {result['occurrence_replaced']} of {result['total_matches']} matches")


def example_regex_with_occurrence():
    """Example: Regex replacement with occurrence"""
    tool = DocumentWriterTool()
    
    # Replace the 2nd occurrence of a date pattern
    result = tool.find_replace(
        target_path="project/dates.txt",
        find_text=r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD pattern
        replace_text="REDACTED",
        occurrence=2,
        regex_mode=True
    )
    
    print(f"Replaced occurrence {result['occurrence_replaced']}")


def example_practical_refactoring():
    """Example: Practical refactoring scenario"""
    tool = DocumentWriterTool()
    
    # Scenario: Rename a function in a specific class (lines 100-200)
    # but only the 1st occurrence (the definition, not the calls)
    result = tool.find_replace(
        target_path="project/service.py",
        find_text="def process_data(self, data):",
        replace_text="def process_dataset(self, data):",
        occurrence=1,
        start_line=100,
        end_line=200
    )
    
    if result['replacements_made'] > 0:
        print("Function definition renamed successfully")
    else:
        print("Function definition not found in specified range")


def example_batch_updates_with_blocks():
    """Example: Batch updates using SEARCH/REPLACE blocks"""
    tool = DocumentWriterTool()
    
    # Update multiple configuration values at once
    blocks = """
<<<<<<< SEARCH
DEBUG = True
=======
DEBUG = False
>>>>>>> REPLACE

<<<<<<< SEARCH
MAX_CONNECTIONS = 10
=======
MAX_CONNECTIONS = 100
>>>>>>> REPLACE

<<<<<<< SEARCH
TIMEOUT = 30
=======
TIMEOUT = 60
>>>>>>> REPLACE
"""
    
    result = tool.search_replace_blocks(
        target_path="project/config.py",
        blocks=blocks
    )
    
    if result['errors']:
        print("Some blocks had errors:")
        for error in result['errors']:
            print(f"  - {error}")
    else:
        print(f"All {result['blocks_processed']} configuration updates successful!")


if __name__ == "__main__":
    print("DocumentWriterTool Precise Editing Examples")
    print("=" * 50)
    print("\nThese examples demonstrate the enhanced find_replace capabilities:")
    print("1. Occurrence-based replacement")
    print("2. Line range support")
    print("3. SEARCH/REPLACE block parsing")
    print("\nSee the function definitions above for usage examples.")

