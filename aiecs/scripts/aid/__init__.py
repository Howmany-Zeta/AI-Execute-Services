# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
AIECS Development Tools (AID)

This module contains development and maintenance tools for the AIECS project.
"""

# Lazy import to avoid circular import issues


def get_version_manager_main():
    """Get the version manager main function"""
    from .version_manager import main

    return main


__all__ = [
    "get_version_manager_main",
]
