# KAG 配置文件集中管理

本目录用于集中管理所有KAG相关的YAML配置文件。

## 目录结构

```
kag_configs/
├── README.md                          # 本说明文件
└── solver/                           # 求解器配置
    └── pipelineconf/                 # 管道配置文件
        ├── deep_thought.yaml         # 深度思考管道配置
        ├── mcp.yaml                  # MCP管道配置
        ├── naive_rag.yaml            # 简单RAG管道配置
        └── self_cognition.yaml       # 自认知管道配置
```

## 配置文件说明

### 求解器管道配置 (solver/pipelineconf/)

这些配置文件定义了不同类型的KAG求解器管道：

- **deep_thought.yaml**: 深度思考管道，使用复杂的推理流程
- **mcp.yaml**: MCP (Model Context Protocol) 管道配置
- **naive_rag.yaml**: 简单的RAG (Retrieval-Augmented Generation) 管道
- **self_cognition.yaml**: 自认知管道，具有自我反思能力

## 使用方式

### 在代码中引用配置

配置文件会被 `app/services/domain/kag_core/solver/main_solver.py` 中的 `load_yaml_files_from_conf_dir()` 函数自动加载。

```python
# 配置文件会自动从以下路径加载：
# app/services/domain/kag_configs/solver/pipelineconf/
```

### 添加新配置

1. 在相应的子目录下创建新的YAML文件
2. 确保配置文件包含必要的 `pipeline_name` 字段
3. 按照现有配置文件的格式编写配置

### 修改配置

直接编辑对应的YAML文件即可，修改会在下次加载时生效。

## 配置文件格式

所有配置文件都应该包含以下基本结构：

```yaml
#------------kag-solver configuration start----------------#
pipeline_name: your_pipeline_name

# 配置内容...

#------------kag-solver configuration end----------------#
```

## 迁移说明

这些配置文件原本位于 `app/services/domain/kag_core/solver/pipelineconf/` 目录下，为了更好的配置管理，已迁移到当前目录。

相关的代码引用已经更新，无需手动修改。

## 注意事项

1. 修改配置文件时请保持YAML格式的正确性
2. 新增配置文件时请确保文件名具有描述性
3. 重要配置修改前建议备份原文件
4. 配置文件中的路径引用应使用相对路径

## 版本历史

- **v1.0** (2025-06-03): 初始版本，从 kag_core 目录迁移配置文件
