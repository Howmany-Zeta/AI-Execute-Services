# ChartTool Langchain Agent使用指南

## 概述

ChartTool是一个功能强大的数据分析和可视化工具，支持多种数据格式读取、多样化图表创建和灵活的数据导出。通过Langchain适配器，ChartTool的每个功能都被转换为独立的工具，供ReAct Agent调用。

## 可用工具列表

在Langchain ReAct Agent中，ChartTool被转换为以下3个独立工具：

1. **`chart_read_data`** - 数据读取和分析
2. **`chart_visualize`** - 数据可视化图表创建  
3. **`chart_export_data`** - 数据格式转换和导出

---

## 1. chart_read_data

### 功能描述
读取各种格式的数据文件，进行基础分析并返回数据摘要信息。

### 支持的文件格式
- **CSV** (`.csv`)
- **Excel** (`.xlsx`, `.xls`) 
- **JSON** (`.json`)
- **Parquet** (`.parquet`)
- **Feather** (`.feather`)
- **SPSS** (`.sav`)
- **SAS** (`.sas7bdat`)
- **Stata** (`.por`)

### Langchain调用方式

```python
# 基础调用
result = agent_executor.invoke({
    "input": "使用chart_read_data读取文件 /path/to/data.csv"
})

# 完整参数调用
result = agent_executor.invoke({
    "input": """使用chart_read_data工具，参数如下：
    file_path: /path/to/data.xlsx
    nrows: 1000
    sheet_name: Sheet1
    export_format: json
    export_path: /tmp/analysis_results.json
    """
})
```

### 输入参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `file_path` | str | ✅ | 数据文件的完整路径 |
| `nrows` | int | ❌ | 限制读取的行数（默认读取全部） |
| `sheet_name` | str/int | ❌ | Excel文件的工作表名或索引（默认0） |
| `export_format` | str | ❌ | 导出格式：json/csv/html/excel/markdown |
| `export_path` | str | ❌ | 导出文件保存路径 |

### 使用场景
- 🔍 **数据探索**：快速了解数据文件的结构和基本信息
- 📊 **数据概览**：查看数据类型、行数、列名等元信息
- 🔄 **格式转换**：将数据读取并转换为其他格式
- 📋 **数据预览**：查看数据的前几行内容

### 返回结果

```json
{
    "variables": ["column1", "column2", "column3"],
    "observations": 1000,
    "dtypes": {
        "column1": "object",
        "column2": "int64", 
        "column3": "float64"
    },
    "memory_usage": 0.25,
    "preview": [
        {"column1": "value1", "column2": 123, "column3": 45.67},
        {"column1": "value2", "column2": 456, "column3": 78.90}
    ],
    "exported_to": "/tmp/analysis_results.json"  // 如果指定了导出
}
```

### Agent调用示例

```
Human: 我想分析这个销售数据文件 /data/sales.csv，看看有多少行数据

Agent: 我来帮你分析销售数据文件。

Action: chart_read_data
Action Input: {"file_path": "/data/sales.csv"}

Observation: {
    "variables": ["date", "product", "sales", "region"],
    "observations": 5000,
    "dtypes": {"date": "object", "product": "object", "sales": "int64", "region": "object"},
    "memory_usage": 0.15,
    "preview": [...]
}

Thought: 数据已成功读取，包含5000行记录，有4个列：日期、产品、销售额和区域。

Final Answer: 你的销售数据文件包含5000行记录，有4个字段：date（日期）、product（产品）、sales（销售额）和region（区域）。数据大小约0.15MB。
```

---

## 2. chart_visualize

### 功能描述
基于数据文件创建各种类型的可视化图表，支持多种图表样式和自定义配置。

### 支持的图表类型

| 图表类型 | 值 | 适用场景 |
|---------|---|---------|
| 直方图 | `histogram` | 单变量分布分析 |
| 箱线图 | `boxplot` | 分布比较、异常值检测 |
| 散点图 | `scatter` | 两变量关系分析 |
| 柱状图 | `bar` | 分类数据比较 |
| 折线图 | `line` | 时间序列、趋势分析 |
| 热力图 | `heatmap` | 相关性矩阵可视化 |
| 配对图 | `pair` | 多变量关系矩阵 |

