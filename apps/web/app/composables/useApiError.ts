import { toApiError } from "~/lib/errors";

/** Maps API error codes to catalog messages: `errors.<code>`, falling back to `errors.generic`. */
export function useApiError() {
  const { t, te } = useI18n();
  return (e: unknown): string => {
    const { code } = toApiError(e);
    return te(`errors.${code}`) ? t(`errors.${code}`) : t("errors.generic");
  };
}
