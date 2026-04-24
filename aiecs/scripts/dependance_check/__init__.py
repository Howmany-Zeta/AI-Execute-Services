# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
依赖检查和修复工具

提供 AIECS 系统依赖的检查、修复和 NLP 数据下载功能。
"""

from .dependency_checker import main as dependency_checker_main
from .dependency_fixer import main as dependency_fixer_main
from .download_nlp_data import main as download_nlp_data_main

__all__ = [
    "dependency_checker_main",
    "dependency_fixer_main",
    "download_nlp_data_main",
]
