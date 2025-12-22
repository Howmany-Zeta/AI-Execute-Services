# APISource Tool Testing Guide

完整的 APISource Tool 和 API Providers 测试套件，包含真实 API 调用测试（无 mock）和详细的调试输出。

## 📋 目录

- [测试概述](#测试概述)
- [快速开始](#快速开始)
- [测试配置](#测试配置)
- [运行测试](#运行测试)
- [测试覆盖率](#测试覆盖率)
- [测试结构](#测试结构)
- [API 密钥配置](#api-密钥配置)
- [调试输出](#调试输出)

## 测试概述

### 测试特点

✅ **无 Mock 测试** - 测试真实的 API 调用和输出  
✅ **高覆盖率** - 目标覆盖率 > 85%  
✅ **详细调试** - 包含详细的 debug 输出，方便调试  
✅ **新框架** - 使用统一的测试框架结构  
✅ **Poetry 管理** - 所有命令使用 `poetry run`

### 测试范围

- ✓ APISourceTool 主工具类
- ✓ 所有 API Providers (FRED, World Bank, News API, Census)
- ✓ BaseAPIProvider 基类功能
- ✓ RateLimiter 速率限制器
- ✓ Provider 注册和发现机制
- ✓ 错误处理和异常
- ✓ 参数验证
- ✓ 配置管理
- ✓ 统计追踪

## 快速开始

### 1. 基本测试（不需要 API 密钥）

```bash
# 运行所有基本测试
poetry run pytest test/unit_tests/tools/test_apisource_tool.py -v -s

# 使用测试脚本
poetry run python test/scripts/run_apisource_coverage.py
```

### 2. 完整测试（需要 API 密钥）

```bash
# 设置环境变量
export FRED_API_KEY="your_fred_api_key"
export NEWSAPI_API_KEY="your_newsapi_api_key"
export CENSUS_API_KEY="your_census_api_key"  # 可选

# 运行包括网络测试
poetry run pytest test/unit_tests/tools/test_apisource_tool.py -v -s -m "network"
```

### 3. 查看覆盖率报告

```bash
# 生成覆盖率报告
poetry run pytest test/unit_tests/tools/test_apisource_tool.py \
    --cov=aiecs.tools.task_tools.apisource_tool \
    --cov=aiecs.tools.api_sources \
    --cov-report=html:test/coverage_reports/htmlcov_apisource \
    --cov-report=term-missing

# 在浏览器中打开报告
open test/coverage_reports/htmlcov_apisource/index.html
```

## 测试配置

### 环境变量

测试使用以下环境变量（可选）：

```bash
# FRED API (Federal Reserve Economic Data)
export FRED_API_KEY="your_key_here"
# 获取: https://fred.stlouisfed.org/docs/api/api_key.html

# News API
export NEWSAPI_API_KEY="your_key_here"
# 获取: https://newsapi.org/register

# US Census Bureau API (可选)
export CENSUS_API_KEY="your_key_here"
# 获取: https://api.census.gov/data/key_signup.html
```

### pytest 配置

测试使用 `test/configs/pytest.ini` 中的配置：

- 最小覆盖率: 85%
- 超时: 300 秒
- 日志级别: INFO
- 标记: slow, integration, network

## 运行测试

### 使用 pytest 直接运行

```bash
# 运行所有测试
poetry run pytest test/unit_tests/tools/test_apisource_tool.py -v

# 运行特定测试类
poetry run pytest test/unit_tests/tools/test_apisource_tool.py::TestAPISourceToolInitialization -v

# 运行特定测试方法
poetry run pytest test/unit_tests/tools/test_apisource_tool.py::TestAPISourceToolInitialization::test_default_initialization -v

# 显示打印输出（调试模式）
poetry run pytest test/unit_tests/tools/test_apisource_tool.py -v -s

# 运行带标记的测试
poetry run pytest test/unit_tests/tools/test_apisource_tool.py -v -m "network"
poetry run pytest test/unit_tests/tools/test_apisource_tool.py -v -m "not slow"
```

### 使用测试脚本运行

```bash
# 基本测试
poetry run python test/scripts/run_apisource_coverage.py

# 包括网络测试
poetry run python test/scripts/run_apisource_coverage.py --network

# 运行所有测试（包括慢速测试）
poetry run python test/scripts/run_apisource_coverage.py --all

# 详细输出
poetry run python test/scripts/run_apisource_coverage.py -v
```

## 测试覆盖率

### 覆盖率目标

- **总体覆盖率**: > 85%
- **APISourceTool**: > 90%
- **每个 Provider**: > 85%
- **BaseAPIProvider**: > 90%

### 查看覆盖率

```bash
# 终端输出
poetry run pytest test/unit_tests/tools/test_apisource_tool.py \
    --cov=aiecs.tools.task_tools.apisource_tool \
    --cov=aiecs.tools.api_sources \
    --cov-report=term-missing

# HTML 报告
poetry run pytest test/unit_tests/tools/test_apisource_tool.py \
    --cov=aiecs.tools.task_tools.apisource_tool \
    --cov=aiecs.tools.api_sources \
    --cov-report=html:test/coverage_reports/htmlcov_apisource

# XML 报告（用于 CI）
poetry run pytest test/unit_tests/tools/test_apisource_tool.py \
    --cov=aiecs.tools.task_tools.apisource_tool \
    --cov=aiecs.tools.api_sources \
    --cov-report=xml
```

## 测试结构

### 测试类组织

```
test_apisource_tool.py
├── TestRateLimiter                    # 速率限制器测试
├── TestBaseAPIProvider                # 基础 Provider 测试
├── TestProviderRegistry               # Provider 注册测试
├── TestFREDProvider                   # FRED Provider 测试
├── TestWorldBankProvider              # World Bank Provider 测试
├── TestNewsAPIProvider                # News API Provider 测试
├── TestCensusProvider                 # Census Provider 测试
├── TestAPISourceToolInitialization    # 工具初始化测试
├── TestAPISourceToolOperations        # 工具操作测试
├── TestAPISourceToolSchemas           # Schema 验证测试
├── TestAPISourceToolExceptions        # 异常处理测试
├── TestProviderOperations             # Provider 操作测试
├── TestProviderErrorHandling          # 错误处理测试
├── TestProviderConfiguration          # 配置测试
├── TestIntegrationScenarios           # 集成场景测试
├── TestEdgeCases                      # 边界情况测试
└── TestCoverageCompleteness           # 覆盖率完整性测试
```

### 测试数量统计

- **总测试数**: 60+
- **基础功能测试**: 20+
- **Provider 测试**: 20+
- **集成测试**: 10+
- **边界测试**: 10+

## API 密钥配置

### 获取 API 密钥

#### FRED API
1. 访问: https://fred.stlouisfed.org/
2. 注册账号
3. 申请 API Key: https://fred.stlouisfed.org/docs/api/api_key.html
4. 免费，无需信用卡

#### News API
1. 访问: https://newsapi.org/
2. 注册账号: https://newsapi.org/register
3. 获取 API Key
4. 免费层级: 100 请求/天

#### Census API
1. 访问: https://www.census.gov/data/developers.html
2. 申请 API Key: https://api.census.gov/data/key_signup.html
3. 免费，大部分数据集不需要 Key

### 配置方式

#### 方式 1: 环境变量

```bash
# 在 ~/.bashrc 或 ~/.zshrc 中添加
export FRED_API_KEY="your_key"
export NEWSAPI_API_KEY="your_key"
export CENSUS_API_KEY="your_key"
```

#### 方式 2: .env 文件

```bash
# 创建 .env 文件
cat > .env << EOF
FRED_API_KEY=your_key
NEWSAPI_API_KEY=your_key
CENSUS_API_KEY=your_key
EOF

# 使用 python-dotenv 加载
poetry add python-dotenv
```

#### 方式 3: 测试配置

```python
# 在测试中直接配置
tool = APISourceTool(config={
    'fred_api_key': 'your_key',
    'newsapi_api_key': 'your_key',
    'census_api_key': 'your_key'
})
```

## 调试输出

### 调试功能

测试包含详细的调试输出，包括：

- ✓ 测试步骤说明
- ✓ 输入参数
- ✓ API 响应数据
- ✓ 错误信息
- ✓ 统计信息
- ✓ 配置详情

### 查看调试输出

```bash
# 使用 -s 标志显示所有打印输出
poetry run pytest test/unit_tests/tools/test_apisource_tool.py -v -s

# 只运行特定测试并查看输出
poetry run pytest test/unit_tests/tools/test_apisource_tool.py::TestFREDProvider::test_fred_real_api_call -v -s
```

### 调试输出示例

```
================================================================================
  Testing FRED Provider Initialization
================================================================================

Provider name: fred
Description: Federal Reserve Economic Data API for US economic indicators and time series
Supported operations: ['get_series', 'search_series', 'get_series_observations', ...]
✓ FRED provider initialized successfully
```

## 故障排除

### 常见问题

#### 1. API 密钥错误

```
Error: FRED API key not found
```

**解决方案**: 设置环境变量或在配置中提供 API 密钥

#### 2. 网络连接错误

```
Error: requests.exceptions.ConnectionError
```

**解决方案**: 检查网络连接，或跳过网络测试 `-m "not network"`

#### 3. 覆盖率不足

```
FAILED: coverage < 85%
```

**解决方案**: 查看覆盖率报告，添加缺失的测试用例

#### 4. 速率限制

```
Error: Rate limit exceeded
```

**解决方案**: 等待一段时间后重试，或调整速率限制配置

## 持续集成

### GitHub Actions 示例

```yaml
name: APISource Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      
      - name: Run tests
        env:
          FRED_API_KEY: ${{ secrets.FRED_API_KEY }}
          NEWSAPI_API_KEY: ${{ secrets.NEWSAPI_API_KEY }}
        run: |
          poetry run python test/scripts/run_apisource_coverage.py
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./coverage.xml
```

## 贡献指南

### 添加新测试

1. 在相应的测试类中添加测试方法
2. 使用 `print_section()` 和 `print_result()` 添加调试输出
3. 确保测试覆盖新功能
4. 运行测试验证覆盖率

### 测试命名规范

- 测试类: `Test<ComponentName>`
- 测试方法: `test_<功能描述>`
- 使用描述性名称

### 代码风格

- 遵循 PEP 8
- 添加文档字符串
- 使用类型提示
- 添加注释说明复杂逻辑

## 参考资料

- [APISource Tool 文档](../../../aiecs/tools/task_tools/apisource_tool.py)
- [API Providers 文档](../../../aiecs/tools/api_sources/)
- [pytest 文档](https://docs.pytest.org/)
- [Coverage.py 文档](https://coverage.readthedocs.io/)

