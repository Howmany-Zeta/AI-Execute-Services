# Git Workflow for Python Middleware Project

This document outlines the Git workflow and branching strategy for the Python Middleware project.

## Branching Strategy

We follow a simplified Git Flow approach with the following branches:

### Main Branches

- **main**: The production-ready branch. All code in this branch should be stable and deployable.
- **develop**: The main development branch where feature branches are merged into.

### Supporting Branches

- **feature/**: For developing new features (e.g., `feature/add-new-service`)
- **bugfix/**: For fixing bugs (e.g., `bugfix/fix-authentication-issue`)
- **hotfix/**: For critical fixes that need to be applied directly to production (e.g., `hotfix/security-vulnerability`)
- **release/**: For preparing releases (e.g., `release/v1.0.0`)

## Workflow Guidelines

### Starting a New Feature

```bash
# Make sure you're on the develop branch
git checkout develop
git pull

# Create a new feature branch
git checkout -b feature/your-feature-name
```

### Working on Your Feature

```bash
# Make changes, then stage them
git add .

# Commit your changes with a descriptive message
git commit -m "Add detailed description of your changes"

# Push your branch to the remote repository
git push -u origin feature/your-feature-name
```

### Completing a Feature

When your feature is complete:

1. Pull the latest changes from the develop branch
   ```bash
   git checkout develop
   git pull
   git checkout feature/your-feature-name
   git merge develop
   ```

2. Resolve any conflicts if they occur

3. Create a pull request from your feature branch to the develop branch

4. After code review and approval, merge the pull request

### Creating a Release

```bash
# Create a release branch from develop
git checkout develop
git checkout -b release/v1.0.0

# Make any final adjustments and version bumps
# ...

# Merge to main when ready
git checkout main
git merge release/v1.0.0
git tag -a v1.0.0 -m "Version 1.0.0"
git push origin main --tags

# Also merge back to develop
git checkout develop
git merge release/v1.0.0
git push origin develop
```

### Hotfixes

For critical issues that need immediate fixing in production:

```bash
# Create hotfix branch from main
git checkout main
git checkout -b hotfix/critical-issue

# Make the fix
# ...

# Merge to both main and develop
git checkout main
git merge hotfix/critical-issue
git tag -a v1.0.1 -m "Hotfix: Critical issue"
git push origin main --tags

git checkout develop
git merge hotfix/critical-issue
git push origin develop
```

## Commit Message Guidelines

Follow these guidelines for commit messages:

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests after the first line
- Consider starting the commit message with an applicable emoji:
  - ✨ `:sparkles:` for new features
  - 🐛 `:bug:` for bug fixes
  - 📚 `:books:` for documentation changes
  - ♻️ `:recycle:` for refactoring code
  - 🧪 `:test_tube:` for adding tests
  - 🔧 `:wrench:` for configuration changes

## Git Best Practices

1. **Commit Often**: Make small, focused commits that address a single concern
2. **Pull Before Push**: Always pull the latest changes before pushing
3. **Write Good Commit Messages**: Follow the commit message guidelines
4. **Use Pull Requests**: For code review and collaboration
5. **Keep Branches Updated**: Regularly merge or rebase with the parent branch
6. **Delete Merged Branches**: Clean up branches after they've been merged

## Git Hooks

Consider setting up Git hooks for:
- Pre-commit: Run linters and formatters
- Pre-push: Run tests

## Versioning

We follow [Semantic Versioning](https://semver.org/):
- MAJOR version for incompatible API changes
- MINOR version for backwards-compatible functionality additions
- PATCH version for backwards-compatible bug fixes