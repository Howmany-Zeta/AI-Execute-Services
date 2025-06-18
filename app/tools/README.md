# Tools Architecture

本目录包含为应用程序提供各种功能的工具。工具架构已经重构，将业务逻辑与性能优化关注点分离。

## 新架构

新架构包含以下组件：

1. **工具执行器** (`app/core/tool_executor.py`): 一个集中式执行框架，处理以下横切关注点：
   - 输入验证
   - 缓存
   - 并发
   - 错误处理
   - 性能优化
   - 日志记录

2. **基础工具类** (`app/tools/base_tool.py`): 所有工具都应继承的基类，提供：
   - 与工具执行器的集成
   - 基于模式的输入验证
   - 标准化错误处理
   - 自动模式发现

3. **工具注册表** (`app/tools/__init__.py`): 处理工具的注册和检索：
   - 工具注册
   - 工具检索
   - 工具发现

## 使用基础工具类

要创建新工具，继承 `BaseTool` 类并实现您的业务逻辑方法：

```python
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.tools import register_tool
from app.tools.base_tool import BaseTool

@register_tool("my_tool")
class MyTool(BaseTool):
    """我的工具描述"""
    
    # 为操作定义输入模式
    class OperationSchema(BaseModel):
        """操作的模式"""
        param1: str = Field(description="参数1")
        param2: int = Field(description="参数2")
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化工具"""
        super().__init__(config)
        # 额外的初始化
    
    def operation(self, param1: str, param2: int) -> Dict[str, Any]:
        """
        在这里实现您的业务逻辑
        
        Args:
            param1: 参数1
            param2: 参数2
            
        Returns:
            操作结果
        """
        # 您的业务逻辑
        return {"result": f"处理 {param1} 和 {param2}"}
```

## 使用装饰器进行性能优化

工具执行器提供了几个装饰器，您可以用它们为方法添加性能优化：

```python
from app.core.tool_executor import cache_result, run_in_executor, measure_execution_time

@cache_result()  # 缓存此方法的结果
def cached_operation(self, param1: str) -> Dict[str, Any]:
    # 此结果将基于param1进行缓存
    return {"result": f"缓存的结果 {param1}"}

@run_in_executor  # 在线程池中运行此方法
def cpu_intensive_operation(self, param1: str) -> Dict[str, Any]:
    # 此方法将在单独的线程中执行
    return {"result": f"CPU密集型结果 {param1}"}

@measure_execution_time  # 记录此方法的执行时间
def monitored_operation(self, param1: str) -> Dict[str, Any]:
    # 此方法的执行时间将被记录
    return {"result": f"监控的结果 {param1}"}
```

## 迁移现有工具

要将现有工具迁移到新架构：

1. 使您的工具类继承 `BaseTool`
2. 为您的操作定义 Pydantic 模式
3. 删除任何自定义缓存、验证或错误处理代码
4. 使用装饰器进行性能优化
5. 更新 `run` 方法以使用基类实现

### 之前：

```python
@register_tool("example")
class ExampleTool:
    def __init__(self):
        self._cache = {}
    
    def run(self, op: str, **kwargs):
        if op == "operation":
            return self.operation(**kwargs)
        else:
            raise ValueError(f"不支持的操作: {op}")
    
    def operation(self, param1: str, param2: int):
        # 自定义缓存
        cache_key = f"{param1}_{param2}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 自定义验证
        if not isinstance(param1, str):
            raise ValueError("param1必须是字符串")
        if not isinstance(param2, int):
            raise ValueError("param2必须是整数")
        
        # 业务逻辑
        result = {"result": f"处理 {param1} 和 {param2}"}
        
        # 缓存结果
        self._cache[cache_key] = result
        
        return result
```

### 之后：

```python
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.tools import register_tool
from app.tools.base_tool import BaseTool
from app.core.tool_executor import cache_result

@register_tool("example")
class ExampleTool(BaseTool):
    """示例工具"""
    
    class OperationSchema(BaseModel):
        """操作的模式"""
        param1: str = Field(description="参数1")
        param2: int = Field(description="参数2")
    
    @cache_result()
    def operation(self, param1: str, param2: int) -> Dict[str, Any]:
        """
        处理参数
        
        Args:
            param1: 参数1
            param2: 参数2
            
        Returns:
            操作结果
        """
        # 只关注业务逻辑
        return {"result": f"处理 {param1} 和 {param2}"}
```

## 新架构的好处

新架构提供了几个好处：

1. **关注点分离**：业务逻辑与缓存、验证和错误处理等横切关注点分离。

2. **减少重复**：常见功能在工具执行器和基础工具中实现一次，而不是在各个工具中重复。

3. **行为一致**：所有工具在验证、错误处理和性能优化方面表现一致。

4. **提高可维护性**：工具更容易维护，因为它们只关注特定的业务逻辑。

5. **增强性能**：工具执行器提供缓存、并发和其他性能特性的优化实现。

6. **更好的测试**：业务逻辑可以独立于横切关注点进行测试。

7. **更容易上手**：新开发人员可以专注于实现业务逻辑，而不必担心性能优化的细节。

## 使用示例

```python
# 获取工具实例
from app.tools import get_tool

# 获取图表工具
chart_tool = get_tool("chart")

# 使用工具
result = chart_tool.run("visualize", 
    file_path="data.csv",
    plot_type="histogram",
    x="age",
    title="年龄分布"
)

# 或直接调用方法
result = chart_tool.visualize(
    file_path="data.csv",
    plot_type="histogram",
    x="age",
    title="年龄分布"
)