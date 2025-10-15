# 工具开发辅助脚本

本目录包含用于 AIECS 工具开发和维护的验证脚本，帮助开发者确保工具质量和 Schema 自动生成的有效性。

## 📋 脚本列表

### 1. 工具验证器 (`verify_tools.py`)

快速验证和展示 aiecs.tools 注册的所有工具和功能，帮助开发者了解工具注册情况。

**用途**：
- 列出所有注册的工具及其状态
- 显示每个工具的描述和功能方法
- 提供工具使用示例
- 分析工具注册表信息
- 展示工具继承关系和模块分布

**命令**：
```bash
# 从项目根目录运行（推荐）
python -m aiecs.scripts.tools_develop.verify_tools

# 直接运行脚本
python aiecs/scripts/tools_develop/verify_tools.py
```

**输出示例**：
```
================================================================================
AIECS Tools 注册工具验证
================================================================================

发现 26 个注册的工具

================================================================================
📁 任务工具 (10 个)
================================================================================

[1] chart
    描述: Chart and visualization operations
    状态: loaded

[2] pandas
    描述: Data analysis and manipulation
    状态: loaded

... (更多工具)

================================================================================
📁 文档工具 (7 个)
================================================================================

[11] document_parser
    描述: Document parsing and content extraction
    状态: loaded

... (更多工具)

================================================================================
📁 数据统计工具 (9 个)
================================================================================

[18] data_loader
    描述: Universal data loading from multiple formats
    状态: loaded

... (更多工具)

================================================================================
✅ 工具列表显示完成! 共 26 个工具
================================================================================

================================================================================
🎮 交互模式
================================================================================

提示:
  - 输入工具序号 (1-26) 查看详细功能
  - 输入工具名称查看详细功能
  - 输入 'list' 重新显示工具列表
  - 输入 'q' 或 'quit' 退出

👉 请选择工具 > pandas

================================================================================
🔍 加载工具: pandas
================================================================================

⏳ 正在加载...
    已触发 task_tools.pandas_tool 模块加载

✅ 工具已成功加载
    类名: PandasTool
    模块: aiecs.tools.task_tools.pandas_tool

📋 原子功能列表 (共 41 个方法):
--------------------------------------------------------------------------------

  [1] apply(records: List, func: str, columns: List, axis: int = 0) -> List
      Apply a function to specified columns or rows.

  [2] astype(records: List, dtypes: Dict) -> List
      Convert column types in DataFrame.

  [3] concat(records_list: List, axis: int = 0) -> List
      Concatenate multiple DataFrames.

  ... (更多方法)

  [41] write_file(records: List, file_path: str, file_type: str = 'csv') -> Dict
      Write DataFrame to a file.

--------------------------------------------------------------------------------
```

### 2. 类型注解检查器 (`check_type_annotations.py`)

检查工具方法的类型注解完整性，确保所有方法都有完整的类型注解（参数类型 + 返回类型）。

**用途**：
- 验证新开发的工具是否有完整的类型注解
- 检查现有工具的类型注解覆盖率
- 为自动 Schema 生成提供基础保障

**命令**：
```bash
# 检查所有工具
aiecs-tools-check-annotations

# 检查特定工具
aiecs-tools-check-annotations pandas

# 检查多个工具
aiecs-tools-check-annotations pandas chart image

# 显示详细的改进建议
aiecs-tools-check-annotations pandas --verbose
```

**输出示例**：
```
====================================================================================================
工具类型注解检查器
====================================================================================================

✅ pandas: 38/38 方法有完整类型注解 (100.0%)

⚠️ my_tool: 5/10 方法有完整类型注解 (50.0%)

  需要改进的方法:
    ✗ process_data: 无类型注解
    ⚠ filter_records: 部分类型注解
      → 为参数 'condition' 添加类型注解
      → 添加返回类型注解

====================================================================================================
总体统计: 43/48 方法有完整类型注解 (89.6%)
====================================================================================================
```

### 3. Schema 质量验证器 (`validate_tool_schemas.py`)

验证自动生成的 Schema 质量，识别需要改进的文档字符串。

**用途**：
- 验证 Schema 自动生成是否成功
- 评估生成的 Schema 描述质量
- 指导开发者改进文档字符串

**命令**：
```bash
# 验证所有工具
aiecs-tools-validate-schemas

# 验证特定工具
aiecs-tools-validate-schemas pandas

# 显示详细的改进建议
aiecs-tools-validate-schemas pandas --verbose

# 显示示例 Schema
aiecs-tools-validate-schemas pandas --show-examples
```

**输出示例**：
```
====================================================================================================
工具 Schema 质量验证器
====================================================================================================

✅ chart
  方法数: 3
  成功生成 Schema: 3 (100.0%)
  描述质量: 100.0%
  综合评分: 100.0% (A (优秀))

❌ pandas
  方法数: 38
  成功生成 Schema: 38 (100.0%)
  描述质量: 0.0%
  综合评分: 66.7% (D (需改进))

  需要改进的方法 (38 个):

    filter:
      💡 在文档字符串的 Args 部分为参数 'records' 添加描述
      💡 在文档字符串的 Args 部分为参数 'condition' 添加描述

====================================================================================================
总体统计:
  方法数: 41
  Schema 生成率: 41/41 (100.0%)
  描述质量: 7.3%
====================================================================================================
```

## 🚀 工具开发工作流

### 新工具开发流程

1. **编写工具类**
   ```python
   from aiecs.tools.base_tool import BaseTool
   from typing import List, Dict
   
   class MyTool(BaseTool):
       """My custom tool"""
       
       def process(self, data: List[Dict], threshold: float = 0.5) -> Dict:
           """
           Process data with threshold.
           
           Args:
               data: Input data to process
               threshold: Processing threshold (0.0 to 1.0)
           
           Returns:
               Processing results
           """
           pass
   ```

