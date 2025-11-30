# ChartTool LangChain Agent Usage Guide

## Overview

ChartTool is a powerful data analysis and visualization tool that supports multiple data format reading, diverse chart creation, and flexible data export. Through the LangChain adapter, each feature of ChartTool is converted into independent tools for ReAct Agent invocation.

## Available Tools List

In LangChain ReAct Agent, ChartTool is converted into the following 3 independent tools:

1. **`chart_read_data`** - Data reading and analysis
2. **`chart_visualize`** - Data visualization chart creation  
3. **`chart_export_data`** - Data format conversion and export

---

## 1. chart_read_data

### Function Description
Read data files in various formats, perform basic analysis, and return data summary information.

### Supported File Formats
- **CSV** (`.csv`)
- **Excel** (`.xlsx`, `.xls`) 
- **JSON** (`.json`)
- **Parquet** (`.parquet`)
- **Feather** (`.feather`)
- **SPSS** (`.sav`)
- **SAS** (`.sas7bdat`)
- **Stata** (`.por`)

### LangChain Invocation Method

```python
# Basic invocation
result = agent_executor.invoke({
    "input": "Use chart_read_data to read file /path/to/data.csv"
})

# Complete parameter invocation
result = agent_executor.invoke({
    "input": """Use chart_read_data tool with the following parameters:
    file_path: /path/to/data.xlsx
    nrows: 1000
    sheet_name: Sheet1
    export_format: json
    export_path: /tmp/analysis_results.json
    """
})
```

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | str | ✅ | Complete path to the data file |
| `nrows` | int | ❌ | Limit the number of rows to read (default: read all) |
| `sheet_name` | str/int | ❌ | Excel worksheet name or index (default: 0) |
| `export_format` | str | ❌ | Export format: json/csv/html/excel/markdown |
| `export_path` | str | ❌ | Export file save path |

### Use Cases
- 🔍 **Data Exploration**: Quickly understand the structure and basic information of data files
- 📊 **Data Overview**: View data types, row count, column names, and other metadata
- 🔄 **Format Conversion**: Read data and convert to other formats
- 📋 **Data Preview**: View the first few rows of data

### Return Result

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
    "exported_to": "/tmp/analysis_results.json"  // If export was specified
}
```

### Agent Invocation Example

```
Human: I want to analyze this sales data file /data/sales.csv to see how many rows of data it contains

Agent: I'll help you analyze the sales data file.

Action: chart_read_data
Action Input: {"file_path": "/data/sales.csv"}

Observation: {
    "variables": ["date", "product", "sales", "region"],
    "observations": 5000,
    "dtypes": {"date": "object", "product": "object", "sales": "int64", "region": "object"},
    "memory_usage": 0.15,
    "preview": [...]
}

Thought: Data successfully read, containing 5000 records with 4 columns: date, product, sales, and region.

Final Answer: Your sales data file contains 5000 records with 4 fields: date, product, sales, and region. The data size is approximately 0.15MB.
```

---

## 2. chart_visualize

### Function Description
Create various types of visualization charts based on data files, supporting multiple chart styles and custom configurations.

### Supported Chart Types

| Chart Type | Value | Use Case |
|-----------|-------|----------|
| Histogram | `histogram` | Single variable distribution analysis |
| Box Plot | `boxplot` | Distribution comparison, outlier detection |
| Scatter Plot | `scatter` | Two-variable relationship analysis |
| Bar Chart | `bar` | Categorical data comparison |
| Line Chart | `line` | Time series,
| Heatmap | `heatmap` | Correlation matrix visualization |
| Pair Plot | `pair` | Multi-variable relationship matrix |

### LangChain Invocation Method

```python
# Basic visualization
result = agent_executor.invoke({
    "input": """Use chart_visualize to create a scatter plot:
    file_path: /data/sales.csv
    plot_type: scatter
    x: price
    y: sales
    title: Price vs Sales Relationship Chart
    """
})