### Langchain调用方式

```python
# 基础可视化
result = agent_executor.invoke({
    "input": """使用chart_visualize创建散点图：
    file_path: /data/sales.csv
    plot_type: scatter
    x: price
    y: sales
    title: 价格与销售量关系图
    """
})

# 高级可视化配置
result = agent_executor.invoke({
    "input": """使用chart_visualize工具：
    file_path: /data/multi_vars.csv
    plot_type: heatmap
    variables: ["var1", "var2", "var3", "var4"]
    title: 变量相关性分析
    figsize: [12, 8]
    output_path: /charts/correlation_heatmap.png
    dpi: 300
    """
})
```

### 输入参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `file_path` | str | ✅ | 数据文件路径 |
| `plot_type` | str | ✅ | 图表类型（见支持的图表类型表格） |
| `x` | str | ❌ | X轴使用的列名 |
| `y` | str | ❌ | Y轴使用的列名 |
| `hue` | str | ❌ | 颜色编码使用的列名 |
| `variables` | List[str] | ❌ | 包含在可视化中的变量列表 |
| `title` | str | ❌ | 图表标题 |
| `figsize` | List[int] | ❌ | 图表尺寸 [宽度, 高度] |
| `output_path` | str | ❌ | 图表保存路径 |
| `dpi` | int | ❌ | 图片分辨率（默认100） |
| `export_format` | str | ❌ | 导出格式：json/csv/html/excel/markdown |
| `export_path` | str | ❌ | 导出结果保存路径 |

### 使用场景

#### 📈 **趋势分析**
```
plot_type: line
x: date  
y: sales
适用：时间序列分析、趋势观察
```

#### 📊 **分布分析**  
```
plot_type: histogram
x: age
适用：单变量分布形态分析
```

#### 🔗 **关系分析**
```
plot_type: scatter  
x: advertising_spend
y: revenue
hue: channel
适用：探索变量间关系和相关性
```

#### 🔥 **相关性分析**
```
plot_type: heatmap
variables: ["var1", "var2", "var3"]  
适用：多变量相关性矩阵可视化
```

#### 📦 **分类比较**
```
plot_type: boxplot
x: department
y: salary
适用：不同组别的分布比较
```

### 返回结果

```json
{
    "plot_type": "scatter",
    "output_path": "/tmp/chart_exports/plot_a1b2c3d4.png",
    "variables": ["price", "sales", "region"],
    "title": "价格与销售量关系图",
    "exported_to": "/charts/analysis_results.json"  // 如果指定了导出
}
```

### Agent调用示例

```
Human: 帮我用销售数据创建一个显示不同区域销售表现的图表

Agent: 我来为你创建一个显示不同区域销售表现的可视化图表。

Action: chart_visualize
Action Input: {
    "file_path": "/data/sales.csv",
    "plot_type": "bar", 
    "x": "region",
    "y": "sales",
    "title": "不同区域销售表现对比",
    "figsize": [12, 6]
}

Observation: {
    "plot_type": "bar",
    "output_path": "/tmp/chart_exports/plot_xy123.png", 
    "variables": ["region", "sales"],
    "title": "不同区域销售表现对比"
}

Thought: 图表已成功创建，显示了不同区域的销售表现对比。

Final Answer: 我已为你创建了一个柱状图，展示不同区域的销售表现对比。图表已保存到 /tmp/chart_exports/plot_xy123.png。这个图表清楚地显示了各区域的销售数据差异。
```

---

## 3. chart_export_data

### 功能描述
将数据文件转换并导出为不同格式，支持变量选择和格式自定义。

### 支持的导出格式

| 格式 | 值 | 描述 | 适用场景 |
|------|---|------|---------|
| JSON | `json` | 结构化数据格式 | API交互、数据交换 |
| CSV | `csv` | 逗号分隔值格式 | Excel兼容、简单分析 |
| HTML | `html` | 网页表格格式 | 报告展示、网页集成 |
| Excel | `excel` | Excel工作簿格式 | 办公软件兼容 |
| Markdown | `markdown` | Markdown表格格式 | 文档编写、GitHub展示 |

