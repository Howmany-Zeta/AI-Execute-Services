#!/usr/bin/env python3
"""
命令行测试脚本：验证 ImageTool YAML 配置加载功能

测试内容：
1. 标准路径配置加载 (config/tools/image.yaml, image_tool.yaml)
2. 自定义路径配置加载 (config/app/tool_config/image_tool.yaml)
3. 多种命名约定支持
4. 配置优先级验证

使用方法：
    poetry run python test_image_tool_yaml_config.py
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from aiecs.config.tool_config import get_tool_config_loader
from aiecs.tools.task_tools.image_tool import ImageTool


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_test_result(test_name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"   {details}")


def create_test_config(config_dir: Path, filename: str, config: Dict[str, Any]) -> Path:
    """Create a test YAML config file."""
    import yaml
    
    config_path = config_dir / filename
    config_dir.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    return config_path


def test_standard_path_config():
    """Test 1: 标准路径配置加载 (config/tools/image.yaml)"""
    print_section("Test 1: 标准路径配置加载")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config_dir = tmp_path / "config" / "tools"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test config
        test_config = {
            "max_file_size_mb": 100,
            "allowed_extensions": [".jpg", ".png", ".gif"],
            "tesseract_pool_size": 4,
            "default_ocr_language": "eng+chi_sim",  # 多语言配置
        }
        
        config_file = create_test_config(config_dir, "image.yaml", test_config)
        print(f"Created config file: {config_file}")
        
        # Set config path and load tool
        loader = get_tool_config_loader()
        loader.set_config_path(tmp_path / "config")
        
        try:
            tool = ImageTool()
            
            # Verify config loaded
            assert tool.config.max_file_size_mb == 100, f"Expected 100, got {tool.config.max_file_size_mb}"
            assert tool.config.tesseract_pool_size == 4, f"Expected 4, got {tool.config.tesseract_pool_size}"
            assert tool.config.default_ocr_language == "eng+chi_sim", f"Expected 'eng+chi_sim', got {tool.config.default_ocr_language}"
            assert ".gif" in tool.config.allowed_extensions, "GIF extension not found"
            
            print_test_result(
                "标准路径配置加载",
                True,
                f"成功加载配置: max_file_size_mb={tool.config.max_file_size_mb}, "
                f"default_ocr_language={tool.config.default_ocr_language}"
            )
            return True
        except Exception as e:
            print_test_result("标准路径配置加载", False, f"错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            loader.set_config_path(None)


def test_multiple_naming_conventions():
    """Test 2: 多种命名约定支持"""
    print_section("Test 2: 多种命名约定支持")
    
    test_cases = [
        ("image.yaml", "image.yaml"),
        ("image_tool.yaml", "image_tool.yaml"),
        ("ImageTool.yaml", "ImageTool.yaml"),
    ]
    
    results = []
    
    for filename, description in test_cases:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = tmp_path / "config" / "tools"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            test_config = {
                "max_file_size_mb": 75,
                "default_ocr_language": "chi_sim",
            }
            
            config_file = create_test_config(config_dir, filename, test_config)
            print(f"Created config file: {config_file}")
            
            loader = get_tool_config_loader()
            loader.set_config_path(tmp_path / "config")
            
            try:
                tool = ImageTool()
                
                assert tool.config.max_file_size_mb == 75, f"Expected 75, got {tool.config.max_file_size_mb}"
                assert tool.config.default_ocr_language == "chi_sim", f"Expected 'chi_sim', got {tool.config.default_ocr_language}"
                
                print_test_result(
                    f"命名约定: {description}",
                    True,
                    f"成功加载: {filename}"
                )
                results.append(True)
            except Exception as e:
                print_test_result(f"命名约定: {description}", False, f"错误: {e}")
                results.append(False)
            finally:
                loader.set_config_path(None)
    
    return all(results)


def test_custom_path_config():
    """Test 3: 自定义路径配置加载 (config/app/tool_config/image_tool.yaml)"""
    print_section("Test 3: 自定义路径配置加载")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # 创建自定义路径结构: config/app/tool_config/
        custom_config_dir = tmp_path / "config" / "app" / "tool_config"
        custom_config_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建配置文件直接在 custom_config_dir 下（不在 tools 子目录）
        test_config = {
            "max_file_size_mb": 200,
            "allowed_extensions": [".jpg", ".jpeg", ".png", ".webp"],
            "tesseract_pool_size": 8,
            "default_ocr_language": "eng+jpn+chi_sim",  # 多语言配置
        }
        
        config_file = create_test_config(custom_config_dir, "image_tool.yaml", test_config)
        print(f"Created config file: {config_file}")
        print(f"Custom config path: {custom_config_dir}")
        
        # Set custom config path
        loader = get_tool_config_loader()
        loader.set_config_path(custom_config_dir)
        
        try:
            tool = ImageTool()
            
            # Verify config loaded from custom path
            assert tool.config.max_file_size_mb == 200, f"Expected 200, got {tool.config.max_file_size_mb}"
            assert tool.config.tesseract_pool_size == 8, f"Expected 8, got {tool.config.tesseract_pool_size}"
            assert tool.config.default_ocr_language == "eng+jpn+chi_sim", f"Expected 'eng+jpn+chi_sim', got {tool.config.default_ocr_language}"
            assert ".webp" in tool.config.allowed_extensions, "WebP extension not found"
            
            print_test_result(
                "自定义路径配置加载",
                True,
                f"成功从自定义路径加载配置: {config_file}\n"
                f"   max_file_size_mb={tool.config.max_file_size_mb}, "
                f"default_ocr_language={tool.config.default_ocr_language}"
            )
            return True
        except Exception as e:
            print_test_result("自定义路径配置加载", False, f"错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            loader.set_config_path(None)


def test_config_precedence():
    """Test 4: 配置优先级验证 (explicit > YAML > env > defaults)"""
    print_section("Test 4: 配置优先级验证")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        config_dir = tmp_path / "config" / "tools"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create YAML config
        yaml_config = {
            "max_file_size_mb": 50,
            "default_ocr_language": "eng",
        }
        create_test_config(config_dir, "image.yaml", yaml_config)
        
        loader = get_tool_config_loader()
        loader.set_config_path(tmp_path / "config")
        
        try:
            # Test: Explicit config should override YAML
            explicit_config = {
                "max_file_size_mb": 300,
                "default_ocr_language": "chi_sim",
            }
            tool = ImageTool(config=explicit_config)
            
            assert tool.config.max_file_size_mb == 300, "Explicit config should override YAML"
            assert tool.config.default_ocr_language == "chi_sim", "Explicit config should override YAML"
            
            print_test_result(
                "配置优先级",
                True,
                "显式配置成功覆盖 YAML 配置"
            )
            return True
        except Exception as e:
            print_test_result("配置优先级", False, f"错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            loader.set_config_path(None)


def test_multilanguage_config():
    """Test 5: 多语言配置验证"""
    print_section("Test 5: 多语言配置验证")
    
    test_cases = [
        ("eng", "English only"),
        ("chi_sim", "Simplified Chinese"),
        ("eng+chi_sim", "English + Chinese"),
        ("eng+jpn+chi_sim", "English + Japanese + Chinese"),
    ]
    
    results = []
    
    for lang_code, description in test_cases:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            config_dir = tmp_path / "config" / "tools"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            test_config = {
                "default_ocr_language": lang_code,
            }
            
            create_test_config(config_dir, "image.yaml", test_config)
            
            loader = get_tool_config_loader()
            loader.set_config_path(tmp_path / "config")
            
            try:
                tool = ImageTool()
                
                assert tool.config.default_ocr_language == lang_code, \
                    f"Expected '{lang_code}', got '{tool.config.default_ocr_language}'"
                
                print_test_result(
                    f"多语言配置: {description}",
                    True,
                    f"语言代码: {lang_code}"
                )
                results.append(True)
            except Exception as e:
                print_test_result(f"多语言配置: {description}", False, f"错误: {e}")
                results.append(False)
            finally:
                loader.set_config_path(None)
    
    return all(results)


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  ImageTool YAML 配置加载测试")
    print("=" * 70)
    
    tests = [
        ("标准路径配置加载", test_standard_path_config),
        ("多种命名约定支持", test_multiple_naming_conventions),
        ("自定义路径配置加载", test_custom_path_config),
        ("配置优先级验证", test_config_precedence),
        ("多语言配置验证", test_multilanguage_config),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{test_name}' 执行失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print_section("测试总结")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