# Advanced visualization configuration
result = agent_executor.invoke({
    "input": """Use chart_visualize tool:
    file_path: /data/multi_vars.csv
    plot_type: heatmap
    variables: ["var1", "var2", "var3", "var4"]
    title: Variable Correlation Analysis
    figsize: [12, 8]
    output_path: /charts/correlation_heatmap.png
    dpi: 300
    """
})
```

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | str | ✅ | Data file path |
| `plot_type` | str | ✅ | Chart type (see supported chart types table) |
| `x` | str | ❌ | Column name for X-axis |
| `y` | str | ❌ | Column name for Y-axis |
| `hue` | str | ❌ | Column name for color encoding |
| `variables` | List[str] | ❌ | List of variables to include in visualization |
| `title` | str | ❌ | Chart title |
| `figsize` | List[int] | ❌ | Chart size [width, height] |
| `output_path` | str | ❌ | Chart save path |
| `dpi` | int | ❌ | Image resolution (default: 100) |
| `export_format` | str | ❌ | Export format: json/csv/html/excel/markdown |
| `export_path` | str | ❌ | Export result save path |

### Use Cases

#### 📈 **Trend Analysis**
```
plot_type: line
x: date  
y: sales
Use case: Time series analysis, trend observation
```

#### 📊 **Distribution Analysis**  
```
plot_type: histogram
x: age
Use case: Single variable distribution shape analysis
```

#### 🔗 **Relationship Analysis**
```
plot_type: scatter  
x: advertising_spend
y: revenue
hue: channel
Use case: Explore relationships and correlations between variables
```

#### 🔥 **Correlation Analysis**
```
plot_type: heatmap
variables: ["var1", "var2", "var3"]  
Use case: Multi-variable correlation matrix visualization
```

#### 📦 **Categorical Comparison**
```
plot_type: boxplot
x: department
y: salary
Use case: Distribution comparison across different groups
```

### Return Result

```json
{
    "plot_type": "scatter",
    "output_path": "/tmp/chart_exports/plot_a1b2c3d4.png",
    "variables": ["price", "sales", "region"],
    "title": "Price vs Sales Relationship Chart",
    "exported_to": "/charts/analysis_results.json"  // If export was specified
}
```

### Agent Invocation Example

```
Human: Help me create a chart showing sales performance by different regions using sales data

Agent: I'll create a visualization chart showing sales performance by different regions for you.

Action: chart_visualize
Action Input: {
    "file_path": "/data/sales.csv",
    "plot_type": "bar", 
    "x": "region",
    "y": "sales",
    "title": "Sales Performance Comparison by Region",
    "figsize": [12, 6]
}

Observation: {
    "plot_type": "bar",
    "output_path": "/tmp/chart_exports/plot_xy123.png", 
    "variables": ["region", "sales"],
    "title": "Sales Performance Comparison by Region"
}

Thought: Chart successfully created, showing sales performance comparison by different regions.

Final Answer: I've created a bar chart showing sales performance comparison by different regions. The chart has been saved to /tmp/chart_exports/plot_xy123.png. This chart clearly shows the sales data differences across regions.
```

---

## 3. chart_export_data

### Function Description
Convert and export data files to different formats, supporting variable selection and format customization.

### Supported Export Formats

| Format | Value | Description | Use Case |
|--------|-------|-------------|----------|
| JSON | `json` | Structured data format | API interaction, data exchange |
| CSV | `csv` | Comma-separated values format | Excel compatibility, simple analysis |
| HTML | `html` | Web table format | Report display, web integration |
| Excel | `excel` | Excel workbook format | Office software compatibility |
| Markdown | `markdown` | Markdown table format | Documentation writing, GitHub display |

### LangChain Invocation Method

```python
# Basic export
result = agent_executor.invoke({
    "input": """Use chart_export_data to export data:
    file_path: /data/sales.csv
    format: excel
    export_path: /exports/sales_data.xlsx
    """
})

# Selective export of specific variables
result = agent_executor.invoke({
    "input": """Use chart_export_data tool:
    file_path: /data/large_dataset.csv
    format: json
    variables: ["id", "name", "score"]
    export_path: /exports/filtered_data.json
    """
})
```

### Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | str | ✅ | Source data file path |
| `format` | str | ✅ | Export format (json/csv/html/excel/markdown) |
| `variables` | List[str] | ❌ | List of column names to export (if not specified, exports all columns) |
| `export_path` | str | ❌ | Export file save path (if not specified, auto-generated) |
| `export_format` | str | ❌ | Result metadata export format |

### Use Cases

#### 📄 **Format Conversion**
```
Source file: data.xlsx → Target format: CSV
Use case: Data migration between different systems
```

#### 🎯 **Selective Data Export**
```
variables: ["name", "score", "grade"]
Use case: Extract specific fields for subsequent analysis
```

#### 📊 **Report Generation**  
```
format: html or markdown
Use case: Create readable data reports
```

#### 💾 **Data Backup**
```
format: excel or json
Use case: Data archiving and long-term storage
```

### Return Result

```json
{
    "format": "excel",
    "path": "/exports/sales_data.xlsx", 
    "rows": 5000,
    "columns": 4,
    "variables": ["date", "product", "sales", "region"],
    "exported_to": "/metadata/export_summary.json"  // If metadata export was specified
}
```

### Agent Invocation Example

```
Human: Convert sales data to Excel format, keeping only product name and sales columns

Agent: I'll help you convert the sales data to Excel format with only the two columns you specified.

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

Thought: Data successfully converted to Excel format with only product name and sales columns.

Final Answer: Data conversion complete! I've converted the sales data to Excel format, saved to /exports/product_sales.xlsx. The exported data contains 5000 records with only the two columns you requested: product name and sales.
```

---

## Complete Workflow Example

### Scenario: Complete Data Analysis Workflow

```
Human: I have a customer data file customer_data.csv, please help me analyze the data structure, create an age distribution chart, and export the results as a report

