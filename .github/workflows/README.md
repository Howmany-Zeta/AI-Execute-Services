# GitHub Actions Workflows

这个目录包含了 AIECS 项目的自动化发布工作流。

## 📋 工作流文件

### 1. `publish-to-testpypi.yml`
**用途**: 自动发布到 TestPyPI  
**触发条件**: 
- 推送以 `v` 开头的标签 (如 `v1.0.0`, `v1.0.1`)
- 手动触发

**功能**:
- 清理之前的构建文件
- 构建 wheel 和 source distribution
- 验证包的完整性
- 发布到 TestPyPI
- 测试从 TestPyPI 安装

### 2. `publish-to-pypi.yml`
**用途**: 自动发布到正式 PyPI  
**触发条件**: 
- 创建正式 GitHub Release
- 手动触发

**功能**:
- 清理之前的构建文件
- 构建 wheel 和 source distribution
- 验证包的完整性
- 发布到正式 PyPI
- 测试从 PyPI 安装

## 🔧 配置 Trusted Publisher

要使用这些工作流，您需要在 PyPI 和 TestPyPI 上配置 Trusted Publisher：

### TestPyPI 配置
1. 访问 [https://test.pypi.org/](https://test.pypi.org/)
2. 登录并进入项目设置
3. 添加 Trusted Publisher:
   - **Repository owner**: `Howmany-Zeta`
   - **Repository name**: `AI-Execute-Servicese-Service`
   - **Workflow filename**: `publish-to-testpypi.yml`
   - **Environment name**: `testpypi`

### PyPI 配置
1. 访问 [https://pypi.org/](https://pypi.org/)
2. 登录并进入项目设置
3. 添加 Trusted Publisher:
   - **Repository owner**: `Howmany-Zeta`
   - **Repository name**: `AI-Execute-Servicese-Service`
   - **Workflow filename**: `publish-to-pypi.yml`
   - **Environment name**: `pypi`

## 🚀 使用方法

### 发布到 TestPyPI
```bash
# 创建并推送标签
git tag v1.0.0
git push origin v1.0.0
```

### 发布到正式 PyPI
1. 在 GitHub 上创建 Release
2. 选择标签 (如 `v1.0.0`)
3. 填写 Release 说明
4. 点击 "Publish release"

### 手动触发
1. 进入 GitHub Actions 页面
2. 选择对应的工作流
3. 点击 "Run workflow"

## 📦 环境配置

工作流使用了 GitHub Environments 来管理发布权限：

- **testpypi**: 用于 TestPyPI 发布
- **pypi**: 用于正式 PyPI 发布

您可以在 GitHub 仓库设置中配置这些环境的保护规则。

## 🔍 监控发布

- 查看 GitHub Actions 页面监控发布状态
- 检查 TestPyPI/PyPI 上的包页面
- 验证包的安装和功能

## ⚠️ 注意事项

1. **版本号**: 确保每次发布使用不同的版本号
2. **测试**: 建议先发布到 TestPyPI 测试
3. **权限**: 确保 GitHub 仓库有正确的 Trusted Publisher 配置
4. **环境**: 配置适当的 GitHub Environments 保护规则
