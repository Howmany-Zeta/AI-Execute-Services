#!/usr/bin/env python3
"""
Script to check documentation files for:
1. Chinese language content
2. Broken internal reference links
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict
import sys


def contains_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    # Chinese Unicode ranges
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    return bool(chinese_pattern.search(text))


def extract_markdown_links(content: str) -> List[Tuple[str, str]]:
    """Extract all markdown links from content.
    
    Returns list of tuples: (link_text, link_path)
    """
    # Remove code blocks to avoid false positives
    # Split by code block markers and process only non-code sections
    lines = content.split('\n')
    in_code_block = False
    non_code_content = []
    
    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            continue
        if not in_code_block:
            non_code_content.append(line)
    
    content_without_code = '\n'.join(non_code_content)
    
    # Pattern for markdown links: [text](path)
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    links = []
    
    for match in link_pattern.finditer(content_without_code):
        link_text = match.group(1)
        link_path = match.group(2)
        # Skip external links (http/https/mailto)
        if not link_path.startswith(('http://', 'https://', 'mailto:', '#')):
            links.append((link_text, link_path))
    
    return links


def resolve_link_path(link_path: str, base_file: Path) -> Path:
    """Resolve a relative link path to an absolute file path.
    
    Handles:
    - Relative paths: ./file.md, ../file.md
    - Absolute paths from docs root: /user/DOMAIN_AGENT/file.md
    - File references without extension
    - Code file references (skip validation)
    """
    # Find the docs root directory (the parent of user/ or developer/)
    current = base_file.parent
    while current.name not in ('user', 'developer') and current.parent != current:
        current = current.parent
    docs_root = current.parent if current.name in ('user', 'developer') else base_file.parent
    
    # Remove anchor if present
    link_path = link_path.split('#')[0]
    
    if not link_path:
        return None
    
    # Skip code file references (they're outside docs)
    code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs'}
    if any(link_path.endswith(ext) for ext in code_extensions):
        return None  # Skip validation for code files
    
    # Skip links to directories (they might be valid)
    if link_path.endswith('/'):
        return None
    
    # Skip links to external repos or openspec (outside docs/user)
    # But allow links to developer/ directory
    if 'openspec' in link_path or (link_path.startswith('../../') and 'developer/' not in link_path):
        return None
    
    # Handle absolute paths from docs root
    if link_path.startswith('/'):
        # Remove leading slash and resolve from docs root
        link_path = link_path.lstrip('/')
        if link_path.startswith('user/') or link_path.startswith('developer/'):
            resolved = docs_root / link_path
        else:
            resolved = docs_root / link_path
    else:
        # Relative path
        resolved = (base_file.parent / link_path).resolve()
    
    # Try with .md extension if no extension
    if not resolved.suffix:
        resolved = resolved.with_suffix('.md')
    
    # Try without .md if it has .md (for Sphinx references)
    if not resolved.exists() and resolved.suffix == '.md':
        alt_resolved = resolved.with_suffix('')
        if alt_resolved.exists():
            return alt_resolved
    
    # Only validate files within docs directory (including developer/)
    if resolved.exists():
        try:
            # Check if file is within docs directory (user/ or developer/)
            rel_path = resolved.relative_to(docs_root)
            if str(rel_path).startswith('user/') or str(rel_path).startswith('developer/'):
                return resolved
        except ValueError:
            pass  # File exists but outside docs directory
    
    return None


def check_file(file_path: Path, docs_root: Path) -> Dict:
    """Check a single file for issues.
    
    Returns dict with:
    - has_chinese: bool
    - chinese_lines: List[int]
    - broken_links: List[Tuple[str, str]]  # (link_text, link_path)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        return {
            'error': str(e),
            'has_chinese': False,
            'chinese_lines': [],
            'broken_links': []
        }
    
    # Check for Chinese
    chinese_lines = []
    for i, line in enumerate(lines, 1):
        if contains_chinese(line):
            chinese_lines.append(i)
    
    # Check for broken links
    broken_links = []
    links = extract_markdown_links(content)
    
    for link_text, link_path in links:
        resolved = resolve_link_path(link_path, file_path)
        if resolved is None:
            broken_links.append((link_text, link_path))
    
    return {
        'has_chinese': len(chinese_lines) > 0,
        'chinese_lines': chinese_lines,
        'broken_links': broken_links
    }


