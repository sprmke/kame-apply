export type NavItem = { key: string; to: string; icon: string; phase: number | null };

/** Rail order from docs/design/design-system.md §8. `phase` is when the screen is built. */
export const NAV: NavItem[] = [
  { key: "today", to: "/", icon: "ph:newspaper", phase: null },
  { key: "tracks", to: "/tracks", icon: "ph:path", phase: 4 },
  { key: "jobs", to: "/jobs", icon: "ph:briefcase", phase: 6 },
  { key: "applications", to: "/applications", icon: "ph:folder-simple", phase: 11 },
  { key: "responses", to: "/responses", icon: "ph:envelope-simple", phase: 20 },
  { key: "runs", to: "/runs", icon: "ph:play-circle", phase: 15 },
  { key: "studio", to: "/studio", icon: "ph:file-text", phase: 8 },
  { key: "answers", to: "/answers", icon: "ph:chat-text", phase: 12 },
  { key: "coach", to: "/coach", icon: "ph:users", phase: 20 },
  { key: "contacts", to: "/contacts", icon: "ph:address-book", phase: 20 },
  { key: "safety", to: "/safety", icon: "ph:shield-check", phase: 7 },
  { key: "settings", to: "/settings", icon: "ph:gear", phase: null },
];

/** Phone bottom bar: four fixed slots around the center Needs-you button; the rest live in More. */
export const MOBILE_PRIMARY = ["today", "jobs"] as const;
export const MOBILE_SECONDARY = ["applications"] as const;
