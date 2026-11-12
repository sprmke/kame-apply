# Route: `/help`

**Page:** `apps/web/app/pages/help.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Words we use | Done | n/a | Documented | Plain definitions, same list as the glossary doc |
| Keyboard shortcuts | Done | n/a | Documented | Global command bar plus job-list keys |
| Setup and feedback | Done | n/a | Documented | Links to `/start` and opens the feedback dialog |

## Behavior

A single help page so nobody has to guess a word or a shortcut. Definitions are static (no AI, no cost). The route is linked from the rail, the mobile More sheet, and the profile menu.

Common questions:

- **Is this the glossary?** Yes, the same terms as `docs/design/glossary.md`, written for people.
- **Do shortcuts work everywhere?** The command bar shortcut does. Job keys work on `/jobs` when no field is focused.
- **How do I redo setup?** **Finish setup** opens `/start` at step 1.

## Implementation map

`help.vue`, `FeedbackButton`, i18n `help.*` and `shell.help*`.
