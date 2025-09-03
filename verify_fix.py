#!/usr/bin/env python3
"""
Verify that the office_tool fixes are properly loaded
"""
import inspect
from aiecs.tools.task_tools.office_tool import OfficeTool

def verify_fixes():
    print("🔍 Verifying office_tool fixes...")
    
    # Check if read_xlsx method contains the fix
    source = inspect.getsource(OfficeTool.read_xlsx)
    
    if "isinstance(data, pd.DataFrame)" in source:
        print("✅ XLSX DataFrame/dict handling fix is present")
    else:
        print("❌ XLSX fix NOT found - cache issue!")
        
    if "data = pd.read_excel" in source:
        print("✅ Variable name 'data' (not 'df') is present")
    else:
        print("❌ Old variable 'df' still present - cache issue!")
    
    # Check if _sanitize_data method contains the fix
    source = inspect.getsource(OfficeTool._sanitize_data)
    
    if "_sanitize_text(str(k))" in source:
        print("✅ Key sanitization fix is present")
    else:
        print("❌ Key sanitization fix NOT found - cache issue!")
    
    # Check if all individual verifications passed
    all_passed = all([
        "isinstance(data, pd.DataFrame)" in inspect.getsource(OfficeTool.read_xlsx),
        "data = pd.read_excel" in inspect.getsource(OfficeTool.read_xlsx),
        "_sanitize_text(str(k))" in inspect.getsource(OfficeTool._sanitize_data)
    ])
    
    print(f"\n🎯 {'All fixes are properly loaded!' if all_passed else 'Cache issues detected!'}")

if __name__ == "__main__":
    verify_fixes()
