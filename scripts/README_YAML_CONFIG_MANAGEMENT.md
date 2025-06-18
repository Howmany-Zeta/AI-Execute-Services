# KAG YAML配置文件集中管理脚本使用说明

本文档说明如何使用YAML配置文件移动脚本来实现KAG项目的配置集中管理。

## 脚本文件

- **`scripts/move_yaml_configs.py`** - YAML配置文件移动和集中管理脚本

## 功能特性

### 1. 自动发现YAML文件
- 递归搜索指定目录下的所有 `.yaml` 和 `.yml` 文件
- 保持原有的目录结构

### 2. 智能路径更新
- 自动查找和更新Python代码中的YAML文件引用
- 支持多种引用模式的识别和替换

### 3. 安全操作
- 支持试运行模式，预览将要进行的操作
- 自动备份和确认机制

### 4. 清理功能
- 自动清理移动后的空目录
- 保持代码库整洁

## 使用方法

### 基本用法

```bash
# 移动kag_core中的YAML文件到kag_configs目录
python3 scripts/move_yaml_configs.py --source app/services/domain/kag_core --target app/services/domain/kag_configs
```

### 试运行模式

```bash
# 查看将要进行的操作，不实际移动文件
python3 scripts/move_yaml_configs.py --source app/services/domain/kag_core --target app/services/domain/kag_configs --dry-run
```

### 自定义路径

```bash
# 指定自定义的源目录和目标目录
python3 scripts/move_yaml_configs.py --source /path/to/source --target /path/to/target
```

## 实际执行结果

### 移动的文件

以下YAML配置文件已成功移动到集中管理目录：

```
app/services/domain/kag_configs/
└── solver/
    └── pipelineconf/
        ├── deep_thought.yaml      # 深度思考管道配置
        ├── mcp.yaml              # MCP管道配置
        ├── naive_rag.yaml        # 简单RAG管道配置
        └── self_cognition.yaml   # 自认知管道配置
```

### 更新的代码引用

- **`app/services/domain/kag_core/solver/main_solver.py`**: 更新了 `load_yaml_files_from_conf_dir()` 函数中的配置目录路径

## 配置文件说明

### 1. deep_thought.yaml
深度思考管道配置，包含：
- 知识图谱概念搜索 (kg_cs)
- 知识图谱自由检索 (kg_fr)
- 检索内容合并 (rc)
- 混合执行器配置
- LLM生成器配置

### 2. mcp.yaml
MCP (Model Context Protocol) 管道配置

### 3. naive_rag.yaml
简单RAG管道配置，适用于基础的检索增强生成场景

### 4. self_cognition.yaml
自认知管道配置，具有自我反思和认知能力

## 配置管理最佳实践

### 1. 目录结构
```
kag_configs/
├── README.md                    # 配置说明文档
└── solver/                     # 求解器相关配置
    └── pipelineconf/           # 管道配置文件
        ├── *.yaml              # 各种管道配置
        └── custom/             # 自定义配置（可选）
```

### 2. 命名规范
- 使用描述性的文件名
- 采用小写字母和下划线
- 包含功能或用途信息

### 3. 配置格式
```yaml
#------------kag-solver configuration start----------------#
pipeline_name: your_pipeline_name

# 配置内容
key: value

#------------kag-solver configuration end----------------#
```

### 4. 版本控制
- 重要配置修改前先备份
- 使用Git跟踪配置文件变更
- 添加有意义的提交信息

## 故障排除

### 问题1: 配置文件加载失败

**症状**: 程序运行时提示找不到配置文件

**解决方案**:
1. 检查配置文件路径是否正确
2. 验证 `main_solver.py` 中的路径更新是否正确
3. 确认配置文件格式是否有效

### 问题2: 路径引用未更新

**症状**: 代码中仍然引用旧的配置文件路径

**解决方案**:
1. 手动搜索并更新遗漏的引用
2. 使用IDE的全局搜索功能查找 "pipelineconf"
3. 检查相对路径和绝对路径的使用

### 问题3: 权限问题

**症状**: 无法移动或创建文件

**解决方案**:
```bash
# 检查文件权限
ls -la app/services/domain/

# 修改权限（如需要）
chmod 755 app/services/domain/kag_configs/
```

## 扩展功能

### 1. 添加新配置类型

如需支持其他类型的配置文件：

```python
# 在脚本中添加新的文件模式
patterns = ['*.yaml', '*.yml', '*.json', '*.toml']
```

### 2. 自定义引用模式

如需识别特殊的引用模式：

```python
# 在 find_yaml_references 方法中添加新模式
patterns.append(r'your_custom_pattern')
```

### 3. 批量操作

```bash
# 创建批量处理脚本
for dir in dir1 dir2 dir3; do
    python3 scripts/move_yaml_configs.py --source $dir --target configs/$dir
done
```

## 集成到CI/CD

### 配置验证脚本

```bash
#!/bin/bash
# validate_configs.sh

echo "验证YAML配置文件..."
for file in app/services/domain/kag_configs/**/*.yaml; do
    python3 -c "import yaml; yaml.safe_load(open('$file'))" || exit 1
done
echo "所有配置文件验证通过"
```

### 自动化部署

```yaml
# .github/workflows/deploy.yml
- name: Validate Configurations
  run: |
    python3 scripts/validate_yaml_configs.py

- name: Deploy Configurations
  run: |
    rsync -av app/services/domain/kag_configs/ $DEPLOY_PATH/configs/
```

## 版本历史

- **v1.0** (2025-06-03): 初始版本
  - 支持YAML文件自动发现和移动
  - 智能路径引用更新
  - 试运行模式
  - 空目录清理

## 相关文档

- [KAG配置文件说明](../app/services/domain/kag_configs/README.md)
- [KAG导入路径更新说明](./README_KAG_IMPORT_UPDATE.md)
