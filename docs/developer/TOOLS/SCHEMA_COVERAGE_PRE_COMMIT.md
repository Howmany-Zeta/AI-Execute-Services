# Schema Coverage Pre-commit Hook

## Overview

The schema coverage pre-commit hook ensures that all tools maintain schema coverage above a specified threshold (default: 90%) before code is committed.

## Setup

### Option 1: Using pre-commit Framework (Recommended)

1. Install pre-commit:
```bash
pip install pre-commit
```

2. Install the hooks:
```bash
pre-commit install
```

3. The hook will automatically run before each commit. To run manually:
```bash
pre-commit run --all-files
```

### Option 2: Using Standalone Script

1. Copy the script to `.git/hooks/pre-commit`:
```bash
cp aiecs/scripts/tools_develop/pre-commit-schema-coverage.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

2. Or create a symlink:
```bash
ln -s ../../aiecs/scripts/tools_develop/pre-commit-schema-coverage.sh .git/hooks/pre-commit
```

## Configuration

### Environment Variables

- `MIN_COVERAGE`: Minimum coverage threshold (default: 90)
- `VERBOSE`: Enable verbose output (default: false)

Example:
```bash
export MIN_COVERAGE=95
export VERBOSE=true
pre-commit run --all-files
```

### Pre-commit Config

Edit `.pre-commit-config.yaml` to customize:

```yaml
- repo: local
  hooks:
    - id: validate-schema-coverage
      entry: bash -c 'python -m aiecs.scripts.tools_develop.validate_tool_schemas --min-coverage 90 || exit 1'
      always_run: true  # Run on every commit
      # Or set to false and use files: '^aiecs/tools/.*\.py$' to run only when tool files change
```

## Usage

### Manual Execution

Run the hook manually:
```bash
./aiecs/scripts/tools_develop/pre-commit-schema-coverage.sh
```

With custom threshold:
```bash
MIN_COVERAGE=95 ./aiecs/scripts/tools_develop/pre-commit-schema-coverage.sh
```

### Bypassing the Hook

If you need to bypass the hook for a specific commit (not recommended):
```bash
git commit --no-verify -m "Your message"
```

## What It Checks

1. **Overall Coverage**: Ensures the overall schema coverage across all tools meets the threshold
2. **Individual Tool Coverage**: Identifies tools below the threshold
3. **Schema Quality**: Validates schema quality metrics (description quality, type coverage)

## Output

The hook will:
- ✅ Pass if coverage meets the threshold
- ❌ Fail if coverage is below threshold, showing:
  - Overall coverage percentage
  - List of tools below threshold
  - Individual tool coverage percentages

## Integration with CI/CD

The same script can be used in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Check Schema Coverage
  run: |
    MIN_COVERAGE=90 ./aiecs/scripts/tools_develop/pre-commit-schema-coverage.sh
```

## Troubleshooting

### Hook Not Running

1. Check if pre-commit is installed: `pre-commit --version`
2. Verify hooks are installed: `pre-commit run --all-files`
3. Check `.git/hooks/pre-commit` exists and is executable

### False Positives

If the hook fails but you believe coverage is sufficient:
1. Run manually to see detailed output: `./aiecs/scripts/tools_develop/pre-commit-schema-coverage.sh`
2. Check individual tool coverage: `aiecs-tools-schema-coverage --format json`
3. Verify tool schemas are properly registered

### Performance

The hook may take a few seconds to run. To speed up:
- Use `files: '^aiecs/tools/.*\.py$'` to run only when tool files change
- Cache results if running frequently

