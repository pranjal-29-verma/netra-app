# AI Code CLI Development Rules

## Purpose

This document defines the mandatory workflow and development rules that any AI Code CLI or coding assistant must follow before modifying or generating code in the repository.

---

# Pre-Development Workflow

The AI Code CLI must strictly follow the steps below before writing or modifying any code.

## 1. Checkout to Main Branch

Ensure the local repository is switched to the `main` branch.

```bash
git checkout main
```

---

## 2. Fetch and Pull Latest Changes

Always synchronize the local `main` branch with the remote repository before starting any work.

```bash
git fetch origin
git pull origin main
```

---

## 3. Create a New Feature Branch

Create a new branch with a meaningful and descriptive name based on the task or feature being implemented.

### Branch Naming Examples

```bash
feature/user-authentication
bugfix/login-api-timeout
hotfix/email-validation
refactor/gitlab-service
```

### Create Branch

```bash
git checkout -b <meaningful-branch-name>
```

---

## 4. Switch to the New Branch

Verify that development is being performed only on the newly created branch.

```bash
git branch
```

---

# Development Rules

## 5. Start Development

After completing all Git preparation steps:

- Begin implementation.
- Follow project coding standards.
- Avoid modifying unrelated files.
- Keep changes minimal and task-specific.
- Ensure code is clean, maintainable, and production-ready.

---

# Pre-Commit Rules

## 6. Ask for Confirmation Before Commit

The AI Code CLI must NEVER commit code automatically.

Before committing:

- Show the modified files.
- Provide a summary of changes.
- Ask the user for approval before running any commit command.

Example:

```text
The implementation is complete.
Would you like me to commit the changes?
```

---

# Commit Rules

## 7. Commit Using Standard Commit Message Format

All commits must follow the standardized commit message structure below.

### Commit Message Format

```text
<TicketNo> : One line summary of changes

What is changed?
--------------
- Add detailed list of implemented changes

Testing
--------------
- Add details of testing performed
```

---

# Additional Rules

- Never push code without explicit user approval.
- Never commit directly to the `main` branch.
- Always use meaningful branch names and commit messages.
- Ensure all tests pass before requesting commit approval.
- Avoid force pushing unless explicitly instructed by the user.
- Keep commits focused on a single task or feature.

---

# Example Workflow

```bash
git checkout main
git fetch origin
git pull origin main

git checkout -b feature/add-user-profile-api

# Start development

# After implementation
git status

# Ask user before commit

git commit -m "1024 : Add user profile API"
```
