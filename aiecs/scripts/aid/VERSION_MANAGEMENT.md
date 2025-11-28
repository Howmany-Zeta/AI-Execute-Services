# AIECS 版本管理

AIECS 提供了一个统一的版本管理工具，可以同时更新项目中所有相关文件的版本号。

## 支持的文件

版本管理工具会自动更新以下文件中的版本号：

1. **`aiecs/__init__.py`** - 更新 `__version__` 变量
2. **`aiecs/main.py`** - 更新 FastAPI 应用版本和健康检查端点版本
3. **`pyproject.toml`** - 更新项目版本

## 使用方法

版本管理工具可以通过两种方式调用：

1. **推荐方式**：使用 `aiecs-version` 命令（更简洁）
2. **替代方式**：使用 Python 模块方式运行

### 1. 显示当前版本

**推荐方式：**
```bash
poetry run aiecs-version --show
```

**替代方式：**
```bash
poetry run python -m aiecs.scripts.aid.version_manager --show
```

### 2. 设置特定版本

**推荐方式：**
```bash
poetry run aiecs-version --version 1.2.0
```

**替代方式：**
```bash
poetry run python -m aiecs.scripts.aid.version_manager --version 1.2.0
```

### 3. 自动递增版本

#### 补丁版本 (Patch)
**推荐方式：**
```bash
poetry run aiecs-version --bump patch
# 1.1.0 -> 1.1.1
```

**替代方式：**
```bash
poetry run python -m aiecs.scripts.aid.version_manager --bump patch
# 1.1.0 -> 1.1.1
```

#### 次版本 (Minor)
**推荐方式：**
```bash
poetry run aiecs-version --bump minor
# 1.1.0 -> 1.2.0
```

**替代方式：**
```bash
poetry run python -m aiecs.scripts.aid.version_manager --bump minor
# 1.1.0 -> 1.2.0
```

#### 主版本 (Major)
**推荐方式：**
```bash
poetry run aiecs-version --bump major
# 1.1.0 -> 2.0.0
```

**替代方式：**
```bash
poetry run python -m aiecs.scripts.aid.version_manager --bump major
# 1.1.0 -> 2.0.0
```

## 版本号格式

版本号遵循 [语义化版本控制](https://semver.org/) 规范：

- **主版本号 (Major)**: 不兼容的API修改
- **次版本号 (Minor)**: 向下兼容的功能性新增
- **补丁版本号 (Patch)**: 向下兼容的问题修正

格式：`X.Y.Z` (例如：1.2.3)

## 命令行选项

- `--version, -v`: 设置特定版本号
- `--bump, -b`: 自动递增版本 (major/minor/patch)
- `--show, -s`: 显示当前版本
- `--help, -h`: 显示帮助信息

## 示例

```bash
# 查看当前版本（推荐方式）
poetry run aiecs-version --show

# 发布补丁版本
poetry run aiecs-version --bump patch

# 发布新功能版本
poetry run aiecs-version --bump minor

# 发布重大更新版本
poetry run aiecs-version --bump major

# 手动设置版本
poetry run aiecs-version --version 2.1.0

# 注意：也可以使用 Python 模块方式运行
# poetry run python -m aiecs.scripts.aid.version_manager --show
```

## 注意事项

1. 版本管理工具会自动验证版本号格式
2. 所有相关文件会同时更新，确保版本号一致性
3. 更新前建议先提交当前更改到版本控制系统
4. 工具会显示详细的更新日志，确认所有文件都已正确更新

## 故障排除

如果遇到问题，请检查：

1. 确保在项目根目录下运行命令
2. 确保所有目标文件存在且可写
3. 检查版本号格式是否正确 (X.Y.Z)
4. 确保没有其他进程正在编辑这些文件
