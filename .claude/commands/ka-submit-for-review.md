# ka-submit-for-review

After `/ka-check-before-pr` passes:

1. Update `docs/phases/README.md` status and tick the phase file's exit criteria; move the scratchpad to `docs/workflow/done/` (`/workflow-done`).
2. Push and open the PR:

```bash
git push -u origin HEAD
gh pr create --fill
```

PR body: what changed and why, the exit-criteria checklist, screenshots for UI work, and notes on any deviation from the phase file. No AI attribution (`git-commits.mdc`). Target `main`.