Agent: I'll help you complete this complete data analysis workflow.

Action: chart_read_data
Action Input: {"file_path": "/data/customer_data.csv"}

Observation: {
    "variables": ["customer_id", "age", "income", "city"],
    "observations": 2500,
    "dtypes": {"customer_id": "int64", "age": "int64", "income": "float64", "city": "object"},
    "preview": [...]
}

Thought: Data structure analysis complete, now creating age distribution histogram.

Action: chart_visualize
Action Input: {
    "file_path": "/data/customer_data.csv",
    "plot_type": "histogram", 
    "x": "age",
    "title": "Customer Age Distribution Chart",
    "output_path": "/reports/age_distribution.png"
}

Observation: {
    "plot_type": "histogram",
    "output_path": "/reports/age_distribution.png",
    "variables": ["age"],
    "title": "Customer Age Distribution Chart"  
}

Thought: Age distribution chart created, now exporting analysis results as HTML report.

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

Thought: Complete analysis workflow finished.

Final Answer: Analysis complete! Your customer data contains 2500 records with 4 fields. I have:
1. Analyzed the data structure and basic information
2. Created an age distribution histogram (saved to /reports/age_distribution.png)  
3. Exported a complete HTML data report (saved to /reports/customer_analysis.html)

The data shows customer age, income, and city distribution, which can be used for further business analysis.
```

---

## Advanced Usage Tips

### 1. Batch Analysis of Multiple Files
```python
# Analyze multiple files sequentially
files = ["/data/q1.csv", "/data/q2.csv", "/data/q3.csv"] 
for file in files:
    agent.invoke(f"Use chart_read_data to analyze file {file}")
```

### 2. Create Comparison Charts
```python
# Multi-variable comparison visualization
agent.invoke("""
Use chart_visualize to create a comparison chart:
file_path: /data/performance.csv
plot_type: bar
x: team  
y: score
hue: quarter
title: Team Performance Comparison by Quarter
""")
```

### 3. Correlation Analysis
```python  
# Create correlation heatmap
agent.invoke("""
Use chart_visualize for correlation analysis:
file_path: /data/features.csv
plot_type: heatmap
variables: ["feature1", "feature2", "feature3", "target"]
title: Feature Correlation Matrix
""")
```

### 4. Custom Output Configuration
```python
# High-resolution chart export
agent.invoke("""
Use chart_visualize to create a high-quality chart:
file_path: /data/data.csv
plot_type: line
x: month
y: revenue  
title: Monthly Revenue Trend
figsize: [16, 10]
dpi: 300
output_path: /reports/high_res_chart.png
""")
```

---

## Error Handling

### Common Errors and Solutions

| Error Type | Cause | Solution |
|-----------|-------|----------|
| `File not found` | File path does not exist | Check if the file path is correct |
| `Variables not found in dataset` | Specified column names do not exist | First use read_data to view available column names |
| `Extension not allowed` | Unsupported file format | Check the supported formats list |
| `Error creating visualization` | Chart creation failed | Check data types and parameter combinations |

### Best Practices

1. **📋 Read Data First**: Use `chart_read_data` to understand data structure
2. **🎯 Clarify Objectives**: Choose appropriate chart type based on analysis purpose  
3. **🔍 Verify Column Names**: Ensure specified column names exist in the data
4. **📐 Reasonable Configuration**: Adjust chart size and resolution based on data characteristics
5. **💾 Plan Paths**: Organize output file directory structure reasonably

---

## Configuration Options

ChartTool supports the following configuration options (set during tool initialization):

```python
config = {
    "export_dir": "/custom/export/path",     # Custom export directory
    "plot_dpi": 150,                        # Default chart resolution  
    "plot_figsize": [12, 8],                # Default chart size
    "allowed_extensions": [".csv", ".xlsx"] # Limit allowed file formats
}
```

---

## Performance Optimization Recommendations

1. **🚀 Large Dataset Processing**: Use `nrows` parameter to limit rows for sampling analysis
2. **💾 Memory Optimization**: Release memory promptly after processing large datasets to avoid memory usage
3. **📁 File Organization**: Plan export directories reasonably to avoid file clutter
4. **🎨 Chart Optimization**: Choose appropriate DPI and size based on usage
5. **🔄 Cache Utilization**: Repeated reads of the same file will use cache to improve performance

---

## Summary

ChartTool provides complete data analysis workflow support through the LangChain adapter:

- ✅ **Data Reading**: Supports 9 file formats with flexible reading options
- ✅ **Visualization Creation**: 7 chart types with rich customization options  
- ✅ **Data Export**: 5 export formats to meet different usage needs
- ✅ **Error Handling**: Complete input validation and exception handling
- ✅ **Performance Optimization**: Built-in cache, performance monitoring, and security checks

Through these tools, LangChain ReAct Agent can execute complete data science workflows from data reading, analysis, visualization to result export, providing users with powerful data analysis capabilities.
