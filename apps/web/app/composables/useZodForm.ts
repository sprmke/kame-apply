import { toTypedSchema } from "@vee-validate/zod";
import { useForm } from "vee-validate";
import type { ZodTypeAny } from "zod";

/** vee-validate + a Zod schema, with errors translated through the message catalog. */
export function useZodForm<S extends ZodTypeAny>(
  schema: S,
  initialValues: Record<string, unknown> = {},
) {
  const { t, te } = useI18n();
  const form = useForm({
    validationSchema: toTypedSchema(schema),
    initialValues: initialValues as never,
  });

  function translate(raw: string | undefined | null): string | undefined {
    if (!raw) return undefined;
    const [key, param] = raw.split(":");
    return te(key!) ? t(key!, { n: param ?? "" }) : t("validation.invalid");
  }

  /** Translated error for a field, shown only after the field was touched or a submit was tried. */
  const err = (name: string) =>
    translate((form.errors.value as Record<string, string | undefined>)[name]);

  return { form, err, translate };
}
