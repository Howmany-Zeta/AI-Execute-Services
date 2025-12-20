# AIECS 工具配置指南

本文档列出了所有工具的配置参数，方便开发者快速配置和使用。

生成时间: check_all_tools_config.py

## 目录

1. [AIDataAnalysisOrchestrator](#aidataanalysisorchestrator)
2. [AIDocumentOrchestrator](#aidocumentorchestrator)
3. [AIDocumentWriterOrchestrator](#aidocumentwriterorchestrator)
4. [AIInsightGeneratorTool](#aiinsightgeneratortool)
5. [AIReportOrchestratorTool](#aireportorchestratortool)
6. [APISourceTool](#apisourcetool)
7. [ChartTool](#charttool)
8. [ClassifierTool](#classifiertool)
9. [ContentInsertionTool](#contentinsertiontool)
10. [DataLoaderTool](#dataloadertool)
11. [DataProfilerTool](#dataprofilertool)
12. [DataTransformerTool](#datatransformertool)
13. [DataVisualizerTool](#datavisualizertool)
14. [DocumentCreatorTool](#documentcreatortool)
15. [DocumentLayoutTool](#documentlayouttool)
16. [DocumentParserTool](#documentparsertool)
17. [DocumentWriterTool](#documentwritertool)
18. [GraphReasoningTool](#graphreasoningtool)
19. [GraphSearchTool](#graphsearchtool)
20. [ImageTool](#imagetool)
21. [KnowledgeGraphBuilderTool](#knowledgegraphbuildertool)
22. [ModelTrainerTool](#modeltrainertool)
23. [OfficeTool](#officetool)
24. [PandasTool](#pandastool)
25. [ReportTool](#reporttool)
26. [ResearchTool](#researchtool)
27. [ScraperTool](#scrapertool)
28. [StatisticalAnalyzerTool](#statisticalanalyzertool)
29. [StatsTool](#statstool)

---

## AIDataAnalysisOrchestrator

**配置字段数**: 6 (必需: 6, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | AI_DATA_ORCHESTRATOR_DEFAULT_MODE -> default_mode | ✅ | `-` | - |
| `default_ai_provider` | str | ✅ | `"openai"` | Default AI provider to use |
| `default_mode` | str | ✅ | `"exploratory"` | Default analysis mode to use |
| `enable_auto_workflow` | bool | ✅ | `-` | - |
| `enable_caching` | bool | ✅ | `True` | Whether to enable result caching |
| `max_iterations` | int | ✅ | `10` | Maximum number of analysis iterations |

### 配置示例

```python
aidataanalysisorchestrator_config = {
    'Example': "your_Example",
    'default_ai_provider': "openai",  # Default AI provider to use
    'default_mode': "exploratory",  # Default analysis mode to use
    'enable_auto_workflow': False,
    'enable_caching': True,  # Whether to enable result caching
    'max_iterations': 10,  # Maximum number of analysis iterations
}
```

### 环境变量映射

```bash
export AIDATAANALYSIS_ORCHESTRATOR_EXAMPLE=<value>
export AIDATAANALYSIS_ORCHESTRATOR_DEFAULT_AI_PROVIDER=<value>
export AIDATAANALYSIS_ORCHESTRATOR_DEFAULT_MODE=<value>
export AIDATAANALYSIS_ORCHESTRATOR_ENABLE_AUTO_WORKFLOW=<value>
export AIDATAANALYSIS_ORCHESTRATOR_ENABLE_CACHING=<value>
export AIDATAANALYSIS_ORCHESTRATOR_MAX_ITERATIONS=<value>
```

---

## AIDocumentOrchestrator

**配置字段数**: 7 (必需: 7, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | AI_DOC_ORCHESTRATOR_DEFAULT_AI_PROVIDER -> default_ai_provider | ✅ | `-` | - |
| `default_ai_provider` | str | ✅ | `"openai"` | Default AI provider to use |
| `default_temperature` | float | ✅ | `0.1` | Default temperature for AI model |
| `max_chunk_size` | int | ✅ | `4000` | Maximum chunk size for AI processing |
| `max_concurrent_requests` | int | ✅ | `5` | Maximum concurrent AI requests |
| `max_tokens` | int | ✅ | `2000` | Maximum tokens for AI response |
| `timeout` | int | ✅ | `60` | Timeout in seconds for AI operations |

### 配置示例

```python
aidocumentorchestrator_config = {
    'Example': "your_Example",
    'default_ai_provider': "openai",  # Default AI provider to use
    'default_temperature': 0.1,  # Default temperature for AI model
    'max_chunk_size': 4000,  # Maximum chunk size for AI processing
    'max_concurrent_requests': 5,  # Maximum concurrent AI requests
    'max_tokens': 2000,  # Maximum tokens for AI response
    'timeout': 60,  # Timeout in seconds for AI operations
}
```

### 环境变量映射

```bash
export AIDOCUMENT_ORCHESTRATOR_EXAMPLE=<value>
export AIDOCUMENT_ORCHESTRATOR_DEFAULT_AI_PROVIDER=<value>
export AIDOCUMENT_ORCHESTRATOR_DEFAULT_TEMPERATURE=<value>
export AIDOCUMENT_ORCHESTRATOR_MAX_CHUNK_SIZE=<value>
export AIDOCUMENT_ORCHESTRATOR_MAX_CONCURRENT_REQUESTS=<value>
export AIDOCUMENT_ORCHESTRATOR_MAX_TOKENS=<value>
export AIDOCUMENT_ORCHESTRATOR_TIMEOUT=<value>
```

---

## AIDocumentWriterOrchestrator

**配置字段数**: 10 (必需: 10, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `auto_backup_on_ai_write` | bool | ✅ | `-` | - |
| `default_ai_provider` | str | ✅ | `"openai"` | Default AI provider to use |
| `default_temperature` | float | ✅ | `0.3` | Default temperature for AI model |
| `enable_content_review` | bool | ✅ | `True` | Whether to enable content review |
| `enable_draft_mode` | bool | ✅ | `True` | Whether to enable draft mode |
| `max_concurrent_writes` | int | ✅ | `5` | Maximum concurrent write operations |
| `max_content_length` | int | ✅ | `-` | - |
| `max_tokens` | int | ✅ | `4000` | Maximum tokens for AI response |
| `temp_dir` | str | ✅ | `-` | - |
| `timeout` | int | ✅ | `60` | Timeout in seconds for AI operations |

### 配置示例

```python
aidocumentwriterorchestrator_config = {
    'auto_backup_on_ai_write': False,
    'default_ai_provider': "openai",  # Default AI provider to use
    'default_temperature': 0.3,  # Default temperature for AI model
    'enable_content_review': True,  # Whether to enable content review
    'enable_draft_mode': True,  # Whether to enable draft mode
    'max_concurrent_writes': 5,  # Maximum concurrent write operations
    'max_content_length': 0,
    'max_tokens': 4000,  # Maximum tokens for AI response
    'temp_dir': "your_temp_dir",
    'timeout': 60,  # Timeout in seconds for AI operations
}
```

### 环境变量映射

```bash
export AIDOCUMENTWRITER_ORCHESTRATOR_AUTO_BACKUP_ON_AI_WRITE=<value>
export AIDOCUMENTWRITER_ORCHESTRATOR_DEFAULT_AI_PROVIDER=<value>
export AIDOCUMENTWRITER_ORCHESTRATOR_DEFAULT_TEMPERATURE=<value>
export AIDOCUMENTWRITER_ORCHESTRATOR_ENABLE_CONTENT_REVIEW=<value>
export AIDOCUMENTWRITER_ORCHESTRATOR_ENABLE_DRAFT_MODE=<value>
export AIDOCUMENTWRITER_ORCHESTRATOR_MAX_CONCURRENT_WRITES=<value>
export AIDOCUMENTWRITER_ORCHESTRATOR_MAX_CONTENT_LENGTH=<value>
export AIDOCUMENTWRITER_ORCHESTRATOR_MAX_TOKENS=<value>
export AIDOCUMENTWRITER_ORCHESTRATOR_TEMP_DIR=<value>
export AIDOCUMENTWRITER_ORCHESTRATOR_TIMEOUT=<value>
```

---

## AIInsightGeneratorTool

**配置字段数**: 5 (必需: 5, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | AI_INSIGHT_GENERATOR_MIN_CONFIDENCE -> min_confidence | ✅ | `-` | - |
| `anomaly_std_threshold` | float | ✅ | `-` | - |
| `correlation_threshold` | float | ✅ | `-` | - |
| `enable_reasoning` | bool | ✅ | `-` | - |
| `min_confidence` | float | ✅ | `-` | - |

### 配置示例

```python
aiinsightgeneratortool_config = {
    'Example': None,
    'anomaly_std_threshold': 0.0,
    'correlation_threshold': 0.0,
    'enable_reasoning': False,
    'min_confidence': 0.0,
}
```

### 环境变量映射

```bash
export AIINSIGHTGENERATOR_TOOL_EXAMPLE=<value>
export AIINSIGHTGENERATOR_TOOL_ANOMALY_STD_THRESHOLD=<value>
export AIINSIGHTGENERATOR_TOOL_CORRELATION_THRESHOLD=<value>
export AIINSIGHTGENERATOR_TOOL_ENABLE_REASONING=<value>
export AIINSIGHTGENERATOR_TOOL_MIN_CONFIDENCE=<value>
```

---

## AIReportOrchestratorTool

**配置字段数**: 7 (必需: 7, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | AI_REPORT_ORCHESTRATOR_DEFAULT_REPORT_TYPE -> default_report_type | ✅ | `-` | - |
| `default_format` | str | ✅ | `"markdown"` | Default report output format |
| `default_report_type` | str | ✅ | `-` | - |
| `include_code` | bool | ✅ | `-` | - |
| `include_visualizations` | bool | ✅ | `-` | - |
| `max_insights_per_report` | int | ✅ | `-` | - |
| `output_directory` | str | ✅ | `-` | - |

### 配置示例

```python
aireportorchestratortool_config = {
    'Example': "your_Example",
    'default_format': "markdown",  # Default report output format
    'default_report_type': "your_default_report_type",
    'include_code': False,
    'include_visualizations': False,
    'max_insights_per_report': 0,
    'output_directory': "your_output_directory",
}
```

### 环境变量映射

```bash
export AIREPORT_ORCHESTRATOR_TOOL_EXAMPLE=<value>
export AIREPORT_ORCHESTRATOR_TOOL_DEFAULT_FORMAT=<value>
export AIREPORT_ORCHESTRATOR_TOOL_DEFAULT_REPORT_TYPE=<value>
export AIREPORT_ORCHESTRATOR_TOOL_INCLUDE_CODE=<value>
export AIREPORT_ORCHESTRATOR_TOOL_INCLUDE_VISUALIZATIONS=<value>
export AIREPORT_ORCHESTRATOR_TOOL_MAX_INSIGHTS_PER_REPORT=<value>
export AIREPORT_ORCHESTRATOR_TOOL_OUTPUT_DIRECTORY=<value>
```

---

## APISourceTool

**配置字段数**: 11 (必需: 11, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | APISOURCE_TOOL_FRED_API_KEY -> fred_api_key | ✅ | `-` | - |
| `cache_ttl` | int | ✅ | `-` | - |
| `census_api_key` | Optional[str] | ✅ | `None` | API key for US Census Bureau |
| `default_timeout` | int | ✅ | `-` | - |
| `enable_data_fusion` | bool | ✅ | `-` | - |
| `enable_fallback` | bool | ✅ | `-` | - |
| `enable_query_enhancement` | bool | ✅ | `-` | - |
| `enable_rate_limiting` | bool | ✅ | `-` | - |
| `fred_api_key` | Optional[str] | ✅ | `-` | - |
| `max_retries` | int | ✅ | `-` | - |
| `newsapi_api_key` | Optional[str] | ✅ | `None` | API key for News API |

### 配置示例

```python
apisourcetool_config = {
    'Example': None,
    'cache_ttl': 0,
    'census_api_key': None,  # API key for US Census Bureau
    'default_timeout': 0,
    'enable_data_fusion': False,
    'enable_fallback': False,
    'enable_query_enhancement': False,
    'enable_rate_limiting': False,
    'fred_api_key': "your_fred_api_key",
    'max_retries': 0,
    'newsapi_api_key': None,  # API key for News API
}
```

### 环境变量映射

```bash
export APISOURCE_TOOL_EXAMPLE=<value>
export APISOURCE_TOOL_CACHE_TTL=<value>
export APISOURCE_TOOL_CENSUS_API_KEY=<value>
export APISOURCE_TOOL_DEFAULT_TIMEOUT=<value>
export APISOURCE_TOOL_ENABLE_DATA_FUSION=<value>
export APISOURCE_TOOL_ENABLE_FALLBACK=<value>
export APISOURCE_TOOL_ENABLE_QUERY_ENHANCEMENT=<value>
export APISOURCE_TOOL_ENABLE_RATE_LIMITING=<value>
export APISOURCE_TOOL_FRED_API_KEY=<value>
export APISOURCE_TOOL_MAX_RETRIES=<value>
export APISOURCE_TOOL_NEWSAPI_API_KEY=<value>
```

---

## ChartTool

**配置字段数**: 5 (必需: 5, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | CHART_TOOL_EXPORT_DIR -> export_dir | ✅ | `-` | - |
| `allowed_extensions` | List[str] | ✅ | `-` | - |
| `export_dir` | str | ✅ | `-` | - |
| `plot_dpi` | int | ✅ | `100` | DPI for plot exports |
| `plot_figsize` | Tuple[int, int] | ✅ | `-` | - |

### 配置示例

```python
charttool_config = {
    'Example': None,
    'allowed_extensions': "your_allowed_extensions",
    'export_dir': "your_export_dir",
    'plot_dpi': 100,  # DPI for plot exports
    'plot_figsize': 0,
}
```

### 环境变量映射

```bash
export CHART_TOOL_EXAMPLE=<value>
export CHART_TOOL_ALLOWED_EXTENSIONS=<value>
export CHART_TOOL_EXPORT_DIR=<value>
export CHART_TOOL_PLOT_DPI=<value>
export CHART_TOOL_PLOT_FIGSIZE=<value>
```

---

## ClassifierTool

**配置字段数**: 12 (必需: 12, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | CLASSIFIER_TOOL_MAX_WORKERS -> max_workers | ✅ | `-` | - |
| `allowed_models` | List[str] | ✅ | `-` | - |
| `max_text_length` | int | ✅ | `10_000` | Maximum text length in characters |
| `max_workers` | int | ✅ | `-` | - |
| `pipeline_cache_size` | int | ✅ | `10` | Maximum number of pipeline cache entries |
| `pipeline_cache_ttl` | int | ✅ | `-` | - |
| `rate_limit_enabled` | bool | ✅ | `True` | Enable rate limiting |
| `rate_limit_requests` | int | ✅ | `100` | Maximum requests per window |
| `rate_limit_window` | int | ✅ | `60` | Rate limit window in seconds |
| `spacy_model_en` | str | ✅ | `"en_core_web_sm"` | spaCy model for English |
| `spacy_model_zh` | str | ✅ | `"zh_core_web_sm"` | spaCy model for Chinese |
| `use_rake_for_english` | bool | ✅ | `True` | Use RAKE for English phrase extraction |

### 配置示例

```python
classifiertool_config = {
    'Example': None,
    'allowed_models': "your_allowed_models",
    'max_text_length': 10_000,  # Maximum text length in characters
    'max_workers': 0,
    'pipeline_cache_size': 10,  # Maximum number of pipeline cache entries
    'pipeline_cache_ttl': 0,
    'rate_limit_enabled': True,  # Enable rate limiting
    'rate_limit_requests': 100,  # Maximum requests per window
    'rate_limit_window': 60,  # Rate limit window in seconds
    'spacy_model_en': "en_core_web_sm",  # spaCy model for English
    'spacy_model_zh': "zh_core_web_sm",  # spaCy model for Chinese
    'use_rake_for_english': True,  # Use RAKE for English phrase extraction
}
```

### 环境变量映射

```bash
export CLASSIFIER_TOOL_EXAMPLE=<value>
export CLASSIFIER_TOOL_ALLOWED_MODELS=<value>
export CLASSIFIER_TOOL_MAX_TEXT_LENGTH=<value>
export CLASSIFIER_TOOL_MAX_WORKERS=<value>
export CLASSIFIER_TOOL_PIPELINE_CACHE_SIZE=<value>
export CLASSIFIER_TOOL_PIPELINE_CACHE_TTL=<value>
export CLASSIFIER_TOOL_RATE_LIMIT_ENABLED=<value>
export CLASSIFIER_TOOL_RATE_LIMIT_REQUESTS=<value>
export CLASSIFIER_TOOL_RATE_LIMIT_WINDOW=<value>
export CLASSIFIER_TOOL_SPACY_MODEL_EN=<value>
export CLASSIFIER_TOOL_SPACY_MODEL_ZH=<value>
export CLASSIFIER_TOOL_USE_RAKE_FOR_ENGLISH=<value>
```

---

## ContentInsertionTool

**配置字段数**: 8 (必需: 8, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | CONTENT_INSERT_TEMP_DIR -> temp_dir | ✅ | `-` | - |
| `assets_dir` | str | ✅ | `-` | - |
| `auto_resize` | bool | ✅ | `-` | - |
| `default_image_format` | str | ✅ | `-` | - |
| `max_chart_size` | Tuple[int, int] | ✅ | `-` | - |
| `max_image_size` | int | ✅ | `10 * 1024 * 1024` | Maximum image size in bytes |
| `optimize_images` | bool | ✅ | `-` | - |
| `temp_dir` | str | ✅ | `-` | - |

### 配置示例

```python
contentinsertiontool_config = {
    'Example': None,
    'assets_dir': "your_assets_dir",
    'auto_resize': False,
    'default_image_format': "your_default_image_format",
    'max_chart_size': 0,
    'max_image_size': 10 * 1024 * 1024,  # Maximum image size in bytes
    'optimize_images': False,
    'temp_dir': "your_temp_dir",
}
```

### 环境变量映射

```bash
export CONTENTINSERTION_TOOL_EXAMPLE=<value>
export CONTENTINSERTION_TOOL_ASSETS_DIR=<value>
export CONTENTINSERTION_TOOL_AUTO_RESIZE=<value>
export CONTENTINSERTION_TOOL_DEFAULT_IMAGE_FORMAT=<value>
export CONTENTINSERTION_TOOL_MAX_CHART_SIZE=<value>
export CONTENTINSERTION_TOOL_MAX_IMAGE_SIZE=<value>
export CONTENTINSERTION_TOOL_OPTIMIZE_IMAGES=<value>
export CONTENTINSERTION_TOOL_TEMP_DIR=<value>
```

---

## DataLoaderTool

**配置字段数**: 7 (必需: 7, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | DATA_LOADER_MAX_FILE_SIZE_MB -> max_file_size_mb | ✅ | `-` | - |
| `default_chunk_size` | int | ✅ | `10000` | Default chunk size for chunked loading |
| `default_encoding` | str | ✅ | `-` | - |
| `enable_quality_validation` | bool | ✅ | `-` | - |
| `enable_schema_inference` | bool | ✅ | `-` | - |
| `max_file_size_mb` | int | ✅ | `500` | Maximum file size in megabytes |
| `max_memory_usage_mb` | int | ✅ | `2000` | Maximum memory usage in megabytes |

### 配置示例

```python
dataloadertool_config = {
    'Example': None,
    'default_chunk_size': 10000,  # Default chunk size for chunked loading
    'default_encoding': "your_default_encoding",
    'enable_quality_validation': False,
    'enable_schema_inference': False,
    'max_file_size_mb': 500,  # Maximum file size in megabytes
    'max_memory_usage_mb': 2000,  # Maximum memory usage in megabytes
}
```

### 环境变量映射

```bash
export DATALOADER_TOOL_EXAMPLE=<value>
export DATALOADER_TOOL_DEFAULT_CHUNK_SIZE=<value>
export DATALOADER_TOOL_DEFAULT_ENCODING=<value>
export DATALOADER_TOOL_ENABLE_QUALITY_VALIDATION=<value>
export DATALOADER_TOOL_ENABLE_SCHEMA_INFERENCE=<value>
export DATALOADER_TOOL_MAX_FILE_SIZE_MB=<value>
export DATALOADER_TOOL_MAX_MEMORY_USAGE_MB=<value>
```

---

## DataProfilerTool

**配置字段数**: 7 (必需: 7, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | DATA_PROFILER_DEFAULT_PROFILE_LEVEL -> default_profile_level | ✅ | `-` | - |
| `correlation_threshold` | float | ✅ | `-` | - |
| `default_profile_level` | str | ✅ | `"standard"` | Default profiling depth level |
| `enable_visualizations` | bool | ✅ | `-` | - |
| `max_unique_values_categorical` | int | ✅ | `-` | - |
| `missing_threshold` | float | ✅ | `-` | - |
| `outlier_std_threshold` | float | ✅ | `-` | - |

### 配置示例

```python
dataprofilertool_config = {
    'Example': None,
    'correlation_threshold': 0.0,
    'default_profile_level': "standard",  # Default profiling depth level
    'enable_visualizations': False,
    'max_unique_values_categorical': 0,
    'missing_threshold': 0.0,
    'outlier_std_threshold': 0.0,
}
```

### 环境变量映射

```bash
export DATAPROFILER_TOOL_EXAMPLE=<value>
export DATAPROFILER_TOOL_CORRELATION_THRESHOLD=<value>
export DATAPROFILER_TOOL_DEFAULT_PROFILE_LEVEL=<value>
export DATAPROFILER_TOOL_ENABLE_VISUALIZATIONS=<value>
export DATAPROFILER_TOOL_MAX_UNIQUE_VALUES_CATEGORICAL=<value>
export DATAPROFILER_TOOL_MISSING_THRESHOLD=<value>
export DATAPROFILER_TOOL_OUTLIER_STD_THRESHOLD=<value>
```

---

## DataTransformerTool

**配置字段数**: 5 (必需: 5, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | DATA_TRANSFORMER_OUTLIER_STD_THRESHOLD -> outlier_std_threshold | ✅ | `-` | - |
| `default_missing_strategy` | str | ✅ | `-` | - |
| `enable_pipeline_caching` | bool | ✅ | `-` | - |
| `max_one_hot_categories` | int | ✅ | `-` | - |
| `outlier_std_threshold` | float | ✅ | `-` | - |

### 配置示例

```python
datatransformertool_config = {
    'Example': None,
    'default_missing_strategy': "your_default_missing_strategy",
    'enable_pipeline_caching': False,
    'max_one_hot_categories': 0,
    'outlier_std_threshold': 0.0,
}
```

### 环境变量映射

```bash
export DATATRANSFORMER_TOOL_EXAMPLE=<value>
export DATATRANSFORMER_TOOL_DEFAULT_MISSING_STRATEGY=<value>
export DATATRANSFORMER_TOOL_ENABLE_PIPELINE_CACHING=<value>
export DATATRANSFORMER_TOOL_MAX_ONE_HOT_CATEGORIES=<value>
export DATATRANSFORMER_TOOL_OUTLIER_STD_THRESHOLD=<value>
```

---

## DataVisualizerTool

**配置字段数**: 6 (必需: 6, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | DATA_VISUALIZER_DEFAULT_STYLE -> default_style | ✅ | `-` | - |
| `default_dpi` | int | ✅ | `100` | Default DPI for image exports |
| `default_figsize` | List[int] | ✅ | `-` | - |
| `default_output_dir` | str | ✅ | `-` | - |
| `default_style` | str | ✅ | `"static"` | Default visualization style |
| `enable_auto_recommendation` | bool | ✅ | `-` | - |

### 配置示例

```python
datavisualizertool_config = {
    'Example': None,
    'default_dpi': 100,  # Default DPI for image exports
    'default_figsize': 0,
    'default_output_dir': "your_default_output_dir",
    'default_style': "static",  # Default visualization style
    'enable_auto_recommendation': False,
}
```

### 环境变量映射

```bash
export DATAVISUALIZER_TOOL_EXAMPLE=<value>
export DATAVISUALIZER_TOOL_DEFAULT_DPI=<value>
export DATAVISUALIZER_TOOL_DEFAULT_FIGSIZE=<value>
export DATAVISUALIZER_TOOL_DEFAULT_OUTPUT_DIR=<value>
export DATAVISUALIZER_TOOL_DEFAULT_STYLE=<value>
export DATAVISUALIZER_TOOL_ENABLE_AUTO_RECOMMENDATION=<value>
```

---

## DocumentCreatorTool

**配置字段数**: 8 (必需: 8, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | DOC_CREATOR_TEMPLATES_DIR -> templates_dir | ✅ | `-` | - |
| `auto_backup` | bool | ✅ | `-` | - |
| `default_format` | str | ✅ | `"markdown"` | Default output format |
| `default_style` | str | ✅ | `"default"` | Default style preset |
| `generate_toc` | bool | ✅ | `-` | - |
| `include_metadata` | bool | ✅ | `-` | - |
| `output_dir` | str | ✅ | `-` | - |
| `templates_dir` | str | ✅ | `-` | - |

### 配置示例

```python
documentcreatortool_config = {
    'Example': None,
    'auto_backup': False,
    'default_format': "markdown",  # Default output format
    'default_style': "default",  # Default style preset
    'generate_toc': False,
    'include_metadata': False,
    'output_dir': "your_output_dir",
    'templates_dir': "your_templates_dir",
}
```

### 环境变量映射

```bash
export DOCUMENTCREATOR_TOOL_EXAMPLE=<value>
export DOCUMENTCREATOR_TOOL_AUTO_BACKUP=<value>
export DOCUMENTCREATOR_TOOL_DEFAULT_FORMAT=<value>
export DOCUMENTCREATOR_TOOL_DEFAULT_STYLE=<value>
export DOCUMENTCREATOR_TOOL_GENERATE_TOC=<value>
export DOCUMENTCREATOR_TOOL_INCLUDE_METADATA=<value>
export DOCUMENTCREATOR_TOOL_OUTPUT_DIR=<value>
export DOCUMENTCREATOR_TOOL_TEMPLATES_DIR=<value>
```

---

## DocumentLayoutTool

**配置字段数**: 7 (必需: 7, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | DOC_LAYOUT_TEMP_DIR -> temp_dir | ✅ | `-` | - |
| `auto_adjust_layout` | bool | ✅ | `-` | - |
| `default_margins` | Dict[str, float] | ✅ | `-` | - |
| `default_orientation` | str | ✅ | `"portrait"` | Default page orientation |
| `default_page_size` | str | ✅ | `"a4"` | Default page size |
| `preserve_formatting` | bool | ✅ | `-` | - |
| `temp_dir` | str | ✅ | `-` | - |

### 配置示例

```python
documentlayouttool_config = {
    'Example': None,
    'auto_adjust_layout': False,
    'default_margins': "your_default_margins",
    'default_orientation': "portrait",  # Default page orientation
    'default_page_size': "a4",  # Default page size
    'preserve_formatting': False,
    'temp_dir': "your_temp_dir",
}
```

### 环境变量映射

```bash
export DOCUMENTLAYOUT_TOOL_EXAMPLE=<value>
export DOCUMENTLAYOUT_TOOL_AUTO_ADJUST_LAYOUT=<value>
export DOCUMENTLAYOUT_TOOL_DEFAULT_MARGINS=<value>
export DOCUMENTLAYOUT_TOOL_DEFAULT_ORIENTATION=<value>
export DOCUMENTLAYOUT_TOOL_DEFAULT_PAGE_SIZE=<value>
export DOCUMENTLAYOUT_TOOL_PRESERVE_FORMATTING=<value>
export DOCUMENTLAYOUT_TOOL_TEMP_DIR=<value>
```

---

## DocumentParserTool

**配置字段数**: 10 (必需: 10, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | DOC_PARSER_TIMEOUT -> timeout | ✅ | `-` | - |
| `default_encoding` | str | ✅ | `"utf-8"` | Default encoding for text files |
| `enable_cloud_storage` | bool | ✅ | `-` | - |
| `gcs_bucket_name` | str | ✅ | `-` | - |
| `gcs_project_id` | Optional[str] | ✅ | `None` | Google Cloud Storage project ID |
| `max_file_size` | int | ✅ | `50 * 1024 * 1024` | Maximum file size in bytes |
| `max_pages` | int | ✅ | `-` | - |
| `temp_dir` | str | ✅ | `-` | - |
| `timeout` | int | ✅ | `30` | Timeout for HTTP requests in seconds |
| `user_agent` | str | ✅ | `-` | - |

### 配置示例

```python
documentparsertool_config = {
    'Example': None,
    'default_encoding': "utf-8",  # Default encoding for text files
    'enable_cloud_storage': False,
    'gcs_bucket_name': "your_gcs_bucket_name",
    'gcs_project_id': None,  # Google Cloud Storage project ID
    'max_file_size': 50 * 1024 * 1024,  # Maximum file size in bytes
    'max_pages': 0,
    'temp_dir': "your_temp_dir",
    'timeout': 30,  # Timeout for HTTP requests in seconds
    'user_agent': "your_user_agent",
}
```

### 环境变量映射

```bash
export DOCUMENTPARSER_TOOL_EXAMPLE=<value>
export DOCUMENTPARSER_TOOL_DEFAULT_ENCODING=<value>
export DOCUMENTPARSER_TOOL_ENABLE_CLOUD_STORAGE=<value>
export DOCUMENTPARSER_TOOL_GCS_BUCKET_NAME=<value>
export DOCUMENTPARSER_TOOL_GCS_PROJECT_ID=<value>
export DOCUMENTPARSER_TOOL_MAX_FILE_SIZE=<value>
export DOCUMENTPARSER_TOOL_MAX_PAGES=<value>
export DOCUMENTPARSER_TOOL_TEMP_DIR=<value>
export DOCUMENTPARSER_TOOL_TIMEOUT=<value>
export DOCUMENTPARSER_TOOL_USER_AGENT=<value>
```

---

## DocumentWriterTool

**配置字段数**: 22 (必需: 22, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | DOC_WRITER_GCS_PROJECT_ID -> gcs_project_id | ✅ | `-` | - |
| `atomic_write` | bool | ✅ | `True` | Whether to use atomic write operations |
| `atomic_writes` | bool | ✅ | `True` | Whether to use atomic write operations |
| `auto_backup` | bool | ✅ | `-` | - |
| `backup_dir` | str | ✅ | `-` | - |
| `default_encoding` | str | ✅ | `"utf-8"` | Default text encoding for documents |
| `default_format` | str | ✅ | `"md"` | Default document format |
| `enable_backup` | bool | ✅ | `-` | - |
| `enable_cloud_storage` | bool | ✅ | `-` | - |
| `enable_content_validation` | bool | ✅ | `True` | Whether to enable content validation |
| `enable_security_scan` | bool | ✅ | `True` | Whether to enable security scanning |
| `enable_versioning` | bool | ✅ | `True` | Whether to enable document versioning |
| `gcs_bucket_name` | str | ✅ | `-` | - |
| `gcs_project_id` | Optional[str] | ✅ | `None` | Google Cloud Storage project ID |
| `max_backup_versions` | int | ✅ | `10` | Maximum number of backup versions to keep |
| `max_file_size` | int | ✅ | `100 * 1024 * 1024` | Maximum file size in bytes |
| `output_dir` | Optional[str] | ✅ | `None` | Default output directory for documents |
| `security_scan` | bool | ✅ | `True` | Whether to enable security scanning |
| `temp_dir` | str | ✅ | `-` | - |
| `timeout_seconds` | int | ✅ | `60` | Operation timeout in seconds |
| `validation_level` | str | ✅ | `"basic"` | Content validation level |
| `version_control` | bool | ✅ | `True` | Whether to enable version control |

### 配置示例

```python
documentwritertool_config = {
    'Example': None,
    'atomic_write': True,  # Whether to use atomic write operations
    'atomic_writes': True,  # Whether to use atomic write operations
    'auto_backup': False,
    'backup_dir': "your_backup_dir",
    'default_encoding': "utf-8",  # Default text encoding for documents
    'default_format': "md",  # Default document format
    'enable_backup': False,
    'enable_cloud_storage': False,
    'enable_content_validation': True,  # Whether to enable content validation
    'enable_security_scan': True,  # Whether to enable security scanning
    'enable_versioning': True,  # Whether to enable document versioning
    'gcs_bucket_name': "your_gcs_bucket_name",
    'gcs_project_id': None,  # Google Cloud Storage project ID
    'max_backup_versions': 10,  # Maximum number of backup versions to keep
    'max_file_size': 100 * 1024 * 1024,  # Maximum file size in bytes
    'output_dir': None,  # Default output directory for documents
    'security_scan': True,  # Whether to enable security scanning
    'temp_dir': "your_temp_dir",
    'timeout_seconds': 60,  # Operation timeout in seconds
    'validation_level': "basic",  # Content validation level
    'version_control': True,  # Whether to enable version control
}
```

### 环境变量映射

```bash
export DOCUMENTWRITER_TOOL_EXAMPLE=<value>
export DOCUMENTWRITER_TOOL_ATOMIC_WRITE=<value>
export DOCUMENTWRITER_TOOL_ATOMIC_WRITES=<value>
export DOCUMENTWRITER_TOOL_AUTO_BACKUP=<value>
export DOCUMENTWRITER_TOOL_BACKUP_DIR=<value>
export DOCUMENTWRITER_TOOL_DEFAULT_ENCODING=<value>
export DOCUMENTWRITER_TOOL_DEFAULT_FORMAT=<value>
export DOCUMENTWRITER_TOOL_ENABLE_BACKUP=<value>
export DOCUMENTWRITER_TOOL_ENABLE_CLOUD_STORAGE=<value>
export DOCUMENTWRITER_TOOL_ENABLE_CONTENT_VALIDATION=<value>
export DOCUMENTWRITER_TOOL_ENABLE_SECURITY_SCAN=<value>
export DOCUMENTWRITER_TOOL_ENABLE_VERSIONING=<value>
export DOCUMENTWRITER_TOOL_GCS_BUCKET_NAME=<value>
export DOCUMENTWRITER_TOOL_GCS_PROJECT_ID=<value>
export DOCUMENTWRITER_TOOL_MAX_BACKUP_VERSIONS=<value>
export DOCUMENTWRITER_TOOL_MAX_FILE_SIZE=<value>
export DOCUMENTWRITER_TOOL_OUTPUT_DIR=<value>
export DOCUMENTWRITER_TOOL_SECURITY_SCAN=<value>
export DOCUMENTWRITER_TOOL_TEMP_DIR=<value>
export DOCUMENTWRITER_TOOL_TIMEOUT_SECONDS=<value>
export DOCUMENTWRITER_TOOL_VALIDATION_LEVEL=<value>
export DOCUMENTWRITER_TOOL_VERSION_CONTROL=<value>
```

---

## GraphReasoningTool

**配置字段数**: 5 (必需: 5, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | GRAPH_REASONING_DEFAULT_MAX_HOPS -> default_max_hops | ✅ | `-` | - |
| `default_confidence_threshold` | float | ✅ | `-` | - |
| `default_inference_max_steps` | int | ✅ | `-` | - |
| `default_max_hops` | int | ✅ | `-` | - |
| `enable_default_rules` | bool | ✅ | `-` | - |

### 配置示例

```python
graphreasoningtool_config = {
    'Example': None,
    'default_confidence_threshold': 0.0,
    'default_inference_max_steps': 0,
    'default_max_hops': 0,
    'enable_default_rules': False,
}
```

### 环境变量映射

```bash
export GRAPHREASONING_TOOL_EXAMPLE=<value>
export GRAPHREASONING_TOOL_DEFAULT_CONFIDENCE_THRESHOLD=<value>
export GRAPHREASONING_TOOL_DEFAULT_INFERENCE_MAX_STEPS=<value>
export GRAPHREASONING_TOOL_DEFAULT_MAX_HOPS=<value>
export GRAPHREASONING_TOOL_ENABLE_DEFAULT_RULES=<value>
```

---

## GraphSearchTool

**配置字段数**: 5 (必需: 5, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | GRAPH_SEARCH_CACHE_MAX_SIZE -> cache_max_size | ✅ | `-` | - |
| `cache_max_size` | int | ✅ | `-` | - |
| `cache_ttl` | int | ✅ | `-` | - |
| `default_max_depth` | int | ✅ | `-` | - |
| `default_max_results` | int | ✅ | `-` | - |

### 配置示例

```python
graphsearchtool_config = {
    'Example': None,
    'cache_max_size': 0,
    'cache_ttl': 0,
    'default_max_depth': 0,
    'default_max_results': 0,
}
```

### 环境变量映射

```bash
export GRAPHSEARCH_TOOL_EXAMPLE=<value>
export GRAPHSEARCH_TOOL_CACHE_MAX_SIZE=<value>
export GRAPHSEARCH_TOOL_CACHE_TTL=<value>
export GRAPHSEARCH_TOOL_DEFAULT_MAX_DEPTH=<value>
export GRAPHSEARCH_TOOL_DEFAULT_MAX_RESULTS=<value>
```

---

## ImageTool

**配置字段数**: 4 (必需: 4, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | IMAGE_TOOL_MAX_FILE_SIZE_MB -> max_file_size_mb | ✅ | `-` | - |
| `allowed_extensions` | List[str] | ✅ | `-` | - |
| `max_file_size_mb` | int | ✅ | `50` | Maximum file size in megabytes |
| `tesseract_pool_size` | int | ✅ | `2` | Number of Tesseract processes for OCR |

### 配置示例

```python
imagetool_config = {
    'Example': None,
    'allowed_extensions': "your_allowed_extensions",
    'max_file_size_mb': 50,  # Maximum file size in megabytes
    'tesseract_pool_size': 2,  # Number of Tesseract processes for OCR
}
```

### 环境变量映射

```bash
export IMAGE_TOOL_EXAMPLE=<value>
export IMAGE_TOOL_ALLOWED_EXTENSIONS=<value>
export IMAGE_TOOL_MAX_FILE_SIZE_MB=<value>
export IMAGE_TOOL_TESSERACT_POOL_SIZE=<value>
```

---

## KnowledgeGraphBuilderTool

**配置字段数**: 7 (必需: 7, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | KG_BUILDER_CHUNK_SIZE -> chunk_size | ✅ | `-` | - |
| `batch_size` | int | ✅ | `-` | - |
| `chunk_size` | int | ✅ | `-` | - |
| `enable_chunking` | bool | ✅ | `-` | - |
| `enable_deduplication` | bool | ✅ | `-` | - |
| `enable_linking` | bool | ✅ | `-` | - |
| `skip_errors` | bool | ✅ | `-` | - |

### 配置示例

```python
knowledgegraphbuildertool_config = {
    'Example': None,
    'batch_size': 0,
    'chunk_size': 0,
    'enable_chunking': False,
    'enable_deduplication': False,
    'enable_linking': False,
    'skip_errors': False,
}
```

### 环境变量映射

```bash
export KNOWLEDGEGRAPHBUILDER_TOOL_EXAMPLE=<value>
export KNOWLEDGEGRAPHBUILDER_TOOL_BATCH_SIZE=<value>
export KNOWLEDGEGRAPHBUILDER_TOOL_CHUNK_SIZE=<value>
export KNOWLEDGEGRAPHBUILDER_TOOL_ENABLE_CHUNKING=<value>
export KNOWLEDGEGRAPHBUILDER_TOOL_ENABLE_DEDUPLICATION=<value>
export KNOWLEDGEGRAPHBUILDER_TOOL_ENABLE_LINKING=<value>
export KNOWLEDGEGRAPHBUILDER_TOOL_SKIP_ERRORS=<value>
```

---

## ModelTrainerTool

**配置字段数**: 6 (必需: 6, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | MODEL_TRAINER_TEST_SIZE -> test_size | ✅ | `-` | - |
| `cv_folds` | int | ✅ | `5` | Number of cross-validation folds |
| `enable_hyperparameter_tuning` | bool | ✅ | `-` | - |
| `max_tuning_iterations` | int | ✅ | `-` | - |
| `random_state` | int | ✅ | `42` | Random state for reproducibility |
| `test_size` | float | ✅ | `0.2` | Proportion of data to use for testing |

### 配置示例

```python
modeltrainertool_config = {
    'Example': None,
    'cv_folds': 5,  # Number of cross-validation folds
    'enable_hyperparameter_tuning': False,
    'max_tuning_iterations': 0,
    'random_state': 42,  # Random state for reproducibility
    'test_size': 0.2,  # Proportion of data to use for testing
}
```

### 环境变量映射

```bash
export MODELTRAINER_TOOL_EXAMPLE=<value>
export MODELTRAINER_TOOL_CV_FOLDS=<value>
export MODELTRAINER_TOOL_ENABLE_HYPERPARAMETER_TUNING=<value>
export MODELTRAINER_TOOL_MAX_TUNING_ITERATIONS=<value>
export MODELTRAINER_TOOL_RANDOM_STATE=<value>
export MODELTRAINER_TOOL_TEST_SIZE=<value>
```

---

## OfficeTool

**配置字段数**: 6 (必需: 6, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | OFFICE_TOOL_MAX_FILE_SIZE_MB -> max_file_size_mb | ✅ | `-` | - |
| `allowed_extensions` | List[str] | ✅ | `-` | - |
| `default_font` | str | ✅ | `"Arial"` | Default font for documents |
| `default_font_size` | int | ✅ | `12` | Default font size in points |
| `max_file_size_mb` | int | ✅ | `100` | Maximum file size in megabytes |
| `tika_log_path` | str | ✅ | `-` | - |

### 配置示例

```python
officetool_config = {
    'Example': None,
    'allowed_extensions': "your_allowed_extensions",
    'default_font': "Arial",  # Default font for documents
    'default_font_size': 12,  # Default font size in points
    'max_file_size_mb': 100,  # Maximum file size in megabytes
    'tika_log_path': "your_tika_log_path",
}
```

### 环境变量映射

```bash
export OFFICE_TOOL_EXAMPLE=<value>
export OFFICE_TOOL_ALLOWED_EXTENSIONS=<value>
export OFFICE_TOOL_DEFAULT_FONT=<value>
export OFFICE_TOOL_DEFAULT_FONT_SIZE=<value>
export OFFICE_TOOL_MAX_FILE_SIZE_MB=<value>
export OFFICE_TOOL_TIKA_LOG_PATH=<value>
```

---

## PandasTool

**配置字段数**: 7 (必需: 7, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | PANDAS_TOOL_CSV_DELIMITER -> csv_delimiter | ✅ | `-` | - |
| `allowed_file_extensions` | List[str] | ✅ | `-` | - |
| `chunk_size` | int | ✅ | `10000` | Chunk size for large file processing |
| `csv_delimiter` | str | ✅ | `"` | Delimiter for CSV files |
| `default_agg` | Dict[str, str] | ✅ | `-` | - |
| `encoding` | str | ✅ | `"utf-8"` | Encoding for file operations |
| `max_csv_size` | int | ✅ | `1000000` | Threshold for chunked CSV processing |

### 配置示例

```python
pandastool_config = {
    'Example': None,
    'allowed_file_extensions': "your_allowed_file_extensions",
    'chunk_size': 10000,  # Chunk size for large file processing
    'csv_delimiter': ",  # Delimiter for CSV files
    'default_agg': "your_default_agg",
    'encoding': "utf-8",  # Encoding for file operations
    'max_csv_size': 1000000,  # Threshold for chunked CSV processing
}
```

### 环境变量映射

```bash
export PANDAS_TOOL_EXAMPLE=<value>
export PANDAS_TOOL_ALLOWED_FILE_EXTENSIONS=<value>
export PANDAS_TOOL_CHUNK_SIZE=<value>
export PANDAS_TOOL_CSV_DELIMITER=<value>
export PANDAS_TOOL_DEFAULT_AGG=<value>
export PANDAS_TOOL_ENCODING=<value>
export PANDAS_TOOL_MAX_CSV_SIZE=<value>
```

---

## ReportTool

**配置字段数**: 10 (必需: 10, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | REPORT_TOOL_TEMPLATES_DIR -> templates_dir | ✅ | `-` | - |
| `allowed_extensions` | List[str] | ✅ | `-` | - |
| `allowed_html_attributes` | Dict[str, List[str]] | ✅ | `-` | - |
| `allowed_html_tags` | Set[str] | ✅ | `-` | - |
| `default_font` | str | ✅ | `"Arial"` | Default font for documents |
| `default_font_size` | int | ✅ | `12` | Default font size in points |
| `default_output_dir` | str | ✅ | `-` | - |
| `pdf_page_size` | str | ✅ | `"A4"` | Default PDF page size |
| `temp_files_max_age` | int | ✅ | `-` | - |
| `templates_dir` | str | ✅ | `os.getcwd(` | Directory for Jinja2 templates |

### 配置示例

```python
reporttool_config = {
    'Example': None,
    'allowed_extensions': "your_allowed_extensions",
    'allowed_html_attributes': "your_allowed_html_attributes",
    'allowed_html_tags': "your_allowed_html_tags",
    'default_font': "Arial",  # Default font for documents
    'default_font_size': 12,  # Default font size in points
    'default_output_dir': "your_default_output_dir",
    'pdf_page_size': "A4",  # Default PDF page size
    'temp_files_max_age': 0,
    'templates_dir': os.getcwd(,  # Directory for Jinja2 templates
}
```

### 环境变量映射

```bash
export REPORT_TOOL_EXAMPLE=<value>
export REPORT_TOOL_ALLOWED_EXTENSIONS=<value>
export REPORT_TOOL_ALLOWED_HTML_ATTRIBUTES=<value>
export REPORT_TOOL_ALLOWED_HTML_TAGS=<value>
export REPORT_TOOL_DEFAULT_FONT=<value>
export REPORT_TOOL_DEFAULT_FONT_SIZE=<value>
export REPORT_TOOL_DEFAULT_OUTPUT_DIR=<value>
export REPORT_TOOL_PDF_PAGE_SIZE=<value>
export REPORT_TOOL_TEMP_FILES_MAX_AGE=<value>
export REPORT_TOOL_TEMPLATES_DIR=<value>
```

---

## ResearchTool

**配置字段数**: 5 (必需: 5, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | RESEARCH_TOOL_SPACY_MODEL -> spacy_model | ✅ | `-` | - |
| `allowed_spacy_models` | List[str] | ✅ | `-` | - |
| `max_text_length` | int | ✅ | `10_000` | Maximum text length for inputs |
| `max_workers` | int | ✅ | `-` | - |
| `spacy_model` | str | ✅ | `"en_core_web_sm"` | Default spaCy model to use |

### 配置示例

```python
researchtool_config = {
    'Example': None,
    'allowed_spacy_models': "your_allowed_spacy_models",
    'max_text_length': 10_000,  # Maximum text length for inputs
    'max_workers': 0,
    'spacy_model': "en_core_web_sm",  # Default spaCy model to use
}
```

### 环境变量映射

```bash
export RESEARCH_TOOL_EXAMPLE=<value>
export RESEARCH_TOOL_ALLOWED_SPACY_MODELS=<value>
export RESEARCH_TOOL_MAX_TEXT_LENGTH=<value>
export RESEARCH_TOOL_MAX_WORKERS=<value>
export RESEARCH_TOOL_SPACY_MODEL=<value>
```

---

## ScraperTool

**配置字段数**: 8 (必需: 8, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | SCRAPER_TOOL_USER_AGENT -> user_agent | ✅ | `-` | - |
| `allowed_domains` | List[str] | ✅ | `[]` | Allowed domains for scraping |
| `blocked_domains` | List[str] | ✅ | `[]` | Blocked domains for scraping |
| `max_content_length` | int | ✅ | `-` | - |
| `output_dir` | str | ✅ | `-` | - |
| `playwright_available` | bool | ✅ | `-` | - |
| `scrapy_command` | str | ✅ | `"scrapy"` | Command to run Scrapy |
| `user_agent` | str | ✅ | `-` | - |

### 配置示例

```python
scrapertool_config = {
    'Example': None,
    'allowed_domains': [],  # Allowed domains for scraping
    'blocked_domains': [],  # Blocked domains for scraping
    'max_content_length': 0,
    'output_dir': "your_output_dir",
    'playwright_available': False,
    'scrapy_command': "scrapy",  # Command to run Scrapy
    'user_agent': "your_user_agent",
}
```

### 环境变量映射

```bash
export SCRAPER_TOOL_EXAMPLE=<value>
export SCRAPER_TOOL_ALLOWED_DOMAINS=<value>
export SCRAPER_TOOL_BLOCKED_DOMAINS=<value>
export SCRAPER_TOOL_MAX_CONTENT_LENGTH=<value>
export SCRAPER_TOOL_OUTPUT_DIR=<value>
export SCRAPER_TOOL_PLAYWRIGHT_AVAILABLE=<value>
export SCRAPER_TOOL_SCRAPY_COMMAND=<value>
export SCRAPER_TOOL_USER_AGENT=<value>
```

---

## StatisticalAnalyzerTool

**配置字段数**: 4 (必需: 4, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | STATISTICAL_ANALYZER_SIGNIFICANCE_LEVEL -> significance_level | ✅ | `-` | - |
| `confidence_level` | float | ✅ | `-` | - |
| `enable_effect_size` | bool | ✅ | `-` | - |
| `significance_level` | float | ✅ | `-` | - |

### 配置示例

```python
statisticalanalyzertool_config = {
    'Example': None,
    'confidence_level': 0.0,
    'enable_effect_size': False,
    'significance_level': 0.0,
}
```

### 环境变量映射

```bash
export STATISTICALANALYZER_TOOL_EXAMPLE=<value>
export STATISTICALANALYZER_TOOL_CONFIDENCE_LEVEL=<value>
export STATISTICALANALYZER_TOOL_ENABLE_EFFECT_SIZE=<value>
export STATISTICALANALYZER_TOOL_SIGNIFICANCE_LEVEL=<value>
```

---

## StatsTool

**配置字段数**: 3 (必需: 3, 可选: 0)

| 字段名 | 类型 | 必需 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `Example` | STATS_TOOL_MAX_FILE_SIZE_MB -> max_file_size_mb | ✅ | `-` | - |
| `allowed_extensions` | List[str] | ✅ | `-` | - |
| `max_file_size_mb` | int | ✅ | `200` | Maximum file size in megabytes |

### 配置示例

```python
statstool_config = {
    'Example': None,
    'allowed_extensions': "your_allowed_extensions",
    'max_file_size_mb': 200,  # Maximum file size in megabytes
}
```

### 环境变量映射

```bash
export STATS_TOOL_EXAMPLE=<value>
export STATS_TOOL_ALLOWED_EXTENSIONS=<value>
export STATS_TOOL_MAX_FILE_SIZE_MB=<value>
```

---
