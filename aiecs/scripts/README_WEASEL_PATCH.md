# Weasel Library Patch Scripts

这个目录包含用于修复weasel库重复验证器函数错误的脚本，该错误导致测试失败。

## 问题描述

错误发生是因为weasel库中有重复的验证器函数，但没有`allow_reuse=True`参数：

```
pydantic.v1.errors.ConfigError: duplicate validator function "weasel.schemas.ProjectConfigSchema.check_legacy_keys"; if this is intended, set `allow_reuse=True`
```

**注意**: 实际的问题是在 `@root_validator` 装饰器中，而不是 `@validator`。

## 可用脚本

### 1. `run_weasel_patch.sh` (推荐使用)
最简单的解决方案，通过poetry运行补丁：
- 自动检测poetry虚拟环境
- 在正确的环境中运行Python补丁脚本
- 提供清晰的反馈和说明

**使用方法:**
```bash
cd python-middleware
./scripts/run_weasel_patch.sh
```

### 2. `fix_weasel_validator.py`
基于Python的方法：
- 使用正则表达式模式识别和修复验证器装饰器
- 提供详细的前后对比
- 创建带时间戳的备份

**使用方法:**
```bash
cd python-middleware
poetry run python3 ./scripts/fix_weasel_validator.py
```

### 3. `fix_weasel_validator.sh`
基于bash的方法，使用sed进行文本替换：
- 简单的sed文本替换
- 创建备份
- 显示前后内容

**使用方法:**
```bash
cd python-middleware
./scripts/fix_weasel_validator.sh
```

### 4. `patch_weasel_library.sh`
综合解决方案：
- 结合多种方法
- 包含测试验证
- 详细的错误处理

**使用方法:**
```bash
cd python-middleware
./scripts/patch_weasel_library.sh
```

## 脚本功能

所有脚本都执行以下操作：

1. **定位虚拟环境**: 找到poetry虚拟环境路径
2. **找到问题文件**: 在site-packages中定位`weasel/schemas.py`
3. **创建备份**: 制作原始文件的带时间戳备份
4. **应用补丁**: 向需要的验证器装饰器添加`allow_reuse=True`
5. **验证修复**: 检查补丁是否正确应用

## 修复内容

脚本将以下代码：
```python
@root_validator(pre=True)
def check_legacy_keys(cls, obj: Dict[str, Any]) -> Dict[str, Any]:
```

修改为：
```python
@root_validator(pre=True, allow_reuse=True)
def check_legacy_keys(cls, obj: Dict[str, Any]) -> Dict[str, Any]:
```

脚本同时支持 `@validator` 和 `@root_validator` 装饰器的修复。

## 回滚

如果需要恢复更改，每个脚本都会创建备份文件。您可以使用以下命令恢复：
```bash
cp /path/to/backup/file /path/to/original/schemas.py
```

确切的路径将在脚本输出中显示。

## 故障排除

1. **找不到Poetry**: 确保已安装poetry并且您在项目目录中
2. **找不到虚拟环境**: 运行`poetry install`创建虚拟环境
3. **找不到文件**: weasel包可能未安装 - 检查您的依赖项
4. **权限错误**: 您可能需要使用适当的权限运行

## 运行补丁后

1. 再次尝试运行您的测试：`poetry run pytest`
2. 如果问题仍然存在，重启您的Python环境/IDE
3. 修复应该解决重复验证器函数错误

## 注意事项

- 这些脚本可以安全地多次运行
- 它们在进行更改之前检查补丁是否已应用
- 所有更改都会自动备份
- 脚本针对特定问题，不会影响其他功能

## 推荐使用流程

1. 首先尝试使用 `run_weasel_patch.sh`（最简单）
2. 如果遇到问题，可以尝试直接运行 `poetry run python3 scripts/fix_weasel_validator.py`
3. 作为最后手段，可以使用 `patch_weasel_library.sh`（最全面）

所有脚本都会在修改前创建备份，因此您可以安全地尝试不同的方法。