### Langchain调用方式

```python
# 基础导出
result = agent_executor.invoke({
    "input": """使用chart_export_data导出数据：
    file_path: /data/sales.csv
    format: excel
    export_path: /exports/sales_data.xlsx
    """
})

# 选择性导出特定变量
result = agent_executor.invoke({
    "input": """使用chart_export_data工具：
    file_path: /data/large_dataset.csv
    format: json
    variables: ["id", "name", "score"]
    export_path: /exports/filtered_data.json
    """
})
```

### 输入参数

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `file_path` | str | ✅ | 源数据文件路径 |
| `format` | str | ✅ | 导出格式（json/csv/html/excel/markdown） |
| `variables` | List[str] | ❌ | 要导出的列名列表（不指定则导出所有列） |
| `export_path` | str | ❌ | 导出文件保存路径（不指定则自动生成） |
| `export_format` | str | ❌ | 结果元数据的导出格式 |

### 使用场景

#### 📄 **格式转换**
```
源文件：data.xlsx → 目标格式：CSV
适用：不同系统间数据迁移
```

#### 🎯 **数据筛选导出**
```
variables: ["name", "score", "grade"]
适用：提取特定字段用于后续分析
```

#### 📊 **报告生成**  
```
format: html 或 markdown
适用：创建可读性强的数据报告
```

#### 💾 **数据备份**
```
format: excel 或 json
适用：数据归档和长期存储
```

### 返回结果

```json
{
    "format": "excel",
    "path": "/exports/sales_data.xlsx", 
    "rows": 5000,
    "columns": 4,
    "variables": ["date", "product", "sales", "region"],
    "exported_to": "/metadata/export_summary.json"  // 如果指定了元数据导出
}
```

### Agent调用示例

```
Human: 把销售数据转换为Excel格式，只要产品名称和销售额两列

Agent: 我来帮你将销售数据转换为Excel格式，并只包含你指定的两列。

Action: chart_export_data  
Action Input: {
    "file_path": "/data/sales.csv",
    "format": "excel",
    "variables": ["product", "sales"],
    "export_path": "/exports/product_sales.xlsx"
}

Observation: {
    "format": "excel", 
    "path": "/exports/product_sales.xlsx",
    "rows": 5000,
    "columns": 2, 
    "variables": ["product", "sales"]
}

Thought: 数据已成功转换为Excel格式，只包含产品名称和销售额两列。

Final Answer: 数据转换完成！我已将销售数据转换为Excel格式，文件保存在 /exports/product_sales.xlsx。导出的数据包含5000行记录，只包含你要求的两列：产品名称和销售额。
```

---

## 完整工作流示例

### 场景：数据分析完整流程

```
Human: 我有一个客户数据文件customer_data.csv，请帮我分析数据结构，创建年龄分布图，并将结果导出为报告

Agent: 我来帮你完成这个完整的数据分析流程。

Action: chart_read_data
Action Input: {"file_path": "/data/customer_data.csv"}

Observation: {
    "variables": ["customer_id", "age", "income", "city"],
    "observations": 2500,
    "dtypes": {"customer_id": "int64", "age": "int64", "income": "float64", "city": "object"},
    "preview": [...]
}

Thought: 数据结构已分析完成，现在创建年龄分布直方图。

Action: chart_visualize
Action Input: {
    "file_path": "/data/customer_data.csv",
    "plot_type": "histogram", 
    "x": "age",
    "title": "客户年龄分布图",
    "output_path": "/reports/age_distribution.png"
}

Observation: {
    "plot_type": "histogram",
    "output_path": "/reports/age_distribution.png",
    "variables": ["age"],
    "title": "客户年龄分布图"  
}

Thought: 年龄分布图已创建，现在将分析结果导出为HTML报告。

Action: chart_export_data
Action Input: {
    "file_path": "/data/customer_data.csv", 
    "format": "html",
    "export_path": "/reports/customer_analysis.html"
}

Observation: {
    "format": "html",
    "path": "/reports/customer_analysis.html",
    "rows": 2500, 
    "columns": 4,
    "variables": ["customer_id", "age", "income", "city"]
}

Thought: 完整的分析流程已完成。

Final Answer: 分析完成！你的客户数据包含2500条记录，有4个字段。我已经：
1. 分析了数据结构和基本信息
2. 创建了年龄分布直方图（保存在 /reports/age_distribution.png）  
3. 导出了完整的HTML数据报告（保存在 /reports/customer_analysis.html）

数据显示客户年龄、收入和所在城市的分布情况，可以用于进一步的业务分析。
```

