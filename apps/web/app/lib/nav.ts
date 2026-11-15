export type NavItem = {
  key: string;
  to: string;
  icon: string;
  phase: number | null;
  /** One-line description shown in the expanded Tools list and the command bar. */
  descKey?: string;
};

/** Primary destinations are the user's job-search loop. Everything else lives under Tools. */
export const NAV: NavItem[] = [
  { key: "today", to: "/", icon: "ph:newspaper", phase: null },
  { key: "tracks", to: "/tracks", icon: "ph:path", phase: 4, descKey: "tools.searchesHint" },
  { key: "jobs", to: "/jobs", icon: "ph:briefcase", phase: 6, descKey: "tools.jobsHint" },
  {
    key: "applications",
    to: "/applications",
    icon: "ph:folder-simple",
    phase: 11,
    descKey: "tools.applicationsHint",
  },
  { key: "profile", to: "/profile", icon: "ph:user-circle", phase: 2 },
  {
    key: "responses",
    to: "/responses",
    icon: "ph:envelope-simple",
    phase: 20,
    descKey: "tools.responsesHint",
  },
  { key: "studio", to: "/studio", icon: "ph:file-text", phase: 8, descKey: "tools.studioHint" },
  { key: "answers", to: "/answers", icon: "ph:chat-text", phase: 12, descKey: "tools.answersHint" },
  { key: "coach", to: "/coach", icon: "ph:users", phase: 20, descKey: "tools.coachHint" },
  {
    key: "contacts",
    to: "/contacts",
    icon: "ph:address-book",
    phase: 20,
    descKey: "tools.contactsHint",
  },
  { key: "safety", to: "/safety", icon: "ph:shield-check", phase: 7, descKey: "tools.safetyHint" },
  { key: "settings", to: "/settings", icon: "ph:gear", phase: null },
];

export const PRIMARY_NAV = NAV.filter((item) =>
  ["today", "tracks", "jobs", "applications", "profile"].includes(item.key),
);

export const MORE_NAV = NAV.filter((item) =>
  ["responses", "studio", "answers", "coach", "contacts", "safety"].includes(item.key),
);

export const SETTINGS_NAV = NAV.find((item) => item.key === "settings")!;
