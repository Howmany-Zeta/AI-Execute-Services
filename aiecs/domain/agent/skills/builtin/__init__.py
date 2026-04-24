# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Built-in Skills Directory

This directory contains the default built-in skills that ship with AIECS.
Skills are auto-discovered from this directory when the skills system initializes.

Each skill is a subdirectory containing:
- SKILL.md: Skill definition with YAML frontmatter and markdown body
- references/: Optional reference documents
- examples/: Optional example files
- scripts/: Optional executable scripts
- assets/: Optional static assets

To add a new built-in skill:
1. Create a new subdirectory with the skill name (e.g., python-coding/)
2. Add a SKILL.md file with the skill definition
3. Add any supporting files in the appropriate subdirectories

See the design documentation for the full SKILL.md format specification.
"""