---

## 高级使用技巧

### 1. 批量分析多个文件
```python
# 依次分析多个文件
files = ["/data/q1.csv", "/data/q2.csv", "/data/q3.csv"] 
for file in files:
    agent.invoke(f"使用chart_read_data分析文件 {file}")
```

### 2. 创建对比图表
```python
# 多变量对比可视化
agent.invoke("""
使用chart_visualize创建对比图：
file_path: /data/performance.csv
plot_type: bar
x: team  
y: score
hue: quarter
title: 各团队季度表现对比
""")
```

### 3. 相关性分析
```python  
# 创建相关性热力图
agent.invoke("""
使用chart_visualize进行相关性分析：
file_path: /data/features.csv
plot_type: heatmap
variables: ["feature1", "feature2", "feature3", "target"]
title: 特征相关性矩阵
""")
```

### 4. 自定义输出配置
```python
# 高分辨率图表导出
agent.invoke("""
使用chart_visualize创建高质量图表：
file_path: /data/data.csv
plot_type: line
x: month
y: revenue  
title: 月度收入趋势
figsize: [16, 10]
dpi: 300
output_path: /reports/high_res_chart.png
""")
```

---

## 错误处理

### 常见错误及解决方案

| 错误类型 | 原因 | 解决方案 |
|---------|------|---------|
| `File not found` | 文件路径不存在 | 检查文件路径是否正确 |
| `Variables not found in dataset` | 指定的列名不存在 | 先用read_data查看可用列名 |
| `Extension not allowed` | 不支持的文件格式 | 查看支持的格式列表 |
| `Error creating visualization` | 图表创建失败 | 检查数据类型和参数组合 |

### 最佳实践

1. **📋 先读取数据**：使用`chart_read_data`了解数据结构
2. **🎯 明确目标**：根据分析目的选择合适的图表类型  
3. **🔍 验证列名**：确保指定的列名存在于数据中
4. **📐 合理配置**：根据数据特点调整图表尺寸和分辨率
5. **💾 规划路径**：合理组织输出文件的目录结构

---

## 配置选项

ChartTool支持以下配置项（在工具初始化时设置）：

```python
config = {
    "export_dir": "/custom/export/path",     # 自定义导出目录
    "plot_dpi": 150,                        # 默认图表分辨率  
    "plot_figsize": [12, 8],                # 默认图表尺寸
    "allowed_extensions": [".csv", ".xlsx"] # 限制允许的文件格式
}
```

---

## 性能优化建议

1. **🚀 大数据集处理**：使用`nrows`参数限制读取行数进行采样分析
2. **💾 内存优化**：处理完大数据集后及时释放，避免内存占用
3. **📁 文件组织**：合理规划导出目录，避免文件混乱
4. **🎨 图表优化**：根据用途选择合适的DPI和尺寸
5. **🔄 缓存利用**：相同文件的重复读取会利用缓存提升性能

---

## 总结

ChartTool通过Langchain适配器提供了完整的数据分析工作流支持：

- ✅ **数据读取**：支持9种文件格式，灵活的读取选项
- ✅ **可视化创建**：7种图表类型，丰富的自定义选项  
- ✅ **数据导出**：5种导出格式，满足不同使用需求
- ✅ **错误处理**：完善的输入验证和异常处理
- ✅ **性能优化**：内置缓存、性能监控和安全检查

通过这些工具，Langchain ReAct Agent能够执行从数据读取、分析、可视化到结果导出的完整数据科学工作流，为用户提供强大的数据分析能力。
