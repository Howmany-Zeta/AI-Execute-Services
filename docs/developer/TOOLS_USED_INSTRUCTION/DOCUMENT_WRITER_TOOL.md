# Document Writer Tool - 现代化高性能文档写入组件

## 概述

文档写入工具（Document Writer Tool）是一个现代化的标准高性能文档写入操作组件，能够跟进AI发出write file指令，对指定文档进行安全、可靠的写入操作和保存。该组件采用生产级的设计理念，确保数据完整性、原子性操作和企业级安全性。

## 🏗️ 组件架构

```
aiecs/tools/docs/
├── document_writer_tool.py              # 🔧 核心文档写入工具  
└── ai_document_writer_orchestrator.py   # 🤖 AI写入编排器
```

## 🎯 核心特性

### 1. 生产级写入操作
- **原子写入**：确保写入操作的原子性，避免部分写入
- **事务支持**：支持批量操作的事务性写入
- **自动备份**：写入前自动创建备份，支持快速回滚
- **版本控制**：自动版本管理，支持历史版本追踪

### 2. 多格式文档支持
- **文本格式**：TXT, JSON, CSV, XML, YAML, HTML, Markdown
- **Office格式**：PDF, DOCX, XLSX（通过扩展）
- **二进制格式**：支持任意二进制文件写入
- **自动转换**：智能内容格式转换和验证

### 3. 多种写入模式
- **CREATE**：创建新文件，如果存在则失败
- **OVERWRITE**：覆盖现有文件
- **APPEND**：追加到现有文件
- **UPDATE**：更新现有文件（智能合并）
- **BACKUP_WRITE**：备份后写入
- **VERSION_WRITE**：版本化写入

### 4. 企业级安全性
- **内容验证**：多级内容验证（基础、严格、企业级）
- **安全扫描**：检测恶意内容和安全威胁
- **权限检查**：写入权限验证和配额管理
- **审计日志**：完整的操作审计和追踪

### 5. AI智能写入
- **内容生成**：AI驱动的内容生成和增强
- **格式转换**：智能文档格式转换
- **模板处理**：模板化文档生成
- **批量操作**：支持大规模批量写入

## 📝 使用方法

### 1. 基础文档写入

```python
from aiecs.tools.docs.document_writer_tool import DocumentWriterTool

# 初始化写入器
writer = DocumentWriterTool()

# 基础文档写入
result = writer.write_document(
    target_path="/path/to/document.txt",
    content="这是要写入的内容",
    format="txt",
    mode="create",  # 创建新文件
    encoding="utf-8",
    validation_level="basic"
)

print(f"写入成功: {result['write_result']['path']}")
print(f"文件大小: {result['write_result']['size']} bytes")
```

### 2. 不同写入模式

```python
# 创建模式 - 文件必须不存在
result = writer.write_document(
    target_path="new_file.txt",
    content="新文件内容",
    format="txt",
    mode="create"
)

# 覆盖模式 - 直接覆盖现有文件
result = writer.write_document(
    target_path="existing_file.txt", 
    content="新内容",
    format="txt",
    mode="overwrite"
)

# 追加模式 - 在文件末尾追加内容
result = writer.write_document(
    target_path="log_file.txt",
    content="\n新的日志条目",
    format="txt", 
    mode="append"
)

# 备份写入模式 - 自动备份后写入
result = writer.write_document(
    target_path="important_file.txt",
    content="更新的内容",
    format="txt",
    mode="backup_write",
    backup_comment="重要更新"
)
```

### 3. 多格式文档写入

```python
# JSON格式写入
data = {"name": "张三", "age": 30, "city": "北京"}
result = writer.write_document(
    target_path="data.json",
    content=data,  # 自动转换为JSON
    format="json",
    mode="create"
)

# CSV格式写入
csv_data = [
    ["姓名", "年龄", "城市"],
    ["张三", "30", "北京"],
    ["李四", "25", "上海"]
]
result = writer.write_document(
    target_path="users.csv",
    content=csv_data,  # 自动转换为CSV
    format="csv",
    mode="create"
)

# HTML格式写入
html_content = {"title": "网页标题", "body": "网页内容"}
result = writer.write_document(
    target_path="page.html",
    content=html_content,  # 自动转换为HTML
    format="html",
    mode="create"
)
```

### 4. 云存储文档写入

```python
# 配置云存储
config = {
    "enable_cloud_storage": True,
    "gcs_bucket_name": "my-documents",
    "gcs_project_id": "my-project"
}

writer = DocumentWriterTool(config)

# 写入到云存储
result = writer.write_document(
    target_path="gs://my-bucket/reports/report.txt",
    content="云存储报告内容",
    format="txt",
    mode="create"
)

# 支持多种云存储格式
cloud_targets = [
    "gs://gcs-bucket/file.txt",      # Google Cloud Storage
    "s3://s3-bucket/file.txt",       # AWS S3
    "azure://container/file.txt"     # Azure Blob Storage
]
```

