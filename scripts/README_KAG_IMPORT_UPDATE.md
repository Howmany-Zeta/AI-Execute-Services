# KAG导入路径更新脚本使用说明

本文档说明如何使用KAG导入路径更新脚本来处理KAG项目集成和更新。

## 脚本文件

1. **`rename_kag_imports.py`** - 简单的重命名脚本，用于一次性导入路径替换
2. **`update_kag_imports.py`** - 高级更新脚本，支持配置文件和多种选项
3. **`kag_update_config.json`** - 配置文件示例

## 快速开始

### 1. 基本用法（简单脚本）

```bash
# 重命名 kag_core 目录下的所有导入路径
python3 scripts/rename_kag_imports.py app/services/domain/kag_core
```

### 2. 高级用法（配置脚本）

```bash
# 使用默认设置更新导入路径
python3 scripts/update_kag_imports.py --directory app/services/domain/kag_core

# 自定义源路径和目标路径
python3 scripts/update_kag_imports.py \
  --source-path kag \
  --target-path app.services.domain.kag_core \
  --directory app/services/domain/kag_core

# 使用配置文件
python3 scripts/update_kag_imports.py --config scripts/kag_update_config.json --directory app/services/domain/kag_core

# 试运行模式（查看将要进行的更改，不实际修改文件）
python3 scripts/update_kag_imports.py --directory app/services/domain/kag_core --dry-run
```

## 配置文件格式

配置文件使用JSON格式，支持多个替换规则：

```json
{
  "rules": [
    {
      "pattern": "\\bfrom kag\\.",
      "replacement": "from app.services.domain.kag_core.",
      "description": "KAG核心模块导入路径重命名"
    },
    {
      "pattern": "\\bimport kag\\.",
      "replacement": "import app.services.domain.kag_core.",
      "description": "KAG模块直接导入重命名"
    }
  ],
  "exclude_patterns": [
    "knext\\.",
    "__pycache__",
    "\\.pyc$"
  ],
  "description": "KAG项目导入路径更新配置"
}
```

### 配置字段说明

- **`rules`**: 替换规则数组
  - `pattern`: 正则表达式模式（需要转义反斜杠）
  - `replacement`: 替换字符串
  - `description`: 规则描述（可选）
- **`exclude_patterns`**: 排除模式数组（暂未实现）
- **`description`**: 配置文件描述

## 常见使用场景

### 场景1: 初次集成KAG项目

当首次将KAG代码复制到项目中时：

```bash
# 1. 复制KAG代码到 app/services/domain/kag_core/
# 2. 运行重命名脚本
python3 scripts/rename_kag_imports.py app/services/domain/kag_core
```

### 场景2: KAG项目更新

当需要更新KAG代码时：

```bash
# 1. 备份当前的 kag_core 目录
cp -r app/services/domain/kag_core app/services/domain/kag_core.backup

# 2. 复制新的KAG代码
# 3. 使用配置文件进行更新
python3 scripts/update_kag_imports.py --config scripts/kag_update_config.json --directory app/services/domain/kag_core

# 4. 验证更改
python3 scripts/update_kag_imports.py --config scripts/kag_update_config.json --directory app/services/domain/kag_core --dry-run
```

### 场景3: 自定义导入路径

如果需要将KAG集成到不同的路径：

```bash
# 将 kag 重命名为 my_project.ai.kag_engine
python3 scripts/update_kag_imports.py \
  --source-path kag \
  --target-path my_project.ai.kag_engine \
  --directory my_project/ai/kag_engine
```

## 验证更新结果

### 1. 检查是否还有遗漏的导入

```bash
# 在 kag_core 目录下搜索是否还有 'from kag.' 导入
grep -r "from kag\." app/services/domain/kag_core/
```

### 2. 检查 knext 导入是否保持不变

```bash
# 确认 knext 导入没有被误改
grep -r "from knext\." app/services/domain/kag_core/
```

### 3. 语法检查

```bash
# 使用 Python 检查语法错误
python3 -m py_compile app/services/domain/kag_core/**/*.py
```

## 注意事项

1. **备份重要**: 在运行脚本前，请务必备份原始代码
2. **试运行**: 使用 `--dry-run` 参数先查看将要进行的更改
3. **knext保护**: 脚本会自动保护 `knext` 相关的导入不被修改
4. **正则表达式**: 配置文件中的正则表达式需要转义反斜杠
5. **编码**: 脚本使用 UTF-8 编码处理文件

## 故障排除

### 问题1: 脚本执行失败

```bash
# 检查 Python 版本
python3 --version

# 检查文件权限
ls -la scripts/update_kag_imports.py

# 添加执行权限
chmod +x scripts/update_kag_imports.py
```

### 问题2: 导入路径错误

如果发现导入路径不正确，可以手动修正配置文件中的 `pattern` 和 `replacement` 字段。

### 问题3: 文件编码问题

如果遇到编码问题，确保所有Python文件都使用UTF-8编码。

## 扩展功能

### 生成新的配置文件

```bash
# 生成默认配置文件
python3 scripts/update_kag_imports.py --generate-config my_config.json
```

### 批量处理多个目录

可以编写shell脚本来批量处理多个目录：

```bash
#!/bin/bash
directories=(
  "app/services/domain/kag_core"
  "app/services/domain/kag_extensions"
)

for dir in "${directories[@]}"; do
  echo "Processing $dir..."
  python3 scripts/update_kag_imports.py --directory "$dir"
done
```

## 版本历史

- **v1.0** (2025-06-03): 初始版本，支持基本的导入路径重命名
- 支持配置文件和试运行模式
- 自动保护 knext 导入不被修改

## 联系支持

如果在使用过程中遇到问题，请检查：
1. Python版本是否为3.6+
2. 文件路径是否正确
3. 配置文件格式是否正确
4. 是否有足够的文件权限
