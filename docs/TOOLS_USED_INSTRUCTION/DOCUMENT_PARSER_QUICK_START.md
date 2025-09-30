# 文档解析工具 - 快速开始指南

## 🚀 开箱即用状态

现在文档解析组件已经完全可以开箱即用！开发者可以直接在项目中使用这些工具。

## 📁 新的目录结构

```
aiecs/tools/
├── docs/                          # 文档处理工具专用目录 
│   ├── __init__.py                # 文档工具模块初始化
│   ├── document_parser_tool.py    # 核心文档解析工具
│   └── ai_document_orchestrator.py # AI智能编排器
├── task_tools/                    # 其他任务工具
│   ├── chart_tool.py
│   ├── scraper_tool.py
│   └── ...
└── __init__.py                    # 主工具注册
```

## 🔧 安装和配置

### 1. 基础安装
```bash
# 项目已包含所有必要依赖
pip install -e .

# 或者从PyPI安装
pip install aiecs
```

### 2. 环境变量配置（可选）
```bash
# 文档解析器配置
export DOC_PARSER_enable_cloud_storage=true
export DOC_PARSER_gcs_bucket_name=your-bucket-name
export DOC_PARSER_gcs_project_id=your-project-id

# AI编排器配置
export AI_DOC_ORCHESTRATOR_default_ai_provider=openai
export AI_DOC_ORCHESTRATOR_max_chunk_size=4000
```

## 💻 基础使用

### 1. 导入工具（新路径）
```python
# 从docs目录导入文档处理工具
from aiecs.tools.docs.document_parser_tool import DocumentParserTool
from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator

# 或者使用懒加载方式
from aiecs.tools.docs import document_parser_tool, ai_document_orchestrator
```

### 2. 快速开始示例
```python
#!/usr/bin/env python3
"""
文档处理快速开始示例
"""

def quick_start_example():
    # 1. 初始化工具
    from aiecs.tools.docs.document_parser_tool import DocumentParserTool
    from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator
    
    parser = DocumentParserTool()
    orchestrator = AIDocumentOrchestrator()
    
    # 2. 处理本地文档
    result = orchestrator.process_document(
        source="test_document.txt",
        processing_mode="summarize"
    )
    
    print("AI摘要:", result['ai_result']['ai_response'])

if __name__ == "__main__":
    quick_start_example()
```

### 3. 支持的文档源
```python
# 支持多种文档源
sources = [
    "/path/to/local/file.pdf",                    # 本地文件
    "https://example.com/document.pdf",           # URL链接
    "gs://bucket/document.pdf",                   # Google Cloud Storage
    "s3://bucket/document.pdf",                   # AWS S3
    "azure://container/document.pdf",             # Azure Blob
    "doc_123456789",                              # 存储ID
]

for source in sources:
    try:
        result = parser.parse_document(source=source)
        print(f"✓ 成功解析: {source}")
    except Exception as e:
        print(f"✗ 解析失败: {source} - {e}")
```

## 🌐 云存储配置

### Google Cloud Storage
```python
config = {
    "enable_cloud_storage": True,
    "gcs_bucket_name": "my-documents",
    "gcs_project_id": "my-project-id"
}

parser = DocumentParserTool(config)
```

### 处理云存储文档
```python
# 直接处理云存储中的文档
cloud_doc = "gs://my-bucket/reports/annual_report.pdf"

result = orchestrator.process_document(
    source=cloud_doc,
    processing_mode="extract_info",
    processing_params={
        "extraction_criteria": "财务数据、关键指标、结论"
    }
)
```

## 🎯 实际应用示例

### 1. 批量处理文档
```python
def batch_process_documents():
    orchestrator = AIDocumentOrchestrator()
    
    documents = [
        "gs://docs/report1.pdf",
        "gs://docs/report2.pdf", 
        "s3://legal/contract.docx"
    ]
    
    result = orchestrator.batch_process_documents(
        sources=documents,
        processing_mode="analyze",
        max_concurrent=3
    )
    
    print(f"成功处理: {result['successful_documents']}")
    return result

# 运行批量处理
batch_result = batch_process_documents()
```

### 2. 自定义AI分析
```python
def custom_document_analysis():
    orchestrator = AIDocumentOrchestrator()
    
    # 创建自定义分析器
    legal_analyzer = orchestrator.create_custom_processor(
        system_prompt="你是一个专业的法律文档分析师",
        user_prompt_template="分析以下法律文档并提取关键条款：{content}"
    )
    
    # 使用自定义分析器
    result = legal_analyzer("contract.pdf")
    return result

# 运行自定义分析
analysis_result = custom_document_analysis()
```

