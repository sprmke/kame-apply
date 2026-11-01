---
name: vee-validate-forms
description: Forms with VeeValidate + Zod schemas generated from OpenAPI, with an unsaved-changes guard.
---

# VeeValidate forms

- Schemas come from the OpenAPI-generated Zod types; extend them for UX-only rules, never weaken server rules.
- `useForm({ validationSchema: toTypedSchema(schema) })`; fields use `packages/ui` inputs with visible labels and `aria-describedby` errors.
- Server errors map back to fields; unknown errors show a form-level message.
- **Unsaved-changes guard**: route-leave and tab-close prompts when the form is dirty; clears on successful save.
- Autosave only where the phase says so (profile interview); otherwise explicit Save.
- Sensitive-class fields are never offered as form fields in the profile (`pii-guard.mdc`).
