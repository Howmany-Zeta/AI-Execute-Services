# 工具自动发现机制

## 📋 概述

从现在开始，**无需手动维护工具列表**！系统会自动发现所有使用 `@register_tool` 装饰器注册的工具。

## ✨ 特性

### 1. 自动工具发现
- ✅ 自动扫描 `aiecs/tools/task_tools/`、`aiecs/tools/docs/`、`aiecs/tools/statistics/` 目录
- ✅ 自动识别所有 `@register_tool` 装饰器
- ✅ 自动提取工具名称和描述
- ✅ 自动分类（task/docs/statistics）

### 2. 零维护成本
- ✅ 添加新工具：只需在工具类上添加 `@register_tool("tool_name")` 装饰器
- ✅ 删除工具：直接删除文件或移除装饰器
- ✅ 重命名工具：修改装饰器参数即可
- ✅ 无需修改任何配置文件

## 🔧 工作原理

### aiecs/tools/__init__.py

```python
def _auto_discover_tools():
    """自动发现所有工具"""
    # 扫描工具目录
    for dir_name, category in [('task_tools', 'task'), ('docs', 'docs'), ('statistics', 'statistics')]:
        # 查找所有 Python 文件
        for filename in os.listdir(dir_path):
            # 读取文件内容
            # 使用正则表达式查找 @register_tool 装饰器
            pattern = r'@register_tool\([\'"]([^\'"]+)[\'"]\)'
            matches = re.findall(pattern, content)
            # 提取工具名称和描述
            # 注册为占位符，等待懒加载
```

### verify_tools.py

```python
def auto_discover_tool_modules():
    """自动发现工具模块映射"""
    # 扫描工具目录
    # 查找 @register_tool 装饰器
    # 建立工具名称到模块路径的映射
    # 返回映射表供动态加载使用
```

## 📝 如何添加新工具

### 步骤 1: 创建工具文件

在合适的目录创建工具文件（例如：`aiecs/tools/task_tools/my_new_tool.py`）

### 步骤 2: 添加装饰器

```python
from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool

@register_tool("my_new_tool")
class MyNewTool(BaseTool):
    """
    这是一个新工具的简短描述。
    
    这个描述会被自动提取并显示在工具列表中。
    """
    
    def my_method(self, param: str) -> str:
        """执行某个操作"""
        return f"Result: {param}"
```

### 步骤 3: 验证

运行验证脚本查看新工具是否被发现：

```bash
poetry run python -m aiecs.scripts.tools_develop.verify_tools
```

就这样！**无需修改任何其他文件**！

## 🎯 支持的目录结构

```
aiecs/tools/
├── task_tools/          # 任务工具 (category: task)
│   ├── chart_tool.py    # @register_tool("chart")
│   ├── pandas_tool.py   # @register_tool("pandas")
│   └── ...
├── docs/                # 文档工具 (category: docs)
│   ├── document_parser_tool.py    # @register_tool("document_parser")
│   ├── document_writer_tool.py    # @register_tool("document_writer")
│   └── ...
└── statistics/          # 统计工具 (category: statistics)
    ├── data_loader_tool.py        # @register_tool("data_loader")
    ├── data_profiler_tool.py      # @register_tool("data_profiler")
    └── ...
```

## 🔍 描述提取规则

系统会自动提取类文档字符串的**第一行**作为工具描述：

```python
@register_tool("example")
class ExampleTool(BaseTool):
    """
    这一行会被用作工具描述 ✅
    
    下面的内容不会被提取。
    可以写详细的文档说明。
    """
```

**建议**：
- 第一行保持简短（< 200 字符）
- 清晰描述工具的主要功能
- 避免使用多行描述

## 📊 当前发现的工具统计

截至最后扫描，系统发现了 **26 个工具**：

- **任务工具** (10个)：chart, classifier, image, office, pandas, report, research, scraper, search, stats
- **文档工具** (7个)：document_parser, document_writer, document_creator, document_layout, content_insertion, ai_document_orchestrator, ai_document_writer_orchestrator
- **数据统计工具** (9个)：data_loader, data_profiler, data_transformer, data_visualizer, model_trainer, statistical_analyzer, ai_data_analysis_orchestrator, ai_insight_generator, ai_report_orchestrator

## ⚡ 性能优化

### 占位符机制
- 工具发现时创建轻量级占位符
- 不导入实际工具模块（避免重依赖）
- 只在实际使用时才加载工具

### 懒加载
- `verify_tools.py` 只在用户选择工具时才加载模块
- 避免启动时加载所有工具
- 提高响应速度

## 🧪 测试验证

### 验证工具发现
```bash
poetry run python -m aiecs.scripts.tools_develop.verify_tools
```

### 验证特定工具
在交互模式中输入工具名称或序号：
```
👉 请选择工具 > pandas
👉 请选择工具 > 7
```

### 验证描述提取
检查工具列表中的描述是否正确提取自类文档字符串。

## 🔄 兼容性

### 向后兼容
- 现有工具无需修改
- 只要有 `@register_tool` 装饰器即可被发现
- 保持与现有代码的兼容性

### 新增目录支持
如果未来需要添加新的工具目录（如 `aiecs/tools/ml_tools/`），只需修改两处：

1. **aiecs/tools/__init__.py**
```python
tool_dirs = [
    ('task_tools', 'task'),
    ('docs', 'docs'),
    ('statistics', 'statistics'),
    ('ml_tools', 'ml'),  # 新增
]
```

2. **verify_tools.py**
```python
tool_dirs = {
    'task_tools': 'aiecs.tools.task_tools',
    'docs': 'aiecs.tools.docs',
    'statistics': 'aiecs.tools.statistics',
    'ml_tools': 'aiecs.tools.ml_tools',  # 新增
}
```

## ❓ 常见问题

### Q: 工具没有被发现？
**A:** 检查以下几点：
1. 文件是否在支持的目录中（task_tools/docs/statistics）
2. 是否使用了 `@register_tool("name")` 装饰器
3. 文件名是否以 `.py` 结尾且不是 `__init__.py`

### Q: 描述显示不正确？
**A:** 检查类文档字符串：
1. 文档字符串必须紧跟类定义
2. 使用三引号 `"""`
3. 确保第一行是简短描述

### Q: 如何重命名工具？
**A:** 只需修改装饰器参数：
```python
# 旧
@register_tool("old_name")

# 新
@register_tool("new_name")
```

### Q: 如何临时禁用工具？
**A:** 两种方法：
1. 注释掉 `@register_tool` 装饰器
2. 移动文件到其他目录

## 🎉 优势总结

| 特性 | 手动维护 | 自动发现 |
|------|---------|---------|
| 添加工具 | 需修改配置文件 | 只需添加装饰器 ✅ |
| 删除工具 | 需修改配置文件 | 直接删除文件 ✅ |
| 维护成本 | 高 | 零 ✅ |
| 出错风险 | 容易遗漏 | 自动同步 ✅ |
| 描述准确性 | 可能不一致 | 直接提取 ✅ |

---

**维护者**: AIECS Tools Team  
**最后更新**: 2025-10-14

