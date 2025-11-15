"""
Weasel 库补丁工具

修复 Weasel 库的验证器问题。
"""

from .fix_weasel_validator import main as fix_weasel_validator_main

__all__ = [
    "fix_weasel_validator_main",
]
