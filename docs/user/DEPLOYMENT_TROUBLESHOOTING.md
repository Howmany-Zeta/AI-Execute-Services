# AIECS 部署故障排除指南

## 📋 常见问题

### 问题：pip 安装警告 - 脚本不在 PATH 中

**症状：**
```
WARNING: The scripts aiecs, aiecs-check-deps, aiecs-check-modules, ... are installed in '/tmp/.local/bin' which is not on PATH.
Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
```

**原因：**
当在容器中使用 `pip install --user` 或设置了 `PIP_USER=1` 环境变量时，pip 会将包和脚本安装到用户目录（通常是 `~/.local`），但该目录可能不在 PATH 环境变量中。

**解决方案：**

#### 方案 1：将用户 bin 目录添加到 PATH（推荐）

在 Dockerfile 中添加以下行：

```dockerfile
# 在安装 aiecs 之前或之后添加
ENV PATH="${PATH}:/root/.local/bin"

# 如果使用非 root 用户，使用对应的用户目录
ENV PATH="${PATH}:/home/youruser/.local/bin"
```

**完整示例：**

```dockerfile
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PIP_USER=1 \
    PATH="${PATH}:/root/.local/bin"

# 安装 aiecs
RUN pip install --user aiecs

# 验证安装
RUN aiecs-version
```

#### 方案 2：使用系统级安装（容器推荐）

在容器中，通常不需要使用 `--user` 安装，可以直接进行系统级安装：

```dockerfile
FROM python:3.11-slim

# 不设置 PIP_USER，使用系统级安装
RUN pip install aiecs

# 脚本会自动安装到 /usr/local/bin，已在 PATH 中
RUN aiecs-version
```

#### 方案 3：在运行时添加 PATH

如果无法修改 Dockerfile，可以在运行时设置：

```bash
# 在 docker run 中
docker run -e PATH="${PATH}:/root/.local/bin" your-image

# 或在 docker-compose.yml 中
services:
  your-service:
    environment:
      - PATH=${PATH}:/root/.local/bin
```

#### 方案 4：使用 Python 模块方式调用（无需 PATH）

如果只需要使用功能而不需要命令行工具，可以直接使用 Python 模块：

```python
# 不使用命令行工具
# aiecs-version  # ❌ 需要 PATH

# 使用 Python 模块
python -m aiecs.scripts.aid.version_manager  # ✅ 不需要 PATH
```

**验证修复：**

```bash
# 检查 PATH
echo $PATH

# 检查脚本位置
which aiecs
which aiecs-version

# 测试命令
aiecs-version
aiecs-check-deps
```

### 问题：容器中找不到 aiecs 命令

**症状：**
```bash
bash: aiecs: command not found
```

**解决方案：**

1. **检查安装位置：**
```bash
# 查找脚本位置
find / -name "aiecs" -type f 2>/dev/null

# 检查 pip 安装位置
pip show -f aiecs | grep Location
```

2. **添加到 PATH：**
```bash
# 临时添加（当前会话）
export PATH="${PATH}:$(python -m site --user-base)/bin"

# 永久添加（在 Dockerfile 中）
ENV PATH="${PATH}:$(python -m site --user-base)/bin"
```

3. **使用完整路径：**
```bash
# 直接使用完整路径
/root/.local/bin/aiecs-version
```

### 问题：多用户容器环境

如果容器中有多个用户，需要为每个用户设置 PATH：

```dockerfile
# 为所有用户设置
RUN echo 'export PATH="${PATH}:${HOME}/.local/bin"' >> /etc/profile

# 或为特定用户设置
USER youruser
RUN echo 'export PATH="${PATH}:${HOME}/.local/bin"' >> ~/.bashrc
```

### 最佳实践建议

1. **容器部署：** 使用系统级安装（不使用 `--user`）
   ```dockerfile
   RUN pip install aiecs
   ```

2. **开发环境：** 可以使用 `--user` 安装，但记得设置 PATH
   ```bash
   pip install --user aiecs
   export PATH="${PATH}:$(python -m site --user-base)/bin"
   ```

3. **CI/CD 环境：** 在构建脚本中设置 PATH
   ```yaml
   # GitHub Actions 示例
   - name: Install aiecs
     run: |
       pip install --user aiecs
       echo "$(python -m site --user-base)/bin" >> $GITHUB_PATH
   ```

## 🔍 其他常见问题

### 权限问题

如果遇到权限错误：

```bash
# 检查权限
ls -la ~/.local/bin/aiecs*

# 修复权限（如果需要）
chmod +x ~/.local/bin/aiecs*
```

### 虚拟环境问题

在虚拟环境中，脚本会自动安装到虚拟环境的 bin 目录：

```bash
# 激活虚拟环境后，脚本自动可用
source venv/bin/activate
pip install aiecs
aiecs-version  # ✅ 自动可用
```

## 📚 相关文档

- [Docker 部署指南](./TOOLS_USED_INSTRUCTION/DOCKER_DEPLOYMENT.md)
- [安装说明](../README.md)

## 💡 需要帮助？

如果以上方案都无法解决问题，请：

1. 检查 Python 和 pip 版本
2. 检查容器的基础镜像
3. 查看完整的错误日志
4. 在 GitHub Issues 中报告问题

