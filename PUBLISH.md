# Publishing AIECS to PyPI

Release checklist for cutting a version and letting **GitHub Actions** build and upload `aiecs` to TestPyPI / PyPI.

Do **not** run local `twine upload`. Push the tag (and publish a GitHub Release for PyPI); CI handles build and publish via trusted publishing.

Version bumps are managed by `aiecs-version`. See [`aiecs/scripts/aid/VERSION_MANAGEMENT.md`](aiecs/scripts/aid/VERSION_MANAGEMENT.md) for full options (`--show`, `--version`, `--bump`, `--no-changelog`).

## How publish is triggered

| Target | Workflow | Trigger |
|--------|----------|---------|
| [TestPyPI](https://test.pypi.org/p/aiecs) | [`.github/workflows/publish-to-testpypi.yml`](.github/workflows/publish-to-testpypi.yml) | Push a tag matching `v*` |
| [PyPI](https://pypi.org/p/aiecs) | [`.github/workflows/publish-to-pypi.yml`](.github/workflows/publish-to-pypi.yml) | Publish a GitHub **Release** for that tag (or `workflow_dispatch`) |

Both workflows use OIDC trusted publishing (`id-token: write`). No PyPI API tokens are needed on the developer machine.

## Prerequisites

1. Project dependencies installed (`poetry install`)
2. Clean working tree for the release commit (recommended)
3. Pre-commit hooks enabled (release commits run license/black/flake8/mypy/deptry)
4. Permission to push tags / create releases on `origin`

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

If you also changed dependencies, refresh the lockfile:

```bash
poetry lock --no-interaction
```

Confirm the bare PEP 440 version (use this for tags; `aiecs-version --show` prints a label prefix):

```bash
VERSION=$(poetry run python -c "import aiecs; print(aiecs.__version__)")
echo "${VERSION}"
```

## 2. Commit

```bash
VERSION=$(poetry run python -c "import aiecs; print(aiecs.__version__)")

git add aiecs/__init__.py aiecs/main.py pyproject.toml CHANGELOG.md
# plus any other release-related files (e.g. poetry.lock, PUBLISH.md, code/tests)
git status   # review staged set

git commit -m "Release v${VERSION}"
```

Pre-commit may take a minute; fix any hook failures and create a **new** commit (do not `--amend` unless you intentionally follow the project amend rules).

## 3. Tag and push (triggers TestPyPI)

```bash
VERSION=$(poetry run python -c "import aiecs; print(aiecs.__version__)")

# Create lightweight tag on current HEAD
git tag "v${VERSION}"

# Verify tag points at the release commit
git show -s --format='%h %s%n%d' "v${VERSION}"

# Push branch, then tag — tag push starts publish-to-testpypi.yml
git push origin HEAD
git push origin "v${VERSION}"
```

Useful checks:

```bash
git tag -l "v${VERSION}"
git ls-remote --tags origin "v${VERSION}"
```

Watch the workflow on GitHub Actions (`Publish to TestPyPI`). When it finishes:

```bash
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  "aiecs==${VERSION}"
python -c "import aiecs; print(aiecs.__version__)"
```

If the tag already exists locally and you need to move it (only when you created it and it was never pushed):

```bash
git tag -d "v${VERSION}"
git tag "v${VERSION}"
```

Do **not** force-push tags to a shared remote unless the team explicitly agrees.

## 4. Publish a GitHub Release (triggers PyPI)

Creating and **publishing** a GitHub Release for `v${VERSION}` starts `publish-to-pypi.yml`.

```bash
VERSION=$(poetry run python -c "import aiecs; print(aiecs.__version__)")

# Example with GitHub CLI (release notes can be empty or taken from CHANGELOG)
gh release create "v${VERSION}" \
  --title "v${VERSION}" \
  --notes-file <(awk "/^## \\[${VERSION}\\]/{flag=1; next} /^## \\[/{flag=0} flag" CHANGELOG.md)
```

Or create the release in the GitHub UI from the existing tag.

Watch `Publish to PyPI` on GitHub Actions. When it finishes:

```bash
pip install --upgrade "aiecs==${VERSION}"
python -c "import aiecs; print(aiecs.__version__)"
```

## Optional: local build smoke test

CI builds the package; local build is optional before tagging.

```bash
VERSION=$(poetry run python -c "import aiecs; print(aiecs.__version__)")

rm -rf dist/ build/ *.egg-info
poetry run pip install build
poetry run python -m build

python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate
pip install "dist/aiecs-${VERSION}-py3-none-any.whl"
python -c "import aiecs; print(aiecs.__version__)"
aiecs-version --show
deactivate
rm -rf test_env
```

## Quick reference

| Goal | Command / action |
|------|------------------|
| Show version | `poetry run aiecs-version --show` |
| Bare version for tags | `poetry run python -c "import aiecs; print(aiecs.__version__)"` |
| Cut stable `X.Y.Z` | `poetry run aiecs-version --version X.Y.Z` |
| Next patch/minor/major | `poetry run aiecs-version --bump patch\|minor\|major` |
| Next RC | `poetry run aiecs-version --bump rc` |
| Skip CHANGELOG rewrite | add `--no-changelog` |
| Refresh lock after dep edits | `poetry lock --no-interaction` |
| Trigger TestPyPI | `git push origin "v${VERSION}"` |
| Trigger PyPI | Publish a GitHub Release for `v${VERSION}` |
| Verify remote tag | `git ls-remote --tags origin "v${VERSION}"` |

## Notes

- Prefer Poetry-invoked tools (`poetry run …`) so the active project environment is used.
- Do not edit version strings by hand across files; always use `aiecs-version`.
- Tag names use a `v` prefix (`v2.1.1`); PyPI / `aiecs-version` use the bare PEP 440 version (`2.1.1`).
- PyPI versions are immutable: fix mistakes with a new patch (or a new RC), not a re-upload of the same version.
- Do not upload with local `twine`; the GitHub workflows are the supported publish path.
- For version-manager behavior and PEP 440 pre-release suffixes (`rcN`, `aN`, `bN`, `.devN`), see [`VERSION_MANAGEMENT.md`](aiecs/scripts/aid/VERSION_MANAGEMENT.md).