### 3. 实时文档处理
```python
async def realtime_document_processing():
    orchestrator = AIDocumentOrchestrator()
    
    # 异步处理多个文档
    tasks = [
        orchestrator.process_document_async(
            source=doc,
            processing_mode="summarize"
        )
        for doc in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    ]
    
    results = await asyncio.gather(*tasks)
    return results

# 运行异步处理
import asyncio
async_results = asyncio.run(realtime_document_processing())
```

## 🔍 故障排除

### 常见问题和解决方案

#### 1. 导入错误
```python
# 错误的旧路径
# from aiecs.tools.task_tools.document_parser_tool import DocumentParserTool

# 正确的新路径
from aiecs.tools.docs.document_parser_tool import DocumentParserTool
```

#### 2. 权限问题
```bash
# 如果遇到临时文件权限问题
export TMPDIR=/tmp/aiecs_temp
mkdir -p $TMPDIR
chmod 755 $TMPDIR
```

#### 3. 云存储配置
```python
# 确保云存储配置正确
config = {
    "enable_cloud_storage": True,
    "gcs_bucket_name": "your-bucket",
    "gcs_project_id": "your-project"
}

# 测试配置
parser = DocumentParserTool(config)
print("云存储配置:", parser.settings.enable_cloud_storage)
```

## 📊 功能检查清单

运行以下代码检查所有功能是否正常：

```python
def system_check():
    """系统功能检查"""
    
    print("🔍 AIECS文档处理系统检查")
    print("=" * 40)
    
    # 1. 导入测试
    try:
        from aiecs.tools.docs.document_parser_tool import DocumentParserTool
        from aiecs.tools.docs.ai_document_orchestrator import AIDocumentOrchestrator
        print("✓ 模块导入成功")
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        return
    
    # 2. 初始化测试
    try:
        parser = DocumentParserTool()
        orchestrator = AIDocumentOrchestrator()
        print("✓ 工具初始化成功")
    except Exception as e:
        print(f"✗ 工具初始化失败: {e}")
        return
    
    # 3. 配置测试
    print(f"✓ 云存储支持: {parser.settings.enable_cloud_storage}")
    print(f"✓ 临时目录: {parser.settings.temp_dir}")
    print(f"✓ AI提供商: {orchestrator.settings.default_ai_provider}")
    
    # 4. 功能测试
    test_sources = [
        ("本地路径", "/tmp/test.txt"),
        ("HTTP URL", "https://example.com/file.pdf"),
        ("云存储", "gs://bucket/file.pdf"),
        ("存储ID", "doc_123456")
    ]
    
    for name, source in test_sources:
        is_supported = (
            not parser._is_url(source) or
            parser._is_cloud_storage_path(source) or
            parser._is_storage_id(source)
        )
        status = "✓" if is_supported else "✗"
        print(f"{status} {name}支持: {source}")
    
    print("\n🎉 系统检查完成!")

# 运行系统检查
system_check()
```

## 🚀 生产部署建议

### 1. 性能配置
```python
# 生产环境推荐配置
production_config = {
    "max_file_size": 100 * 1024 * 1024,  # 100MB
    "timeout": 120,                       # 2分钟超时
    "max_concurrent_requests": 10,        # 并发请求限制
    "enable_cloud_storage": True,         # 启用云存储
    "max_chunk_size": 8000               # AI处理块大小
}
```

### 2. 错误处理
```python
def robust_document_processing(source):
    """健壮的文档处理"""
    try:
        orchestrator = AIDocumentOrchestrator()
        result = orchestrator.process_document(
            source=source,
            processing_mode="summarize"
        )
        return {"status": "success", "result": result}
    
    except Exception as e:
        logger.error(f"文档处理失败: {source} - {e}")
        return {"status": "error", "error": str(e)}
```

### 3. 监控和日志
```python
import logging

# 配置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 启用特定模块的调试日志
logging.getLogger('aiecs.tools.docs').setLevel(logging.DEBUG)
```

## 📚 更多资源

- 完整API文档: `docs/TOOLS_USED_INSTRUCTION/DOCUMENT_PARSER_TOOL.md`
- 示例代码: `examples/document_processing_example.py`
- 云存储示例: `examples/cloud_storage_document_example.py`
- 工具架构说明: `docs/TOOLS_USED_INSTRUCTION/TOOL_SPECIAL_SPECIAL_INSTRUCTIONS.md`

## 🎯 总结

文档解析组件现在已经：

✅ **开箱即用** - 可直接在项目中使用  
✅ **结构清晰** - 文档工具独立在`docs`目录  
✅ **功能完整** - 支持多种文档源和AI处理模式  
✅ **高性能** - 异步处理、智能缓存、并发控制  
✅ **易扩展** - 支持自定义处理流程和AI提供商  

开发者现在可以直接使用这套现代化的文档解析组件来构建自己的AI文档处理应用！
