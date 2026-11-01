import { onMounted, ref } from "vue";

export type ThemeChoice = "system" | "light" | "dark";
const KEY = "kame.theme";
const choice = ref<ThemeChoice>("system");

function apply(c: ThemeChoice) {
  const el = document.documentElement;
  if (c === "system") el.removeAttribute("data-theme");
  else el.setAttribute("data-theme", c);
}

export function useTheme() {
  onMounted(() => {
    try {
      const stored = localStorage.getItem(KEY) as ThemeChoice | null;
      if (stored === "light" || stored === "dark") choice.value = stored;
    } catch {
      // no storage: stay on the system theme
    }
    apply(choice.value);
  });

  function set(c: ThemeChoice) {
    choice.value = c;
    apply(c);
    try {
      if (c === "system") localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, c);
    } catch {
      // ignore
    }
  }

  return { choice, set };
}
