# 工具配置检查器使用指南

> **AIECS 2.0:** `apisource`, `scraper_tool`, `statistics`, and built-in `knowledge_graph` tools were removed from core. This checker covers **active** tools (`task_tools`, `docs`, `search_tool`) only.

这个脚本用于检查所有注册工具的配置设置是否正确，并生成配置模板和文档，方便开发者配置和使用。

## 功能特性

✅ **配置验证**
- 检查所有工具是否正确使用 `self._config_obj`
- 验证 `__init__` 方法是否调用 `super().__init__()`
- 检测错误的配置模式

✅ **配置信息展示**
- 显示每个工具的配置字段
- 标识必需字段和可选字段
- 显示字段类型、默认值和描述

✅ **模板生成**
- 生成 JSON 格式的配置模板
- 生成 Markdown 格式的配置文档
- 提供配置示例和环境变量映射

## 使用方法

### 1. 基本检查

检查所有工具的配置是否正确：

```bash
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py
```

输出示例：
```
================================================================================
检查所有注册工具的配置设置
================================================================================

找到 29 个工具文件

✅ 正确配置 (29 个)
❌ 需要修复 (0 个)
📝 无需配置 (0 个)
```

### 2. 显示详细配置信息

查看每个工具的详细配置字段：

```bash
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py --show-config
```

输出示例：
```
(legacy APISourceTool examples removed in 2.0 — use `search_tool` / `docs` / custom `BaseTool`)
  配置字段 (11 个):
    • fred_api_key: Optional[str]
      🔴 必需
      默认值: None
      说明: API key for FRED API
    • newsapi_api_key: Optional[str]
      🟢 可选
      默认值: None
      说明: API key for News API
    ...
```

### 3. 生成 JSON 配置模板

生成 JSON 格式的配置模板文件：

```bash
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py --generate-template
```

默认输出文件：`tools_config_template.json`

自定义输出路径：
```bash
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py --generate-template --output /path/to/config.json
```

### 4. 生成 Markdown 配置文档

生成 Markdown 格式的配置文档：

```bash
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py --generate-markdown
```

默认输出文件：`TOOLS_CONFIG_GUIDE.md`

自定义输出路径：
```bash
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py --generate-markdown --markdown-output /path/to/guide.md
```

### 5. 组合使用

同时执行多个操作：

```bash
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py \
  --show-config \
  --generate-template \
  --generate-markdown
```

## 输出文件说明

### 1. tools_config_template.json

JSON 格式的配置模板，包含所有工具的配置字段：

```json
{
  "APISourceTool": {
    "fred_api_key": {
      "value": "your_fred_api_key_here",
      "type": "Optional[str]",
      "required": true,
      "description": "API key for FRED API"
    },
    ...
  }
}
```

### 2. TOOLS_CONFIG_GUIDE.md

Markdown 格式的完整配置指南，包含：
- 目录索引
- 每个工具的配置表格
- 配置示例代码
- 环境变量映射

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--show-config` | 显示每个工具的详细配置信息 |
| `--generate-template` | 生成 JSON 格式配置模板文件 |
| `--generate-markdown` | 生成 Markdown 格式配置文档 |
| `--output PATH` | 指定 JSON 模板输出路径 |
| `--markdown-output PATH` | 指定 Markdown 文档输出路径 |
| `-h, --help` | 显示帮助信息 |

## 配置状态说明

脚本会检查并报告以下状态：

### ✅ 正确配置 (CORRECT)
工具正确使用了 `self._config_obj` 模式：
```python
self.config = self._config_obj if self._config_obj else self.Config()
```

### ❌ 错误配置 (INCORRECT)
工具直接创建了 Config 对象，未使用 `self._config_obj`

### ⚠️ 混合模式 (MIXED)
工具同时包含正确和错误的配置模式

### 📝 无 Config 类 (NO_CONFIG)
工具没有定义 Config 类（可能不需要配置）

### 📝 无 __init__ 方法 (NO_INIT)
工具没有自定义的 `__init__` 方法

## 最佳实践

### 1. 定期检查

在开发过程中定期运行检查，确保所有工具配置正确：

```bash
# 在提交代码前运行
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py
```

### 2. 更新文档

当添加或修改工具配置时，重新生成文档：

```bash
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py --generate-markdown
```

### 3. 使用配置模板

新项目或环境配置时，使用生成的 JSON 模板作为起点：

```bash
# 生成模板
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py --generate-template

# 根据模板配置工具
# 编辑 tools_config_template.json
```

### 4. 查阅配置文档

配置工具前，先查阅 `TOOLS_CONFIG_GUIDE.md` 了解各字段含义：

```bash
# 生成配置文档
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py --generate-markdown

# 查看文档
less TOOLS_CONFIG_GUIDE.md
```

## 故障排查

### 问题：脚本无法找到工具文件

**解决方案**：确保在项目根目录运行脚本

```bash
cd /path/to/python-middleware-dev
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py
```

### 问题：配置检查失败

**解决方案**：查看详细错误信息，修正工具的 `__init__` 方法

```bash
# 查看详细信息
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py --show-config
```

### 问题：生成的文档不完整

**解决方案**：检查工具的 Config 类是否正确定义，字段是否有完整的类型注解

## 开发说明

### 扩展功能

如需扩展脚本功能，可修改以下函数：

- `extract_config_fields()`: 提取配置字段信息
- `generate_config_template()`: 生成 JSON 模板
- `generate_markdown_doc()`: 生成 Markdown 文档
- `print_config_details()`: 打印配置详情

### 测试

确保脚本能正确处理各种配置模式：

```bash
# 运行完整测试
poetry run python aiecs/scripts/tools_develop/check_all_tools_config.py --show-config --generate-template --generate-markdown
```

## 相关文件

- `check_all_tools_config.py`: 主脚本
- `test_all_tools_config_runtime.py`: 运行时配置测试
- `tools_config_template.json`: 生成的 JSON 配置模板
- `TOOLS_CONFIG_GUIDE.md`: 生成的 Markdown 配置文档

## 总结

这个工具帮助开发者：
- ✅ 确保所有工具配置正确
- 📝 快速查看工具配置参数
- 🚀 快速生成配置模板
- 📖 自动生成配置文档

使其成为 AIECS 项目开发和部署的重要辅助工具。