2. **检查类型注解**
   ```bash
   aiecs-tools-check-annotations my_tool --verbose
   ```
   
   确保所有方法都有 ✅ 标记。

3. **验证 Schema 质量**
   ```bash
   aiecs-tools-validate-schemas my_tool --show-examples
   ```
   
   目标：综合评分 ≥ 80% (B 良好)

4. **改进文档字符串**
   
   根据验证器的建议，改进文档字符串：
   ```python
   def process(self, data: List[Dict], threshold: float = 0.5) -> Dict:
       """
       Process data with threshold filtering.
       
       Args:
           data: List of data records to process (each record is a dict)
           threshold: Minimum confidence threshold for filtering (0.0 to 1.0, default: 0.5)
       
       Returns:
           Dictionary containing processed results and statistics
       """
       pass
   ```

5. **重新验证**
   ```bash
   aiecs-tools-validate-schemas my_tool
   ```

### 现有工具维护流程

1. **定期检查**
   ```bash
   # 每次修改工具后运行
   aiecs-tools-check-annotations my_tool
   aiecs-tools-validate-schemas my_tool
   ```

2. **批量检查**
   ```bash
   # 检查所有工具
   aiecs-tools-check-annotations
   aiecs-tools-validate-schemas
   ```

3. **持续改进**
   - 优先改进评分 < 80% 的工具
   - 为通用描述（如 "Parameter xxx"）添加有意义的说明

## 📊 质量标准

### 类型注解标准

- ✅ **优秀 (100%)**：所有方法都有完整类型注解
- ⚠️ **良好 (80-99%)**：大部分方法有完整类型注解
- ❌ **需改进 (<80%)**：缺少大量类型注解

### Schema 质量标准

- ✅ **A (优秀) ≥90%**：Schema 生成成功，描述质量高
- ⚠️ **B (良好) 80-89%**：Schema 生成成功，描述质量中等
- ⚠️ **C (中等) 70-79%**：Schema 生成成功，描述质量较低
- ❌ **D (需改进) <70%**：Schema 生成失败或描述质量差

## 💡 最佳实践

### 1. 完整的类型注解

```python
# ✅ 好的示例
def filter(self, records: List[Dict], condition: str) -> List[Dict]:
    pass

# ❌ 不好的示例
def filter(self, records, condition):  # 缺少类型注解
    pass

def filter(self, records: List[Dict], condition):  # 部分缺失
    pass
```

### 2. 详细的文档字符串

使用 Google 或 NumPy 风格：

```python
# ✅ Google 风格（推荐）
def filter(self, records: List[Dict], condition: str) -> List[Dict]:
    """
    Filter DataFrame based on a condition.
    
    Args:
        records: List of records to filter (each record is a dict)
        condition: Filter condition using pandas query syntax (e.g., 'age > 30')
    
    Returns:
        Filtered list of records
    """
    pass

# ✅ NumPy 风格
def filter(self, records: List[Dict], condition: str) -> List[Dict]:
    """
    Filter DataFrame based on a condition.
    
    Parameters
    ----------
    records : List[Dict]
        List of records to filter (each record is a dict)
    condition : str
        Filter condition using pandas query syntax (e.g., 'age > 30')
    
    Returns
    -------
    List[Dict]
        Filtered list of records
    """
    pass
```

### 3. 有意义的描述

```python
# ❌ 不好的描述
"""
Args:
    records: Parameter records
    condition: Parameter condition
"""

# ✅ 好的描述
"""
Args:
    records: List of data records to filter (each record contains fields like 'name', 'age', etc.)
    condition: Filter condition using pandas query syntax (e.g., 'age > 30 and status == "active"')
"""
```

### 4. 处理复杂类型

```python
from typing import List, Dict, Optional, Union
import pandas as pd

# ✅ 使用标准类型
def process(self, data: List[Dict]) -> Dict:
    pass

# ✅ pandas 类型会自动映射为 Any
def process(self, df: pd.DataFrame) -> pd.DataFrame:
    pass

# ✅ 可选参数
def process(self, data: List[Dict], config: Optional[Dict] = None) -> Dict:
    pass
```

## 🔧 故障排查

### 问题：类型注解检查失败

**原因**：缺少类型注解或使用了不支持的类型

**解决**：
1. 为所有参数添加类型注解
2. 添加返回类型注解
3. 使用标准类型（List, Dict, str, int, float, bool 等）

### 问题：Schema 生成失败

**原因**：
- 方法没有参数（除了 self）→ 这是正常的，无需 Schema
- 类型注解不完整 → 运行类型注解检查器
- 使用了不支持的类型 → 会自动映射为 Any

### 问题：描述质量低

**原因**：文档字符串缺少 Args 部分或描述不详细

**解决**：
1. 添加文档字符串的 Args 部分
2. 为每个参数添加详细描述
3. 使用 Google 或 NumPy 风格

## 📚 相关文档

- [Schema Generator 技术文档](../../../docs/TOOLS/TOOLS_SCHEMA_GENERATOR.md)
- [LangChain Adapter 技术文档](../../../docs/TOOLS/TOOLS_LANGCHAIN_ADAPTER.md)
- [BaseTool 开发指南](../../../docs/TOOLS/TOOLS_BASE_TOOL.md)

## 🤝 贡献

如果你发现这些工具有改进空间，欢迎提交 PR 或 Issue！

---

**维护者**: AIECS Tools Team  
**最后更新**: 2025-10-02