### 5. AI智能写入

```python
from aiecs.tools.docs.ai_document_writer_orchestrator import AIDocumentWriterOrchestrator

# 初始化AI写入编排器
orchestrator = AIDocumentWriterOrchestrator()

# AI生成内容写入
result = orchestrator.ai_write_document(
    target_path="ai_generated_report.md",
    content_requirements="创建一份关于AI技术发展的报告，包含现状、趋势和挑战",
    generation_mode="generate",
    document_format="markdown",
    write_strategy="immediate"
)

print(f"AI生成内容: {result['ai_result']['generated_content'][:200]}...")
```

### 6. 内容增强和重写

```python
# 增强现有文档
result = orchestrator.enhance_document(
    source_path="draft_article.txt",
    enhancement_goals="提高可读性，增加专业术语解释，优化结构",
    target_path="enhanced_article.txt",
    preserve_format=True
)

# 格式转换
result = orchestrator.ai_write_document(
    target_path="converted_document.html",
    content_requirements="将markdown文档转换为HTML格式",
    generation_mode="convert_format",
    generation_params={
        "source_format": "markdown",
        "target_format": "html",
        "content": "# 标题\n\n这是markdown内容"
    }
)
```

### 7. 批量写入操作

```python
# 批量AI写入
write_requests = [
    {
        "target_path": "report1.txt",
        "content_requirements": "技术报告1",
        "generation_mode": "generate",
        "document_format": "txt"
    },
    {
        "target_path": "report2.md", 
        "content_requirements": "技术报告2",
        "generation_mode": "generate",
        "document_format": "markdown"
    }
]

batch_result = orchestrator.batch_ai_write(
    write_requests=write_requests,
    coordination_strategy="parallel",
    max_concurrent=3
)

print(f"批量写入: 成功 {batch_result['successful_requests']}, 失败 {batch_result['failed_requests']}")
```

### 8. 模板化文档生成

```python
# 创建内容模板
template_info = orchestrator.create_content_template(
    template_name="project_report",
    template_content="""
# 项目报告: {project_name}

## 概述
项目 {project_name} 在 {project_period} 期间取得了以下进展：

## 主要成果
{achievements}

## 下一步计划
{next_steps}

## 项目团队
负责人: {team_lead}
团队成员: {team_members}
    """,
    template_variables=["project_name", "project_period", "achievements", "next_steps", "team_lead", "team_members"]
)

# 使用模板生成文档
result = orchestrator.use_content_template(
    template_name="project_report",
    template_data={
        "project_name": "AI文档处理系统",
        "project_period": "2024年Q1",
        "achievements": "完成核心功能开发",
        "next_steps": "性能优化和测试",
        "team_lead": "张工程师",
        "team_members": "李开发、王测试、陈产品"
    },
    target_path="q1_project_report.md",
    ai_enhancement=True
)
```

## ⚙️ 配置选项

### DocumentWriterTool 配置

```python
config = {
    # 基础配置
    "temp_dir": "/tmp/document_writer",
    "backup_dir": "/tmp/document_backups", 
    "max_file_size": 100 * 1024 * 1024,  # 100MB
    "default_encoding": "utf-8",
    
    # 功能开关
    "enable_backup": True,
    "enable_versioning": True,
    "enable_content_validation": True,
    "enable_security_scan": True,
    "atomic_write": True,
    
    # 云存储配置
    "enable_cloud_storage": True,
    "gcs_bucket_name": "my-documents",
    "gcs_project_id": "my-project",
    
    # 版本管理
    "max_backup_versions": 10
}

writer = DocumentWriterTool(config)
```

### AIDocumentWriterOrchestrator 配置

```python
config = {
    # AI配置
    "default_ai_provider": "openai",
    "max_content_length": 50000,
    "default_temperature": 0.3,
    "max_tokens": 4000,
    
    # 写入配置
    "max_concurrent_writes": 5,
    "enable_draft_mode": True,
    "enable_content_review": True,
    "auto_backup_on_ai_write": True
}

orchestrator = AIDocumentWriterOrchestrator(config)
```

## 🔒 安全性和验证

### 1. 内容验证级别

