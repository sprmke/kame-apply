export type NavItem = { key: string; to: string; icon: string; phase: number | null };

/** Primary destinations are the user's job-search loop. Everything else lives under More. */
export const NAV: NavItem[] = [
  { key: "today", to: "/", icon: "ph:newspaper", phase: null },
  { key: "tracks", to: "/tracks", icon: "ph:path", phase: 4 },
  { key: "jobs", to: "/jobs", icon: "ph:briefcase", phase: 6 },
  { key: "applications", to: "/applications", icon: "ph:folder-simple", phase: 11 },
  { key: "profile", to: "/profile", icon: "ph:user-circle", phase: 2 },
  { key: "responses", to: "/responses", icon: "ph:envelope-simple", phase: 20 },
  { key: "studio", to: "/studio", icon: "ph:file-text", phase: 8 },
  { key: "answers", to: "/answers", icon: "ph:chat-text", phase: 12 },
  { key: "coach", to: "/coach", icon: "ph:users", phase: 20 },
  { key: "contacts", to: "/contacts", icon: "ph:address-book", phase: 20 },
  { key: "safety", to: "/safety", icon: "ph:shield-check", phase: 7 },
  { key: "settings", to: "/settings", icon: "ph:gear", phase: null },
];

export const PRIMARY_NAV = NAV.filter((item) =>
  ["today", "tracks", "jobs", "applications", "profile"].includes(item.key),
);

export const MORE_NAV = NAV.filter((item) =>
  ["responses", "studio", "answers", "coach", "contacts", "safety"].includes(item.key),
);

export const SETTINGS_NAV = NAV.find((item) => item.key === "settings")!;
