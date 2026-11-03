---
name: "source-command-ka-pull-new-changes"
description: "Migrated source command `ka-pull-new-changes`"
---

# source-command-ka-pull-new-changes

Use this skill when the user asks to run the migrated source command `ka-pull-new-changes`.

## Command Template

# ka-pull-new-changes

```bash
git fetch origin
git checkout main
git pull origin main
```

Rebase your feature branch if needed: `git checkout <branch> && git rebase main`