```python
# 无验证
result = writer.write_document(
    target_path="file.txt",
    content="内容",
    format="txt",
    validation_level="none"
)

# 基础验证 - 格式和大小检查
result = writer.write_document(
    target_path="data.json",
    content='{"key": "value"}',
    format="json",
    validation_level="basic"  # 验证JSON格式
)

# 严格验证 - 内容和结构检查
result = writer.write_document(
    target_path="config.xml",
    content="<config><item>value</item></config>",
    format="xml",
    validation_level="strict"  # 验证XML结构
)

# 企业级验证 - 安全扫描
result = writer.write_document(
    target_path="user_content.html",
    content="<p>用户提交的内容</p>",
    format="html",
    validation_level="enterprise"  # 安全扫描
)
```

### 2. 权限和安全检查

```python
# 检查写入权限
try:
    result = writer.write_document(
        target_path="/protected/file.txt",
        content="内容",
        format="txt",
        mode="create"
    )
except WritePermissionError as e:
    print(f"权限错误: {e}")

# 安全内容过滤
try:
    result = writer.write_document(
        target_path="user_input.html",
        content="<script>alert('xss')</script>",  # 危险内容
        format="html",
        validation_level="enterprise"
    )
except ContentValidationError as e:
    print(f"内容验证失败: {e}")
```

## 📊 生产级特性

### 1. 原子性操作

```python
# 原子写入 - 使用临时文件确保操作完整性
config = {"atomic_write": True}
writer = DocumentWriterTool(config)

# 即使在写入过程中发生错误，也不会产生部分写入的文件
result = writer.write_document(
    target_path="critical_data.json",
    content=large_json_data,
    format="json",
    mode="create"
)
```

### 2. 事务性批量操作

```python
# 事务性批量写入
write_operations = [
    {
        "target_path": "file1.txt",
        "content": "内容1",
        "format": "txt",
        "mode": "create"
    },
    {
        "target_path": "file2.json", 
        "content": {"data": "value"},
        "format": "json",
        "mode": "create"
    }
]

try:
    result = writer.batch_write_documents(
        write_operations=write_operations,
        transaction_mode=True,      # 事务模式
        rollback_on_error=True      # 出错时回滚
    )
    print("批量写入成功")
except DocumentWriterError as e:
    print(f"批量写入失败，已回滚: {e}")
```

### 3. 自动备份和版本控制

```python
# 自动备份
result = writer.write_document(
    target_path="important_config.json",
    content=updated_config,
    format="json",
    mode="backup_write",  # 自动创建备份
    backup_comment="配置更新v2.1"
)

# 查看备份信息
backup_info = result['backup_info']
print(f"备份路径: {backup_info['backup_path']}")
print(f"备份时间: {backup_info['timestamp']}")

# 版本历史
version_info = result['version_info']
print(f"版本号: {version_info['version']}")
```

### 4. 审计和监控

```python
# 审计日志
audit_info = result['audit_info']
print(f"操作ID: {audit_info['operation_id']}")
print(f"文件大小: {audit_info['file_size']}")
print(f"校验和: {audit_info['checksum']}")

# 操作统计
stats = {
    "total_operations": result['processing_metadata']['duration'],
    "success_rate": "100%",
    "average_time": f"{result['processing_metadata']['duration']:.2f}s"
}
```

## 🔄 写入策略详解

### 1. CREATE vs OVERWRITE

```python
# CREATE - 安全创建，文件存在时失败
try:
    result = writer.write_document(
        target_path="new_file.txt",
        content="内容", 
        format="txt",
        mode="create"  # 文件存在会抛出异常
    )
except DocumentWriterError as e:
    print("文件已存在，创建失败")

# OVERWRITE - 直接覆盖
result = writer.write_document(
    target_path="existing_file.txt",
    content="新内容",
    format="txt", 
    mode="overwrite"  # 直接覆盖，不备份
)
```

### 2. APPEND vs UPDATE

```python
# APPEND - 追加内容
result = writer.write_document(
    target_path="log.txt",
    content="\n2024-01-01 新日志条目",
    format="txt",
    mode="append"  # 在文件末尾追加
)

# UPDATE - 智能更新（需要实现具体逻辑）
result = writer.write_document(
    target_path="config.json",
    content={"new_setting": "value"},
    format="json",
    mode="update"  # 智能合并JSON
)
```

### 3. 备份策略

```python
# 额外保存 - 使用不同文件名
result = writer.write_document(
    target_path="document_v2.txt",
    content="新版本内容",
    format="txt",
    mode="create"  # 保留原文件，创建新版本
)

# 覆盖保存 - 带自动备份
result = writer.write_document(
    target_path="document.txt", 
    content="更新内容",
    format="txt",
    mode="backup_write"  # 自动备份原文件后覆盖
)
```

## 🚨 错误处理和回滚

### 常见错误类型

