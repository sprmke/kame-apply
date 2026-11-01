# workflow-wont-do

Mark a plan as **cancelled** and move it to `docs/workflow/wont-do/`.

1. Identify the slug from `planned/`, `in-progress/`, or the user message.
2. Run `bash scripts/dev/workflow-move.sh wont-do <slug>` (moves `<slug>.md` and `<slug>-design.md` if present).
3. Add a row to `docs/workflow/wont-do/README.md` with a one-line reason.
4. Remove the row from `docs/workflow/planned/README.md` or `in-progress/README.md` if listed.
