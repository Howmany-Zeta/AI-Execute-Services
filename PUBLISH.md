# Publishing AIECS to PyPI

Release checklist for building and uploading `aiecs` to TestPyPI / PyPI.

Version bumps are managed by `aiecs-version`. See [`aiecs/scripts/aid/VERSION_MANAGEMENT.md`](aiecs/scripts/aid/VERSION_MANAGEMENT.md) for full options (`--show`, `--version`, `--bump`, `--no-changelog`).

## Prerequisites

1. Accounts on [PyPI](https://pypi.org/) and [TestPyPI](https://test.pypi.org/)
2. Project dependencies installed (`poetry install`)
3. Build / upload tools available:

```bash
poetry run pip install build twine
# or: pip install build twine
```

4. Clean working tree for the release commit (recommended)

## 1. Set the release version

From the repository root:

```bash
# Inspect current version
poetry run aiecs-version --show

# Stable release (example: promote 2.1.0rc10 → 2.1.0)
poetry run aiecs-version --version 2.1.0

# Or bump automatically (clears any rc/a/b/.dev suffix)
poetry run aiecs-version --bump patch   # 2.1.0 -> 2.1.1
poetry run aiecs-version --bump minor   # 2.1.0 -> 2.2.0
poetry run aiecs-version --bump major   # 2.1.0 -> 3.0.0

# Pre-release RC
poetry run aiecs-version --bump rc      # 2.1.0 -> 2.1.0rc1, or 2.1.0rc1 -> 2.1.0rc2
poetry run aiecs-version --version 2.2.0rc1
```

`aiecs-version` updates:

- `aiecs/__init__.py` (`__version__`)
- `aiecs/main.py` (FastAPI / health-check version)
- `pyproject.toml` (`[project]` and `[tool.poetry]`)
- `CHANGELOG.md` (promotes `[Unreleased]` into a dated release section)

Put release notes under `## [Unreleased]` **before** running `aiecs-version`, so they land in the new section. Use `--no-changelog` only when intentionally skipping CHANGELOG.

Confirm:

```bash
poetry run aiecs-version --show
```

## 2. Commit and tag

```bash
VERSION=$(poetry run aiecs-version --show)

git add aiecs/__init__.py aiecs/main.py pyproject.toml CHANGELOG.md
# plus any other release-related files
git commit -m "Release v${VERSION}"

git tag "v${VERSION}"
git push origin HEAD
git push origin "v${VERSION}"
```

## 3. Build the package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build sdist + wheel
poetry run python -m build
# or: python -m build
```

Artifacts appear under `dist/` as `aiecs-<version>.tar.gz` and `aiecs-<version>-py3-none-any.whl`.

## 4. Smoke-test the wheel locally

```bash
VERSION=$(poetry run aiecs-version --show)

python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

pip install "dist/aiecs-${VERSION}-py3-none-any.whl"

python -c "import aiecs; print(aiecs.__version__)"
aiecs --help
aiecs-version --show
aiecs-patch-weasel --help

deactivate
rm -rf test_env
```

## 5. Upload to TestPyPI (recommended first)

```bash
poetry run twine upload --repository testpypi dist/*
# or: python -m twine upload --repository testpypi dist/*

VERSION=$(poetry run aiecs-version --show)
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "aiecs==${VERSION}"
```

## 6. Upload to PyPI

```bash
poetry run twine upload dist/*
# or: python -m twine upload dist/*
```

## 7. Post-upload verification

```bash
VERSION=$(poetry run aiecs-version --show)

pip install --upgrade "aiecs==${VERSION}"
python -c "import aiecs; print(aiecs.__version__)"
```

## Quick reference — stable vs RC

| Goal | Command |
|------|---------|
| Show version | `poetry run aiecs-version --show` |
| Cut stable `X.Y.Z` | `poetry run aiecs-version --version X.Y.Z` |
| Next patch/minor/major | `poetry run aiecs-version --bump patch\|minor\|major` |
| Next RC | `poetry run aiecs-version --bump rc` |
| Skip CHANGELOG rewrite | add `--no-changelog` |
| Tag | `git tag v$(poetry run aiecs-version --show)` |

## Notes

- Prefer Poetry-invoked tools (`poetry run …`) so the active project environment is used.
- Do not edit version strings by hand across files; always use `aiecs-version`.
- PyPI versions are immutable: fix mistakes with a new patch (or a new RC), not a re-upload of the same version.
- For version-manager behavior and PEP 440 pre-release suffixes (`rcN`, `aN`, `bN`, `.devN`), see [`VERSION_MANAGEMENT.md`](aiecs/scripts/aid/VERSION_MANAGEMENT.md).