def scan_directory(directory: Path) -> Dict:
    """Scan all markdown files in directory recursively.
    
    Returns dict with:
    - chinese_files: List[Tuple[Path, List[int]]]
    - broken_link_files: List[Tuple[Path, List[Tuple[str, str]]]]
    """
    chinese_files = []
    broken_link_files = []
    errors = []
    
    docs_root = directory.parent if directory.name in ('user', 'developer') else directory
    
    for md_file in directory.rglob('*.md'):
        result = check_file(md_file, docs_root)
        
        if 'error' in result:
            errors.append((md_file, result['error']))
            continue
        
        if result['has_chinese']:
            chinese_files.append((md_file, result['chinese_lines']))
        
        if result['broken_links']:
            broken_link_files.append((md_file, result['broken_links']))
    
    return {
        'chinese_files': chinese_files,
        'broken_link_files': broken_link_files,
        'errors': errors
    }


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check documentation for Chinese content and broken links')
    parser.add_argument('--output', '-o', type=str, help='Output results to file')
    parser.add_argument('--chinese-only', action='store_true', help='Only check for Chinese content')
    parser.add_argument('--links-only', action='store_true', help='Only check for broken links')
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    user_dir = script_dir / 'user'
    
    if not user_dir.exists():
        print(f"Error: {user_dir} does not exist")
        sys.exit(1)
    
    output_lines = []
    
    def print_and_capture(*args, **kwargs):
        """Print and optionally capture output."""
        line = ' '.join(str(arg) for arg in args)
        print(*args, **kwargs)
        output_lines.append(line)
    
    print_and_capture("=" * 80)
    print_and_capture("Documentation Check Script")
    print_and_capture("=" * 80)
    print_and_capture(f"\nScanning: {user_dir}")
    print_and_capture()
    
    results = scan_directory(user_dir)
    
    # Report Chinese files
    if not args.links_only:
        print_and_capture("=" * 80)
        print_and_capture("CHINESE CONTENT DETECTION")
        print_and_capture("=" * 80)
        if results['chinese_files']:
            print_and_capture(f"\nFound {len(results['chinese_files'])} file(s) with Chinese content:\n")
            for file_path, lines in results['chinese_files']:
                rel_path = file_path.relative_to(script_dir)
                print_and_capture(f"  📄 {rel_path}")
                print_and_capture(f"     Chinese content found on lines: {', '.join(map(str, lines[:10]))}")
                if len(lines) > 10:
                    print_and_capture(f"     ... and {len(lines) - 10} more lines")
                print_and_capture()
        else:
            print_and_capture("\n✅ No Chinese content detected in user-facing documentation.\n")
    
    # Report broken links
    if not args.chinese_only:
        print_and_capture("=" * 80)
        print_and_capture("BROKEN INTERNAL LINKS")
        print_and_capture("=" * 80)
        if results['broken_link_files']:
            print_and_capture(f"\nFound {len(results['broken_link_files'])} file(s) with broken links:\n")
            for file_path, broken_links in results['broken_link_files']:
                rel_path = file_path.relative_to(script_dir)
                print_and_capture(f"  📄 {rel_path}")
                for link_text, link_path in broken_links:
                    print_and_capture(f"     ❌ [{link_text}]({link_path})")
                print_and_capture()
        else:
            print_and_capture("\n✅ No broken internal links found.\n")
    
    # Report errors
    if results['errors']:
        print_and_capture("=" * 80)
        print_and_capture("ERRORS")
        print_and_capture("=" * 80)
        for file_path, error in results['errors']:
            rel_path = file_path.relative_to(script_dir)
            print_and_capture(f"  ⚠️  {rel_path}: {error}")
        print_and_capture()
    
    # Summary
    print_and_capture("=" * 80)
    print_and_capture("SUMMARY")
    print_and_capture("=" * 80)
    print_and_capture(f"Files with Chinese content: {len(results['chinese_files'])}")
    print_and_capture(f"Files with broken links: {len(results['broken_link_files'])}")
    print_and_capture(f"Files with errors: {len(results['errors'])}")
    print_and_capture()
    
    # Write to file if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_lines))
        print(f"\nResults written to: {args.output}")
    
    # Exit code
    if results['chinese_files'] or results['broken_link_files'] or results['errors']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()

