import { useAuthStore } from "~/stores/auth";

/** Display formatting in the user's timezone and locale (the database stores UTC). */
export function useFormat() {
  const auth = useAuthStore();
  const { locale } = useI18n();
  const tz = () => auth.user?.timezone || "UTC";

  const dateTime = (iso: string) =>
    new Intl.DateTimeFormat(locale.value, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: tz(),
    }).format(new Date(iso));
  const date = (iso: string) =>
    new Intl.DateTimeFormat(locale.value, { dateStyle: "medium", timeZone: tz() }).format(
      new Date(iso),
    );
  const usd = (micros: number) =>
    new Intl.NumberFormat(locale.value, { style: "currency", currency: "USD" }).format(
      micros / 1_000_000,
    );
  const usdCents = (cents: number) =>
    new Intl.NumberFormat(locale.value, { style: "currency", currency: "USD" }).format(cents / 100);

  return { dateTime, date, usd, usdCents };
}
