#!/usr/bin/env python3
"""
Example usage of the Open Library API provider.

This example demonstrates how to:
1. Search for books by title, author, or ISBN
2. Get detailed information about works and editions
3. Search for authors
4. Browse books by subject

Open Library is a free, open API that provides access to millions of books
and bibliographic data. No API key is required.
"""

from aiecs.tools.apisource.providers.openlibrary import OpenLibraryProvider


def main():
    """Run Open Library API examples"""

    # Initialize the provider (no API key needed)
    config = {
        'timeout': 30,
        'rate_limit': 10,
        'max_burst': 20,
    }

    provider = OpenLibraryProvider(config)

    print("=" * 80)
    print("Open Library API Provider Examples")
    print("=" * 80)

    # Example 1: Search for books by title
    print("\n1. Searching for books by title: 'The Lord of the Rings'")
    print("-" * 80)
    result = provider.search_books(q="the lord of the rings", limit=3)
    print(f"Found {len(result['data'])} results")
    for i, book in enumerate(result['data'][:3], 1):
        title = book.get('title', 'N/A')
        author = book.get('author_name', ['N/A'])[0] if book.get('author_name') else 'N/A'
        year = book.get('first_publish_year', 'N/A')
        print(f"  {i}. {title} by {author} ({year})")

    # Example 2: Search for books by author
    print("\n2. Searching for books by author: 'J.R.R. Tolkien'")
    print("-" * 80)
    result = provider.search_books(author="J.R.R. Tolkien", limit=5)
    print(f"Found {len(result['data'])} results")
    for i, book in enumerate(result['data'][:5], 1):
        title = book.get('title', 'N/A')
        year = book.get('first_publish_year', 'N/A')
        print(f"  {i}. {title} ({year})")

    # Example 3: Search for books by ISBN
    print("\n3. Searching for book by ISBN: '9780140328721'")
    print("-" * 80)
    result = provider.search_books(isbn="9780140328721", limit=1)
    if result['data']:
        book = result['data'][0]
        title = book.get('title', 'N/A')
        author = book.get('author_name', ['N/A'])[0] if book.get('author_name') else 'N/A'
        publisher = book.get('publisher', ['N/A'])[0] if book.get('publisher') else 'N/A'
        print(f"  Title: {title}")
        print(f"  Author: {author}")
        print(f"  Publisher: {publisher}")

    # Example 4: Get work details
    print("\n4. Getting work details for 'The Lord of the Rings' (OL27448W)")
    print("-" * 80)
    result = provider.get_work(work_id="OL27448W")
    work = result['data']
    title = work.get('title', 'N/A')
    description = work.get('description', 'N/A')
    if isinstance(description, dict):
        description = description.get('value', 'N/A')
    print(f"  Title: {title}")
    print(f"  Description: {description[:200]}..." if len(str(description)) > 200 else f"  Description: {description}")

    # Example 5: Search for authors
    print("\n5. Searching for authors: 'Mark Twain'")
    print("-" * 80)
    result = provider.search_authors(q="Mark Twain", limit=3)
    print(f"Found {len(result['data'])} results")
    for i, author in enumerate(result['data'][:3], 1):
        name = author.get('name', 'N/A')
        birth_date = author.get('birth_date', 'N/A')
        work_count = author.get('work_count', 0)
        print(f"  {i}. {name} (born: {birth_date}, works: {work_count})")

    # Example 6: Browse books by subject
    print("\n6. Browsing books by subject: 'science_fiction'")
    print("-" * 80)
    result = provider.get_subject(subject="science_fiction", limit=5)
    works = result['data']
    if isinstance(works, dict):
        works = works.get('works', [])
    print(f"Found {len(works)} results")
    for i, work in enumerate(works[:5], 1):
        title = work.get('title', 'N/A')
        authors = work.get('authors', [])
        author_name = authors[0].get('name', 'N/A') if authors else 'N/A'
        print(f"  {i}. {title} by {author_name}")

    # Example 7: Get operation schema
    print("\n7. Getting operation schema for 'search_books'")
    print("-" * 80)
    schema = provider.get_operation_schema('search_books')
    print(f"  Description: {schema['description']}")
    print("  Parameters:")
    for param_name, param_info in schema['parameters'].items():
        required = "required" if param_info.get('required', False) else "optional"
        print(f"    - {param_name} ({param_info['type']}, {required}): {param_info['description']}")

    print("\n" + "=" * 80)
    print("Examples completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()

