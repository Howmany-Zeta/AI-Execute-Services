"""
自动 Schema 生成工具

从方法签名和类型注解自动生成 Pydantic Schema
"""

import inspect
import logging
from typing import Any, Dict, List, Optional, Type, get_type_hints, Union
from pydantic import BaseModel, Field, create_model, ConfigDict

logger = logging.getLogger(__name__)


def _normalize_type(param_type: Type) -> Type:
    """
    标准化类型，处理不支持的类型

    将 pandas.DataFrame 等复杂类型映射为 Any
    """
    # 获取类型名称
    type_name = getattr(param_type, '__name__', str(param_type))

    # 检查是否是 pandas 类型
    if 'DataFrame' in type_name or 'Series' in type_name:
        return Any

    return param_type


def _extract_param_description_from_docstring(docstring: str, param_name: str) -> Optional[str]:
    """
    从文档字符串中提取参数描述

    支持格式:
    - Google style: Args: param_name: description
    - NumPy style: Parameters: param_name : type description
    """
    if not docstring:
        return None

    lines = docstring.split('\n')
    in_args_section = False
    current_param = None
    description_lines = []

    for line in lines:
        stripped = line.strip()

        # 检测 Args/Parameters 部分
        if stripped in ['Args:', 'Arguments:', 'Parameters:']:
            in_args_section = True
            continue

        # 检测结束
        if in_args_section and stripped in ['Returns:', 'Raises:', 'Yields:', 'Examples:', 'Note:', 'Notes:']:
            break

        if in_args_section:
            # Google style: param_name: description 或 param_name (type): description
            if ':' in stripped and not stripped.startswith(' '):
                # 保存之前的参数
                if current_param == param_name and description_lines:
                    return ' '.join(description_lines).strip()

                # 解析新参数
                parts = stripped.split(':', 1)
                if len(parts) == 2:
                    # 移除可能的类型注解 (type)
                    param_part = parts[0].strip()
                    if '(' in param_part:
                        param_part = param_part.split('(')[0].strip()

                    current_param = param_part
                    description_lines = [parts[1].strip()]
            elif current_param and stripped:
                # 继续描述
                description_lines.append(stripped)

    # 检查最后一个参数
    if current_param == param_name and description_lines:
        return ' '.join(description_lines).strip()

    return None


def generate_schema_from_method(
    method: callable,
    method_name: str,
    base_class: Type[BaseModel] = BaseModel
) -> Optional[Type[BaseModel]]:
    """
    从方法签名自动生成 Pydantic Schema

    Args:
        method: 要生成 Schema 的方法
        method_name: 方法名称
        base_class: Schema 基类

    Returns:
        生成的 Pydantic Schema 类，如果无法生成则返回 None
    """
    try:
        # 获取方法签名
        sig = inspect.signature(method)

        # 获取类型注解
        try:
            type_hints = get_type_hints(method)
        except Exception as e:
            logger.debug(f"Failed to get type hints for {method_name}: {e}")
            type_hints = {}

        # 获取文档字符串
        docstring = inspect.getdoc(method) or f"Execute {method_name} operation"

        # 提取简短描述（第一行）
        first_line = docstring.split('\n')[0].strip()
        schema_description = first_line if first_line else f"Execute {method_name} operation"

        # 构建字段定义
        field_definitions = {}

        for param_name, param in sig.parameters.items():
            # 跳过 self 参数
            if param_name == 'self':
                continue

            # 获取参数类型并标准化
            param_type = type_hints.get(param_name, Any)
            param_type = _normalize_type(param_type)

            # 获取默认值
            has_default = param.default != inspect.Parameter.empty
            default_value = param.default if has_default else ...

            # 从文档字符串提取参数描述
            field_description = _extract_param_description_from_docstring(docstring, param_name)
            if not field_description:
                field_description = f"Parameter {param_name}"

            # 创建 Field
            if has_default:
                if default_value is None:
                    # Optional 参数
                    field_definitions[param_name] = (
                        param_type,
                        Field(default=None, description=field_description)
                    )
                else:
                    field_definitions[param_name] = (
                        param_type,
                        Field(default=default_value, description=field_description)
                    )
            else:
                # 必需参数
                field_definitions[param_name] = (
                    param_type,
                    Field(description=field_description)
                )

        # 如果没有参数（除了 self），返回 None
        if not field_definitions:
            logger.debug(f"No parameters found for {method_name}, skipping schema generation")
            return None

        # 生成 Schema 类名
        schema_name = f"{method_name.title().replace('_', '')}Schema"

        # 创建 Schema 类，允许任意类型
        schema_class = create_model(
            schema_name,
            __base__=base_class,
            __doc__=schema_description,
            __config__=ConfigDict(arbitrary_types_allowed=True),
            **field_definitions
        )

        logger.debug(f"Generated schema {schema_name} for method {method_name}")
        return schema_class

    except Exception as e:
        logger.warning(f"Failed to generate schema for {method_name}: {e}")
        return None


def generate_schemas_for_tool(tool_class: Type) -> Dict[str, Type[BaseModel]]:
    """
    为工具类的所有方法生成 Schema
    
    Args:
        tool_class: 工具类
        
    Returns:
        方法名到 Schema 类的映射
    """
    schemas = {}
    
    for method_name in dir(tool_class):
        # 跳过私有方法和特殊方法
        if method_name.startswith('_'):
            continue
        
        # 跳过基类方法
        if method_name in ['run', 'run_async', 'run_batch']:
            continue
        
        method = getattr(tool_class, method_name)
        
        # 跳过非方法属性
        if not callable(method):
            continue
        
        # 跳过类（如 Config, Schema 等）
        if isinstance(method, type):
            continue
        
        # 生成 Schema
        schema = generate_schema_from_method(method, method_name)
        
        if schema:
            # 标准化方法名（移除下划线，转小写）
            normalized_name = method_name.replace('_', '').lower()
            schemas[normalized_name] = schema
            logger.info(f"Generated schema for {method_name}")
    
    return schemas





# 使用示例
if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/home/coder1/python-middleware-dev')

    from aiecs.tools import discover_tools, TOOL_CLASSES

    # 配置日志
    logging.basicConfig(level=logging.INFO)

    # 发现工具
    discover_tools()

    # 为 PandasTool 生成 Schema
    print("为 PandasTool 生成 Schema:")
    print("=" * 80)

    pandas_tool = TOOL_CLASSES['pandas']
    schemas = generate_schemas_for_tool(pandas_tool)

    print(f"\n生成了 {len(schemas)} 个 Schema:\n")

    # 显示前3个示例
    for method_name, schema in list(schemas.items())[:3]:
        print(f"{schema.__name__}:")
        print(f"  描述: {schema.__doc__}")
        print(f"  字段:")
        for field_name, field_info in schema.model_fields.items():
            required = "必需" if field_info.is_required() else "可选"
            default = f" (默认: {field_info.default})" if not field_info.is_required() and field_info.default is not None else ""
            print(f"    - {field_name}: {field_info.description} [{required}]{default}")
        print()