```python
from aiecs.tools.docs.document_writer_tool import (
    DocumentWriterError,
    WritePermissionError, 
    ContentValidationError,
    StorageError
)

try:
    result = writer.write_document(...)
    
except WritePermissionError as e:
    print(f"权限错误: {e}")
    
except ContentValidationError as e:
    print(f"内容验证失败: {e}")
    
except StorageError as e:
    print(f"存储错误: {e}")
    
except DocumentWriterError as e:
    print(f"写入错误: {e}")
```

### 回滚操作

```python
# 自动回滚示例
def safe_update_config(config_path, new_config):
    """安全更新配置文件"""
    try:
        result = writer.write_document(
            target_path=config_path,
            content=new_config,
            format="json",
            mode="backup_write"  # 自动备份
        )
        return result
        
    except Exception as e:
        # 发生错误时，备份会自动用于回滚
        print(f"更新失败，已自动回滚: {e}")
        raise
```

## 📈 性能优化

### 1. 大文件处理

```python
# 配置大文件支持
config = {
    "max_file_size": 500 * 1024 * 1024,  # 500MB
    "atomic_write": True,  # 原子写入对大文件很重要
}

writer = DocumentWriterTool(config)

# 分块处理大内容（由工具内部处理）
large_content = "x" * (10 * 1024 * 1024)  # 10MB内容
result = writer.write_document(
    target_path="large_file.txt",
    content=large_content,
    format="txt",
    mode="create"
)
```

### 2. 并发写入控制

```python
# 批量写入性能优化
batch_result = orchestrator.batch_ai_write(
    write_requests=large_write_list,
    coordination_strategy="smart",  # 智能协调
    max_concurrent=10  # 控制并发数
)
```

## 🎯 最佳实践

### 1. 生产环境配置

```python
# 生产环境推荐配置
production_config = {
    # 安全配置
    "enable_content_validation": True,
    "enable_security_scan": True,
    "validation_level": "enterprise",
    
    # 可靠性配置  
    "atomic_write": True,
    "enable_backup": True,
    "enable_versioning": True,
    "max_backup_versions": 5,
    
    # 性能配置
    "max_file_size": 100 * 1024 * 1024,
    "max_concurrent_writes": 5,
    
    # 云存储配置
    "enable_cloud_storage": True,
    "gcs_bucket_name": "prod-documents"
}
```

### 2. 错误处理策略

```python
def robust_document_write(target_path, content, format_type):
    """健壮的文档写入"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            result = writer.write_document(
                target_path=target_path,
                content=content,
                format=format_type,
                mode="backup_write",
                validation_level="strict"
            )
            return result
            
        except WritePermissionError:
            # 权限错误不重试
            raise
        except (StorageError, ContentValidationError) as e:
            if attempt == max_retries - 1:
                raise
            print(f"写入失败，重试 {attempt + 1}/{max_retries}: {e}")
            time.sleep(1)  # 等待后重试
```

### 3. 监控和日志

```python
import logging

# 配置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 启用写入工具调试日志
logging.getLogger('aiecs.tools.docs.document_writer_tool').setLevel(logging.DEBUG)

# 监控写入操作
def monitor_write_operation(result):
    """监控写入操作"""
    metadata = result['processing_metadata']
    duration = metadata['duration']
    
    if duration > 5.0:  # 超过5秒的操作
        logger.warning(f"Slow write operation: {duration:.2f}s")
    
    # 记录文件大小
    file_size = result['write_result']['size']
    logger.info(f"Written file size: {file_size} bytes")
```

## 🔮 高级特性

### 1. 自定义格式转换器

```python
# 扩展格式支持
class CustomDocumentWriter(DocumentWriterTool):
    def _convert_to_custom_format(self, content):
        # 实现自定义格式转换
        return f"CUSTOM:{content}"
```

### 2. 插件式验证器

```python
# 自定义验证器
def custom_validator(content, format_type, validation_level):
    """自定义内容验证器"""
    if "禁用词" in content:
        raise ContentValidationError("内容包含禁用词")
    return True

# 注册自定义验证器
writer.validators["custom"] = custom_validator
```

## 📚 总结

文档写入组件提供了：

✅ **生产级可靠性** - 原子操作、事务支持、自动备份  
✅ **企业级安全性** - 内容验证、安全扫描、权限控制  
✅ **多格式支持** - 文本、JSON、XML、HTML等格式  
✅ **智能写入模式** - 创建、覆盖、追加、更新等策略  
✅ **AI增强功能** - AI内容生成、格式转换、模板处理  
✅ **云存储集成** - 无缝云存储读写支持  
✅ **性能优化** - 批量操作、并发控制、大文件支持  

开发者现在可以使用这套现代化的文档写入组件来构建安全、可靠、高性能的文档处理应用！
